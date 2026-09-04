from datetime import datetime, timezone

import structlog

from src.domain.entities.proxy import Proxy
from src.domain.interfaces.proxy_repository import ProxyRepository
from src.domain.interfaces.runtime_config_port import RuntimeConfigPort
from src.infrastructure.proxy.health_check import check_proxy_health
from src.infrastructure.proxy.rotation import select_proxy

logger = structlog.get_logger(__name__)

DEACTIVATE_AFTER_CONSECUTIVE_FAILURES = 3


class ProxyManager:
    """Orchestrates the proxy pool (§5.1): dynamic-strategy selection, and the
    health-check sweep that deactivates dead proxies / re-tests inactive ones."""

    def __init__(self, repository: ProxyRepository, runtime_config: RuntimeConfigPort) -> None:
        self._repository = repository
        self._runtime_config = runtime_config

    async def add_proxy(self, proxy: Proxy) -> Proxy:
        return await self._repository.add(proxy)

    async def list_proxies(self, *, active_only: bool = False) -> list[Proxy]:
        if active_only:
            return await self._repository.list_active()
        return await self._repository.list_all()

    async def select_proxy(self) -> Proxy | None:
        """Picks the next proxy per the currently-configured strategy
        (`runtime_config.proxy_strategy`, default round_robin) — read fresh on
        every call, so a strategy switch via the API takes effect immediately
        (§5.1, §5.6)."""
        strategy = await self._runtime_config.get("proxy_strategy", "round_robin")
        active_proxies = await self._repository.list_active()
        return select_proxy(active_proxies, strategy or "round_robin")

    async def select_proxy_with_secret(self) -> Proxy | None:
        """Like select_proxy(), but with the password decrypted onto the
        entity — needed by anything that actually connects through the proxy
        (Browser Engine, §5.2)."""
        selected = await self.select_proxy()
        if selected is None:
            return None
        return await self._repository.get_with_secret(selected.id)

    async def record_result(self, proxy_id, *, success: bool, latency_ms: int | None = None) -> None:
        """Lets callers outside the periodic health-check sweep (e.g. a real
        task run through the proxy, §5.2) also feed back into the same
        success/failure counters that drive auto-deactivation."""
        full_proxy = await self._repository.get_with_secret(proxy_id)
        if full_proxy is None:
            return
        if success:
            full_proxy.record_success(latency_ms or 0)
        else:
            full_proxy.record_failure(deactivate_after=DEACTIVATE_AFTER_CONSECUTIVE_FAILURES)
        await self._repository.update(full_proxy)

    async def run_health_check_cycle(self) -> dict[str, int]:
        """Probes every proxy — active ones (to catch newly-dead proxies) and
        inactive ones (self-healing re-test, §5.1). Returns a small summary
        for logging/CLI output."""
        active = await self._repository.list_active()
        inactive = await self._repository.list_inactive()

        summary = {"checked": 0, "healthy": 0, "unhealthy": 0, "reactivated": 0, "deactivated": 0}

        for proxy in active + inactive:
            was_active = proxy.is_active
            full_proxy = await self._repository.get_with_secret(proxy.id)
            if full_proxy is None:
                continue

            healthy, latency_ms = await check_proxy_health(full_proxy)
            summary["checked"] += 1

            if healthy:
                full_proxy.record_success(latency_ms or 0)
                summary["healthy"] += 1
                if not was_active:
                    summary["reactivated"] += 1
            else:
                full_proxy.record_failure(deactivate_after=DEACTIVATE_AFTER_CONSECUTIVE_FAILURES)
                summary["unhealthy"] += 1
                if was_active and not full_proxy.is_active:
                    summary["deactivated"] += 1

            full_proxy.last_checked_at = datetime.now(timezone.utc)
            await self._repository.update(full_proxy)

            logger.info(
                "proxy_health_checked",
                proxy_id=str(full_proxy.id),
                host=full_proxy.host,
                healthy=healthy,
                latency_ms=latency_ms,
                is_active=full_proxy.is_active,
            )

        return summary
