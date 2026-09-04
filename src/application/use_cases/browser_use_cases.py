import asyncio
from datetime import datetime, timezone

from src.domain.entities.metric import Metric
from src.domain.entities.session import BrowserSession
from src.domain.entities.target import Target
from src.domain.entities.task import Task
from src.domain.entities.task_run import TaskRun
from src.domain.interfaces.target_repository import TargetRepository
from src.domain.interfaces.task_repository import TaskRepository
from src.domain.interfaces.task_run_repository import TaskRunRepository
from src.infrastructure.browser.engine import BrowserEngine
from src.infrastructure.proxy.manager import ProxyManager

MANUAL_TASK_TYPE = "manual_test"  # Phase 3 CLI-driven runs; Phase 4 adds real scheduled task types.


class RunBrowserSessionUseCase:
    """One full lifecycle: get-or-create Target/Task -> create TaskRun
    (queued) -> select proxy -> run the browser session -> persist the
    terminal result (§5.2, §5.5). This is what both the Phase 3 CLI and,
    later, the Phase 4 task runner call."""

    def __init__(
        self,
        engine: BrowserEngine,
        target_repo: TargetRepository,
        task_repo: TaskRepository,
        task_run_repo: TaskRunRepository,
        proxy_manager: ProxyManager | None,
    ) -> None:
        self._engine = engine
        self._target_repo = target_repo
        self._task_repo = task_repo
        self._task_run_repo = task_run_repo
        self._proxy_manager = proxy_manager

    async def execute(
        self,
        *,
        url: str,
        target_name: str | None = None,
        use_proxy: bool = True,
        take_screenshot: bool = True,
    ) -> TaskRun:
        target = await self._target_repo.get_or_create(
            Target(name=target_name or url, base_url=url, target_type="own_site")
        )
        task = await self._task_repo.get_or_create(Task(target_id=target.id, task_type=MANUAL_TASK_TYPE))

        proxy = None
        if use_proxy and self._proxy_manager is not None:
            proxy = await self._proxy_manager.select_proxy_with_secret()

        task_run = await self._task_run_repo.create(TaskRun(task_id=task.id, proxy_id=proxy.id if proxy else None))
        await self._task_run_repo.mark_running(task_run.id, datetime.now(timezone.utc))

        result = await self._engine.run_session(url, proxy=proxy, take_screenshot=take_screenshot)

        if proxy is not None and self._proxy_manager is not None:
            await self._proxy_manager.record_result(
                proxy.id, success=result.success, latency_ms=result.duration_ms
            )

        finished_at = datetime.now(timezone.utc)

        if not result.success:
            await self._task_run_repo.fail(task_run.id, result.error or "unknown error", finished_at)
            task_run.status = "failed"
            task_run.error_message = result.error
            task_run.finished_at = finished_at
            return task_run

        sessions = [
            BrowserSession(
                task_run_id=task_run.id,
                browser_type="chromium",
                user_agent=result.fingerprint.user_agent if result.fingerprint else None,
                viewport=result.fingerprint.viewport if result.fingerprint else None,
                fingerprint_config=result.fingerprint.as_config_dict() if result.fingerprint else None,
            )
        ]
        metrics = [
            Metric(task_run_id=task_run.id, metric_name=name, metric_value=value, unit="ms")
            for name, value in result.metrics.items()
            if value is not None
        ]

        task_run.status = "success"
        task_run.finished_at = finished_at
        task_run.duration_ms = result.duration_ms
        task_run.result = result.metrics
        task_run.screenshot_path = result.screenshot_path

        await self._task_run_repo.complete(task_run, sessions, metrics)
        return task_run


class RunBrowserBatchUseCase:
    """Fires `count` concurrent RunBrowserSessionUseCase runs against the same
    (shared) BrowserEngine — demonstrates that Semaphore(N) actually caps
    concurrency (§Phase 3 exit criterion: max 5 contexts at once), not just
    that it's declared. Each concurrent run gets ITS OWN use-case instance
    (own DB session, passed in by the caller) since AsyncSession isn't safe
    to share across concurrent coroutines."""

    def __init__(self, use_cases: list[RunBrowserSessionUseCase]) -> None:
        self._use_cases = use_cases

    async def execute(self, *, url: str, use_proxy: bool = True, take_screenshot: bool = False) -> list[TaskRun]:
        return await asyncio.gather(
            *(
                uc.execute(url=url, use_proxy=use_proxy, take_screenshot=take_screenshot)
                for uc in self._use_cases
            )
        )
