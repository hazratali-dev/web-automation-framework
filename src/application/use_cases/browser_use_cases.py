import asyncio
import uuid
from collections.abc import Callable
from datetime import datetime, timezone

import structlog

from src.domain.entities.metric import Metric
from src.domain.entities.session import BrowserSession
from src.domain.entities.target import Target
from src.domain.entities.task import Task
from src.domain.entities.task_run import TaskRun
from src.domain.interfaces.preview_store_port import PreviewStorePort
from src.domain.interfaces.status_store_port import StatusStorePort
from src.domain.interfaces.target_repository import TargetRepository
from src.domain.interfaces.task_repository import TaskRepository
from src.domain.interfaces.task_run_repository import TaskRunRepository
from src.domain.interfaces.task_runner_port import TaskHandler
from src.infrastructure.browser.engine import BrowserEngine, BrowserRunResult
from src.infrastructure.config.runtime_config_service import DbRuntimeConfigService
from src.infrastructure.database.repositories.proxy_repository import SqlAlchemyProxyRepository
from src.infrastructure.database.repositories.target_repository import SqlAlchemyTargetRepository
from src.infrastructure.database.repositories.task_repository import SqlAlchemyTaskRepository
from src.infrastructure.database.repositories.task_run_repository import SqlAlchemyTaskRunRepository
from src.infrastructure.proxy.manager import ProxyManager
from src.infrastructure.resilience.circuit_breaker import CircuitBreakerRegistry, CircuitOpenError, default_registry
from src.infrastructure.security.encryption import decrypt_json
from src.shared.retry import compute_backoff

logger = structlog.get_logger(__name__)

MANUAL_TASK_TYPE = "manual_test"  # Phase 3 CLI-driven runs; scheduled runs use real task_type values (§3).


class RunBrowserSessionUseCase:
    """One full lifecycle: resolve Target/Task -> create TaskRun (queued) ->
    select proxy -> run the browser session with retry+circuit-breaker
    (§7) -> persist the terminal result (§5.2, §5.5). `execute()` is the
    ad-hoc/CLI entry (Phase 3); `execute_for_task()` is what the Phase 4
    scheduler/task-runner calls for an already-existing Task."""

    def __init__(
        self,
        engine: BrowserEngine,
        target_repo: TargetRepository,
        task_repo: TaskRepository,
        task_run_repo: TaskRunRepository,
        proxy_manager: ProxyManager | None,
        *,
        circuit_registry: CircuitBreakerRegistry | None = None,
        status_store: StatusStorePort | None = None,
        preview_store: PreviewStorePort | None = None,
        max_retries: int = 2,
        retry_base_delay: float = 1.0,
    ) -> None:
        self._engine = engine
        self._target_repo = target_repo
        self._task_repo = task_repo
        self._task_run_repo = task_run_repo
        self._proxy_manager = proxy_manager
        self._circuit_registry = circuit_registry or default_registry
        self._status_store = status_store
        self._preview_store = preview_store
        self._max_retries = max_retries
        self._retry_base_delay = retry_base_delay

    async def _push_status(self, task_run: TaskRun, task: Task) -> None:
        """§5.5 — live status for the dashboard WebSocket. A no-op when no
        status_store was wired in (e.g. Phase 3/4 CLI usage)."""
        if self._status_store is None:
            return
        await self._status_store.set(
            task_run.id,
            {
                "task_run_id": str(task_run.id),
                "task_id": str(task.id),
                "status": task_run.status,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            },
        )

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
        return await self._run_task(task, target, use_proxy=use_proxy, take_screenshot=take_screenshot)

    async def execute_for_task(self, task_id: uuid.UUID, *, use_proxy: bool = True, take_screenshot: bool = False) -> TaskRun:
        """Scheduler/task-runner entry point (§Phase 4) — the Task already
        exists (created ahead of time via the CLI/API), we just run it."""
        task = await self._task_repo.get(task_id)
        if task is None:
            raise ValueError(f"Task {task_id} not found")
        target = await self._target_repo.get(task.target_id)
        if target is None:
            raise ValueError(f"Target {task.target_id} not found")
        return await self._run_task(task, target, use_proxy=use_proxy, take_screenshot=take_screenshot)

    async def _run_task(self, task: Task, target: Target, *, use_proxy: bool, take_screenshot: bool) -> TaskRun:
        proxy = None
        if use_proxy and self._proxy_manager is not None:
            proxy = await self._proxy_manager.select_proxy_with_secret()

        task_run = await self._task_run_repo.create(TaskRun(task_id=task.id, proxy_id=proxy.id if proxy else None))
        await self._push_status(task_run, task)

        await self._task_run_repo.mark_running(task_run.id, datetime.now(timezone.utc))
        task_run.status = "running"
        await self._push_status(task_run, task)

        # §Product-readiness — dashboard-managed credentials (never in code/.env).
        # Decrypted here, held only in this local variable, passed straight
        # through to the engine; never logged, never persisted anywhere.
        credentials, login_selectors = self._decrypt_target_credentials(target)

        result, attempts = await self._run_with_resilience(
            target.base_url, target.id, proxy, take_screenshot, credentials, login_selectors, task_run.id
        )
        task_run.retry_count = attempts - 1  # attempts includes the first try

        if proxy is not None and self._proxy_manager is not None:
            await self._proxy_manager.record_result(proxy.id, success=result.success, latency_ms=result.duration_ms)

        finished_at = datetime.now(timezone.utc)

        if not result.success:
            await self._task_run_repo.fail(
                task_run.id, result.error or "unknown error", finished_at, retry_count=task_run.retry_count
            )
            task_run.status = "failed"
            task_run.error_message = result.error
            task_run.finished_at = finished_at
            await self._push_status(task_run, task)
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
        await self._push_status(task_run, task)
        return task_run

    @staticmethod
    def _decrypt_target_credentials(target: Target) -> tuple[dict | None, dict | None]:
        """Reads `target.config.credentials_encrypted` (set via
        PATCH /api/targets/{id}/credentials, §Product-readiness), decrypts it
        if present. Never raises on a missing/absent key — most targets won't
        have credentials at all, and that's the normal case, not an error."""
        config = target.config or {}
        token = config.get("credentials_encrypted")
        if not token:
            return None, None
        try:
            credentials = decrypt_json(token)
        except Exception:
            # Deliberately no exception detail in the log — see auto_login.py
            # for the same reasoning (never risk a secret in a log line).
            logger.warning("target_credentials_decrypt_failed", target_id=str(target.id))
            return None, None
        return credentials, config.get("login_selectors")

    async def _run_with_resilience(
        self,
        url: str,
        target_id: uuid.UUID,
        proxy,
        take_screenshot: bool,
        credentials: dict | None = None,
        login_selectors: dict | None = None,
        task_run_id: uuid.UUID | None = None,
    ) -> tuple[BrowserRunResult, int]:
        """Retry with exponential backoff+jitter (§7), gated by a circuit
        breaker per target and (if used) per proxy — a target/proxy that's
        currently open gets skipped instantly instead of burning another
        attempt on something already known to be failing."""
        target_breaker = await self._circuit_registry.get(f"target:{target_id}")
        proxy_breaker = await self._circuit_registry.get(f"proxy:{proxy.id}") if proxy else None

        attempt = 0
        last_result: BrowserRunResult | None = None

        while True:
            attempt += 1
            try:
                await target_breaker.before_call()
                if proxy_breaker is not None:
                    await proxy_breaker.before_call()
            except CircuitOpenError as exc:
                last_result = BrowserRunResult(success=False, error=str(exc), duration_ms=0)
                logger.warning("browser_session_skipped_circuit_open", url=url, attempt=attempt, error=str(exc))
                return last_result, attempt

            result = await self._engine.run_session(
                url,
                proxy=proxy,
                credentials=credentials,
                login_selectors=login_selectors,
                take_screenshot=take_screenshot,
                task_run_id=task_run_id,
                preview_store=self._preview_store,
            )
            last_result = result

            if result.success:
                await target_breaker.record_success()
                if proxy_breaker is not None:
                    await proxy_breaker.record_success()
                return result, attempt

            await target_breaker.record_failure()
            if proxy_breaker is not None:
                await proxy_breaker.record_failure()

            if attempt > self._max_retries:
                return result, attempt

            backoff = compute_backoff(attempt, base_delay=self._retry_base_delay)
            logger.warning("browser_session_retrying", url=url, attempt=attempt, backoff_seconds=round(backoff, 2))
            await asyncio.sleep(backoff)


class RunBrowserBatchUseCase:
    """Fires `count` concurrent RunBrowserSessionUseCase runs against the same
    (shared) BrowserEngine — demonstrates that Semaphore(N) actually caps
    concurrency, not just that it's declared. Each concurrent run gets ITS
    OWN use-case instance (own DB session, passed in by the caller) since
    AsyncSession isn't safe to share across concurrent coroutines."""

    def __init__(self, use_cases: list[RunBrowserSessionUseCase]) -> None:
        self._use_cases = use_cases

    async def execute(self, *, url: str, use_proxy: bool = True, take_screenshot: bool = False) -> list[TaskRun]:
        return await asyncio.gather(
            *(
                uc.execute(url=url, use_proxy=use_proxy, take_screenshot=take_screenshot)
                for uc in self._use_cases
            )
        )


def make_task_execution_handler(
    engine: BrowserEngine,
    session_factory: Callable,
    circuit_registry: CircuitBreakerRegistry | None = None,
    status_store: StatusStorePort | None = None,
    preview_store: PreviewStorePort | None = None,
) -> TaskHandler:
    """Wires a TaskRunnerPort.submit()-compatible handler (§5.3): given a
    task_id, open a fresh DB session, run it through RunBrowserSessionUseCase,
    and log the outcome. This is what AsyncioTaskRunner's consumers call —
    both the Phase 4 scheduler and the Phase 5 `run-now`/`simulate-visitors`
    API endpoints submit task_ids through the same task_runner."""

    async def handler(task_id: uuid.UUID) -> None:
        async with session_factory() as session:
            proxy_manager = ProxyManager(SqlAlchemyProxyRepository(session), DbRuntimeConfigService(session))
            use_case = RunBrowserSessionUseCase(
                engine=engine,
                target_repo=SqlAlchemyTargetRepository(session),
                task_repo=SqlAlchemyTaskRepository(session),
                task_run_repo=SqlAlchemyTaskRunRepository(session),
                proxy_manager=proxy_manager,
                circuit_registry=circuit_registry,
                status_store=status_store,
                preview_store=preview_store,
            )
            task_run = await use_case.execute_for_task(task_id)
            logger.info("scheduled_task_executed", task_id=str(task_id), status=task_run.status)

    return handler
