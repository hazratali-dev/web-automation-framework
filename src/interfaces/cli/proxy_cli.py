"""Standalone Proxy Manager CLI (§Phase 2) — exercises add/list/rotate/health-check
against the local SQLite DB, no broker/Celery/Docker needed.

Usage (from the project root, inside the venv):
    python -m src.interfaces.cli.proxy_cli add --host 1.2.3.4 --port 8080
    python -m src.interfaces.cli.proxy_cli list
    python -m src.interfaces.cli.proxy_cli rotate
    python -m src.interfaces.cli.proxy_cli check
"""

import asyncio

import typer

from src.application.use_cases.proxy_use_cases import (
    AddProxyUseCase,
    ListProxiesUseCase,
    RunProxyHealthCheckUseCase,
    SelectProxyUseCase,
)
from src.infrastructure.config.runtime_config_service import DbRuntimeConfigService
from src.infrastructure.database.repositories.proxy_repository import SqlAlchemyProxyRepository
from src.infrastructure.database.session import AsyncSessionLocal
from src.infrastructure.monitoring.logging_setup import configure_logging
from src.infrastructure.proxy.manager import ProxyManager

app = typer.Typer(help="Proxy Manager CLI — Phase 2")


def _build_manager(session) -> ProxyManager:
    repository = SqlAlchemyProxyRepository(session)
    runtime_config = DbRuntimeConfigService(session)
    return ProxyManager(repository, runtime_config)


@app.command()
def add(
    host: str = typer.Option(..., help="Proxy host/IP"),
    port: int = typer.Option(..., help="Proxy port"),
    protocol: str = typer.Option("http", help="http or socks5"),
    username: str = typer.Option(None),
    password: str = typer.Option(None),
    provider: str = typer.Option(None),
    country: str = typer.Option(None),
) -> None:
    """Add a proxy to the pool."""

    async def run() -> None:
        async with AsyncSessionLocal() as session:
            use_case = AddProxyUseCase(_build_manager(session))
            proxy = await use_case.execute(
                host=host,
                port=port,
                protocol=protocol,
                username=username,
                password=password,
                provider=provider,
                country=country,
            )
            typer.echo(f"Added proxy {proxy.id}: {proxy.protocol}://{proxy.host}:{proxy.port}")

    asyncio.run(run())


@app.command(name="list")
def list_proxies(active_only: bool = typer.Option(False, "--active-only")) -> None:
    """List proxies in the pool."""

    async def run() -> None:
        async with AsyncSessionLocal() as session:
            use_case = ListProxiesUseCase(_build_manager(session))
            proxies = await use_case.execute(active_only=active_only)
            if not proxies:
                typer.echo("No proxies found.")
                return
            for p in proxies:
                status = "active" if p.is_active else "inactive"
                typer.echo(
                    f"{p.id}  {p.protocol}://{p.host}:{p.port}  [{status}]  "
                    f"success_rate={p.success_rate:.2f}  fails={p.consecutive_failures}"
                )

    asyncio.run(run())


@app.command()
def rotate(times: int = typer.Option(1, "--times", help="How many consecutive selections to show")) -> None:
    """Show which proxy the currently-configured strategy would select next.

    NOTE: the round-robin cursor lives in process memory (§Phase 2 scope —
    matches Appendix A's single-process dev model), so it only cycles *within*
    one CLI invocation. Use --times N to see it rotate; running the command
    again starts a fresh process (and thus a fresh cursor). In the real app
    this isn't an issue — selection happens from the one long-running
    FastAPI/asyncio process, not a new process per call.
    """

    async def run() -> None:
        async with AsyncSessionLocal() as session:
            use_case = SelectProxyUseCase(_build_manager(session))
            for _ in range(times):
                proxy = await use_case.execute()
                if proxy is None:
                    typer.echo("No active proxies available.")
                    return
                typer.echo(f"Selected: {proxy.id}  {proxy.protocol}://{proxy.host}:{proxy.port}")

    asyncio.run(run())


@app.command()
def check() -> None:
    """Run one health-check sweep over the whole pool (active + inactive)."""

    async def run() -> None:
        async with AsyncSessionLocal() as session:
            use_case = RunProxyHealthCheckUseCase(_build_manager(session))
            summary = await use_case.execute()
            typer.echo(summary)

    asyncio.run(run())


if __name__ == "__main__":
    from src.config.settings import get_settings

    settings = get_settings()
    configure_logging(settings.app_env, settings.log_level)
    app()
