"""Task Orchestration & Fault-Tolerance CLI (§Phase 4) — asyncio-native,
no Celery/Redis/Docker.

Usage (from the project root, inside the venv):
    python -m src.interfaces.cli.task_cli create-task --url https://example.com --cron "* * * * *"
    python -m src.interfaces.cli.task_cli set-status --url https://example.com --status paused
    python -m src.interfaces.cli.task_cli run-scheduler --seconds 90
    python -m src.interfaces.cli.task_cli visitor-batch --url https://example.com --total 50
    python -m src.interfaces.cli.task_cli fault-demo --url https://10.255.255.1/ --attempts 6
"""

import asyncio

import typer

from src.application.use_cases.browser_use_cases import RunBrowserSessionUseCase, make_task_execution_handler
from src.application.use_cases.visitor_batch_use_cases import RunVisitorBatchUseCase
from src.config.settings import get_settings
from src.domain.entities.target import Target
from src.domain.entities.task import Task
from src.infrastructure.browser.engine import BrowserEngine
from src.infrastructure.database.repositories.target_repository import SqlAlchemyTargetRepository
from src.infrastructure.database.repositories.task_repository import SqlAlchemyTaskRepository
from src.infrastructure.database.repositories.task_run_repository import SqlAlchemyTaskRunRepository
from src.infrastructure.database.session import AsyncSessionLocal
from src.infrastructure.monitoring.logging_setup import configure_logging
from src.infrastructure.resilience.circuit_breaker import CircuitBreakerRegistry
from src.infrastructure.scheduler.asyncio_scheduler import AsyncioScheduler
from src.infrastructure.task_runner.asyncio_runner import AsyncioTaskRunner

app = typer.Typer(help="Task Orchestration & Fault-Tolerance CLI — Phase 4")

DEMO_TASK_TYPE = "performance_check"


@app.command(name="create-task")
def create_task(
    url: str = typer.Option(..., help="Target URL"),
    cron: str = typer.Option(..., help='Cron expression, e.g. "* * * * *" for every minute'),
    task_type: str = typer.Option(DEMO_TASK_TYPE),
) -> None:
    """Get-or-create a Target + a scheduled Task for it."""

    async def run() -> None:
        async with AsyncSessionLocal() as session:
            target = await SqlAlchemyTargetRepository(session).get_or_create(Target(name=url, base_url=url))
            task_repo = SqlAlchemyTaskRepository(session)
            existing = await task_repo.get_by_target_and_type(target.id, task_type)
            if existing is not None:
                typer.echo(f"Task already exists: {existing.id} (status={existing.status})")
                return
            task = await task_repo.add(Task(target_id=target.id, task_type=task_type, schedule_cron=cron))
            typer.echo(f"Created task {task.id} for target {target.id}, cron='{cron}'")

    asyncio.run(run())


@app.command(name="set-status")
def set_status(
    url: str = typer.Option(...),
    status: str = typer.Option(..., help="active | paused | archived"),
    task_type: str = typer.Option(DEMO_TASK_TYPE),
) -> None:
    """Pause/resume/archive a task (§5.3) — scheduler stops enqueueing new
    runs for it, but any run already in flight finishes normally."""

    async def run() -> None:
        async with AsyncSessionLocal() as session:
            target_repo = SqlAlchemyTargetRepository(session)
            task_repo = SqlAlchemyTaskRepository(session)
            target = await target_repo.get_by_base_url(url)
            if target is None:
                typer.echo("No target found for that URL.")
                return
            task = await task_repo.get_by_target_and_type(target.id, task_type)
            if task is None:
                typer.echo("No task found for that target/task_type.")
                return
            await task_repo.update_status(task.id, status)
            typer.echo(f"Task {task.id} status -> {status}")

    asyncio.run(run())


@app.command(name="run-scheduler")
def run_scheduler(seconds: float = typer.Option(90.0, help="How long to let the scheduler run before stopping")) -> None:
    """Starts BrowserEngine + AsyncioTaskRunner + AsyncioScheduler together
    for `seconds`, so you can watch scheduled (cron-due, non-paused) tasks
    fire automatically — no manual trigger."""

    async def run() -> None:
        async with BrowserEngine(headless=True) as engine:
            handler = make_task_execution_handler(engine, AsyncSessionLocal)
            task_runner = AsyncioTaskRunner(handler)
            scheduler = AsyncioScheduler(AsyncSessionLocal, task_runner)

            await task_runner.start()
            await scheduler.start()
            typer.echo(f"Scheduler running for {seconds}s — watch the logs for scheduled_trigger_fired...")
            await asyncio.sleep(seconds)

            await scheduler.stop()
            await task_runner.stop()

    asyncio.run(run())


@app.command(name="visitor-batch")
def visitor_batch(
    url: str = typer.Option(...),
    total: int = typer.Option(50, help="Total visitors to simulate"),
    proxy: bool = typer.Option(False),
) -> None:
    """§Appendix A.2 — simulate `total` visitors, batched at whatever
    runtime_config.max_concurrent_browsers currently says."""

    async def run() -> None:
        async with BrowserEngine() as engine:
            use_case = RunVisitorBatchUseCase(engine, AsyncSessionLocal)
            task_runs = await use_case.execute(url=url, total_visitors=total, use_proxy=proxy)
            succeeded = sum(1 for tr in task_runs if tr.status == "success")
            typer.echo(f"{succeeded}/{len(task_runs)} succeeded")

    asyncio.run(run())


@app.command(name="fault-demo")
def fault_demo(
    url: str = typer.Option(..., help="An unreachable URL, to force failures on purpose"),
    attempts: int = typer.Option(6, help="How many sequential requests to fire at it"),
) -> None:
    """Fires repeated requests at an unreachable target to show retry
    backoff+jitter, then the circuit breaker opening and short-circuiting
    later attempts instantly instead of waiting through a timeout again."""

    async def run() -> None:
        registry = CircuitBreakerRegistry(fail_max=3, reset_timeout=15.0)
        async with BrowserEngine() as engine:
            for i in range(1, attempts + 1):
                async with AsyncSessionLocal() as session:
                    use_case = RunBrowserSessionUseCase(
                        engine=engine,
                        target_repo=SqlAlchemyTargetRepository(session),
                        task_repo=SqlAlchemyTaskRepository(session),
                        task_run_repo=SqlAlchemyTaskRunRepository(session),
                        proxy_manager=None,
                        circuit_registry=registry,
                        max_retries=1,
                        retry_base_delay=1.0,
                    )
                    task_run = await use_case.execute(url=url, use_proxy=False, take_screenshot=False)
                    typer.echo(
                        f"request {i}: status={task_run.status} retry_count={task_run.retry_count} "
                        f"error={task_run.error_message}"
                    )

    asyncio.run(run())


if __name__ == "__main__":
    settings = get_settings()
    configure_logging(settings.app_env, settings.log_level)
    app()
