import time

import httpx
import structlog

from src.domain.entities.proxy import Proxy

logger = structlog.get_logger(__name__)

DEFAULT_CHECK_URL = "https://httpbin.org/ip"
DEFAULT_TIMEOUT_SECONDS = 10.0


async def check_proxy_health(
    proxy: Proxy,
    *,
    check_url: str = DEFAULT_CHECK_URL,
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
) -> tuple[bool, int | None]:
    """Lightweight liveness probe (§5.1) — a GET through the proxy to
    `check_url`. Returns (is_healthy, latency_ms). Never raises: any failure
    (timeout, refused connection, bad proxy auth, ...) is reported as
    unhealthy rather than propagated, so a single bad proxy can't crash a
    health-check sweep over the whole pool."""
    started = time.monotonic()
    try:
        async with httpx.AsyncClient(proxy=proxy.proxy_url(), timeout=timeout_seconds) as client:
            response = await client.get(check_url)
            response.raise_for_status()
        latency_ms = int((time.monotonic() - started) * 1000)
        return True, latency_ms
    except Exception as exc:
        logger.warning("proxy_health_check_failed", proxy_id=str(proxy.id), host=proxy.host, error=str(exc))
        return False, None
