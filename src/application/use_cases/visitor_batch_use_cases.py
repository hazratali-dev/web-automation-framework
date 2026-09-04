import asyncio
import uuid
from collections.abc import Awaitable, Callable

import structlog

from src.domain.entities.task_run import TaskRun
from src.domain.interfaces.preview_store_port import PreviewStorePort
from src.domain.interfaces.runtime_config_port import RuntimeConfigPort
from src.domain.interfaces.status_store_port import StatusStorePort
from src.infrastructure.browser.engine import BrowserEngine
from src.infrastructure.config.runtime_config_service import DbRuntimeConfigService
from src.infrastructure.database.repositories.proxy_repository import SqlAlchemyProxyRepository
from src.infrastructure.database.repositories.target_repository import SqlAlchemyTargetRepository
from src.infrastructure.database.repositories.task_repository import SqlAlchemyTaskRepository
from src.infrastructure.database.repositories.task_run_repository import SqlAlchemyTaskRunRepository
from src.infrastructure.proxy.manager import ProxyManager
from src.infrastructure.resilience.circuit_breaker import CircuitBreakerRegistry, default_registry

from .browser_use_cases import RunBrowserSessionUseCase

logger = structlog.get_logger(__name__)

DEFAULT_TOTAL_VISITORS = 50


class RunVisitorBatchUseCase:
    """§Appendix A.2 / §5.2 — simulates `total_visitors` real sessions,
    batched at whatever `runtime_config.max_concurrent_browsers` currently
    says (default 5 -> 10 batches of 5). The cap is re-read fresh before
    *every* batch, so a live config change (via the API in Phase 5, or the
    CLI today) reshapes the remaining batches without restarting anything."""

    def __init__(
        self,
        engine: BrowserEngine,
        session_factory: Callable,
        *,
        circuit_registry: CircuitBreakerRegistry | None = None,
        status_store: StatusStorePort | None = None,
        preview_store: PreviewStorePort | None = None,
    ) -> None:
        self._engine = engine
        self._session_factory = session_factory
        self._circuit_registry = circuit_registry or default_registry
        self._status_store = status_store
        self._preview_store = preview_store

    async def execute(
        self, *, url: str, total_visitors: int = DEFAULT_TOTAL_VISITORS, use_proxy: bool = False
    ) -> list[TaskRun]:
        """Ad-hoc/CLI entry (§Phase 4) — no existing Task, get-or-creates a
        `manual_test`-type one under the hood (same as
        RunBrowserSessionUseCase.execute())."""
        return await self._run_batches(lambda: self._run_one_visitor(url, use_proxy), total_visitors)

    async def execute_for_task(
        self, task_id: uuid.UUID, *, total_visitors: int = DEFAULT_TOTAL_VISITORS, use_proxy: bool = False
    ) -> list[TaskRun]:
        """§Phase 5 dashboard entry — "Simulate Visitors" on a specific,
        already-existing task. Every resulting task_run is recorded against
        *that* task_id, so its Run History actually shows them (rather than
        a separate synthetic "manual_test" task on the same target, which is
        what execute() would create)."""
        return await self._run_batches(lambda: self._run_one_visitor_for_task(task_id, use_proxy), total_visitors)

    async def _run_batches(self, run_one: Callable[[], Awaitable[TaskRun]], total_visitors: int) -> list[TaskRun]:
        results: list[TaskRun] = []
        remaining = total_visitors
        batch_num = 0

        while remaining > 0:
            batch_num += 1
            cap = await self._current_cap()
            self._engine.set_concurrency(cap)
            batch_size = min(cap, remaining)

            logger.info("visitor_batch_starting", batch_num=batch_num, batch_size=batch_size, cap=cap)
            batch_results = await asyncio.gather(*(run_one() for _ in range(batch_size)))
            results.extend(batch_results)
            remaining -= batch_size
            logger.info(
                "visitor_batch_completed",
                batch_num=batch_num,
                succeeded=sum(1 for r in batch_results if r.status == "success"),
                failed=sum(1 for r in batch_results if r.status != "success"),
                remaining=remaining,
            )

        return results

    async def _current_cap(self) -> int:
        async with self._session_factory() as session:
            runtime_config: RuntimeConfigPort = DbRuntimeConfigService(session)
            return await runtime_config.get_int("max_concurrent_browsers", 5)

    def _build_use_case(self, session, use_proxy: bool) -> RunBrowserSessionUseCase:
        proxy_manager = (
            ProxyManager(SqlAlchemyProxyRepository(session), DbRuntimeConfigService(session))
            if use_proxy
            else None
        )
        return RunBrowserSessionUseCase(
            engine=self._engine,
            target_repo=SqlAlchemyTargetRepository(session),
            task_repo=SqlAlchemyTaskRepository(session),
            task_run_repo=SqlAlchemyTaskRunRepository(session),
            proxy_manager=proxy_manager,
            circuit_registry=self._circuit_registry,
            status_store=self._status_store,
            preview_store=self._preview_store,
        )

    async def _run_one_visitor(self, url: str, use_proxy: bool) -> TaskRun:
        async with self._session_factory() as session:
            use_case = self._build_use_case(session, use_proxy)
            return await use_case.execute(url=url, use_proxy=use_proxy, take_screenshot=False)

    async def _run_one_visitor_for_task(self, task_id: uuid.UUID, use_proxy: bool) -> TaskRun:
        async with self._session_factory() as session:
            use_case = self._build_use_case(session, use_proxy)
            return await use_case.execute_for_task(task_id, use_proxy=use_proxy, take_screenshot=False)
