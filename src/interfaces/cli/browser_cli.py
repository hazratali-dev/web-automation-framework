"""Standalone Browser Automation Engine CLI (§Phase 3).

Usage (from the project root, inside the venv):
    python -m src.interfaces.cli.browser_cli run --url https://example.com
    python -m src.interfaces.cli.browser_cli run-batch --url https://example.com --count 8
"""

import asyncio

import typer

from src.application.use_cases.browser_use_cases import RunBrowserBatchUseCase, RunBrowserSessionUseCase
from src.config.settings import get_settings
from src.infrastructure.browser.engine import DEFAULT_MAX_CONCURRENT_BROWSERS, BrowserEngine
from src.infrastructure.config.runtime_config_service import DbRuntimeConfigService
from src.infrastructure.database.repositories.proxy_repository import SqlAlchemyProxyRepository
from src.infrastructure.database.repositories.target_repository import SqlAlchemyTargetRepository
from src.infrastructure.database.repositories.task_repository import SqlAlchemyTaskRepository
from src.infrastructure.database.repositories.task_run_repository import SqlAlchemyTaskRunRepository
from src.infrastructure.database.session import AsyncSessionLocal
from src.infrastructure.monitoring.logging_setup import configure_logging
from src.infrastructure.proxy.manager import ProxyManager

app = typer.Typer(help="Browser Automation Engine CLI — Phase 3")


def _build_use_case(session, engine: BrowserEngine, *, use_proxy: bool) -> RunBrowserSessionUseCase:
    proxy_manager = None
    if use_proxy:
        proxy_manager = ProxyManager(SqlAlchemyProxyRepository(session), DbRuntimeConfigService(session))
    return RunBrowserSessionUseCase(
        engine=engine,
        target_repo=SqlAlchemyTargetRepository(session),
        task_repo=SqlAlchemyTaskRepository(session),
        task_run_repo=SqlAlchemyTaskRunRepository(session),
        proxy_manager=proxy_manager,
    )


@app.command()
def run(
    url: str = typer.Option(..., help="Target URL to load"),
    proxy: bool = typer.Option(True, help="Route through a proxy from the pool, if any are active"),
    screenshot: bool = typer.Option(True, help="Save a screenshot to ./screenshots/"),
    headed: bool = typer.Option(False, help="Show the browser window (dev default is headless, §Appendix A.2)"),
) -> None:
    """Run one browser session against URL and persist the result."""

    async def run_once() -> None:
        async with BrowserEngine(headless=not headed) as engine:
            async with AsyncSessionLocal() as session:
                use_case = _build_use_case(session, engine, use_proxy=proxy)
                task_run = await use_case.execute(url=url, use_proxy=proxy, take_screenshot=screenshot)
                typer.echo(f"task_run={task_run.id} status={task_run.status}")
                if task_run.status == "success":
                    typer.echo(f"metrics={task_run.result}")
                    typer.echo(f"screenshot={task_run.screenshot_path}")
                else:
                    typer.echo(f"error={task_run.error_message}")

    asyncio.run(run_once())


@app.command(name="run-batch")
def run_batch(
    url: str = typer.Option(..., help="Target URL to load"),
    count: int = typer.Option(8, help="How many concurrent sessions to request"),
    proxy: bool = typer.Option(False, help="Route through a proxy from the pool"),
) -> None:
    """Fire `count` concurrent sessions to prove the Semaphore(N) concurrency
    cap actually holds (default N=5, §Phase 3)."""

    async def run_all() -> None:
        typer.echo(f"max_concurrent_browsers (hardcoded, Phase 3) = {DEFAULT_MAX_CONCURRENT_BROWSERS}")
        async with BrowserEngine(headless=True) as engine:
            # A fresh AsyncSession per concurrent run — AsyncSession isn't
            # safe to share across concurrently-running coroutines.
            sessions = [AsyncSessionLocal() for _ in range(count)]
            for s in sessions:
                await s.__aenter__()
            try:
                use_cases = [_build_use_case(s, engine, use_proxy=proxy) for s in sessions]
                batch = RunBrowserBatchUseCase(use_cases)
                task_runs = await batch.execute(url=url, use_proxy=proxy, take_screenshot=False)
                for tr in task_runs:
                    typer.echo(f"task_run={tr.id} status={tr.status} duration_ms={tr.duration_ms}")
            finally:
                for s in sessions:
                    await s.__aexit__(None, None, None)

    asyncio.run(run_all())


if __name__ == "__main__":
    settings = get_settings()
    configure_logging(settings.app_env, settings.log_level)
    app()
