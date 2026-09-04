from src.domain.entities.proxy import Proxy
from src.infrastructure.proxy.manager import ProxyManager


class AddProxyUseCase:
    def __init__(self, manager: ProxyManager) -> None:
        self._manager = manager

    async def execute(
        self,
        *,
        host: str,
        port: int,
        protocol: str = "http",
        username: str | None = None,
        password: str | None = None,
        provider: str | None = None,
        country: str | None = None,
    ) -> Proxy:
        proxy = Proxy(
            host=host,
            port=port,
            protocol=protocol,
            username=username,
            password=password,
            provider=provider,
            country=country,
        )
        return await self._manager.add_proxy(proxy)


class ListProxiesUseCase:
    def __init__(self, manager: ProxyManager) -> None:
        self._manager = manager

    async def execute(self, *, active_only: bool = False) -> list[Proxy]:
        return await self._manager.list_proxies(active_only=active_only)


class SelectProxyUseCase:
    """AKA "rotate" — returns whichever proxy the currently-configured
    strategy would hand out next (§5.1)."""

    def __init__(self, manager: ProxyManager) -> None:
        self._manager = manager

    async def execute(self) -> Proxy | None:
        return await self._manager.select_proxy()


class RunProxyHealthCheckUseCase:
    def __init__(self, manager: ProxyManager) -> None:
        self._manager = manager

    async def execute(self) -> dict[str, int]:
        return await self._manager.run_health_check_cycle()
