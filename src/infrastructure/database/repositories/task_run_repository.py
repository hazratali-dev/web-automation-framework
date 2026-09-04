import uuid
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.metric import Metric
from src.domain.entities.session import BrowserSession
from src.domain.entities.task_run import TaskRun
from src.domain.interfaces.task_run_repository import TaskRunRepository
from src.infrastructure.database.models.metric import Metric as MetricModel
from src.infrastructure.database.models.session import BrowserSession as BrowserSessionModel
from src.infrastructure.database.models.task_run import TaskRun as TaskRunModel


def _to_entity(row: TaskRunModel) -> TaskRun:
    return TaskRun(
        id=row.id,
        task_id=row.task_id,
        proxy_id=row.proxy_id,
        status=row.status,
        started_at=row.started_at,
        finished_at=row.finished_at,
        duration_ms=row.duration_ms,
        retry_count=row.retry_count,
        error_message=row.error_message,
        result=row.result,
        screenshot_path=row.screenshot_path,
        created_at=row.created_at,
    )


class SqlAlchemyTaskRunRepository(TaskRunRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, task_run: TaskRun) -> TaskRun:
        row = TaskRunModel(
            id=task_run.id,
            task_id=task_run.task_id,
            proxy_id=task_run.proxy_id,
            status=task_run.status,
            retry_count=task_run.retry_count,
        )
        self._session.add(row)
        await self._session.commit()
        await self._session.refresh(row)
        return _to_entity(row)

    async def mark_running(self, task_run_id: uuid.UUID, started_at: datetime) -> None:
        row = await self._session.get(TaskRunModel, task_run_id)
        if row is None:
            raise ValueError(f"TaskRun {task_run_id} not found")
        row.status = "running"
        row.started_at = started_at
        await self._session.commit()

    async def complete(
        self,
        task_run: TaskRun,
        sessions: list[BrowserSession],
        metrics: list[Metric],
    ) -> None:
        row = await self._session.get(TaskRunModel, task_run.id)
        if row is None:
            raise ValueError(f"TaskRun {task_run.id} not found")

        row.status = task_run.status
        row.finished_at = task_run.finished_at
        row.duration_ms = task_run.duration_ms
        row.result = task_run.result
        row.screenshot_path = task_run.screenshot_path

        for session in sessions:
            self._session.add(
                BrowserSessionModel(
                    id=session.id,
                    task_run_id=session.task_run_id,
                    browser_type=session.browser_type,
                    user_agent=session.user_agent,
                    viewport=session.viewport,
                    fingerprint_config=session.fingerprint_config,
                )
            )

        for metric in metrics:
            self._session.add(
                MetricModel(
                    task_run_id=metric.task_run_id,
                    metric_name=metric.metric_name,
                    metric_value=metric.metric_value,
                    unit=metric.unit,
                )
            )

        await self._session.commit()

    async def fail(self, task_run_id: uuid.UUID, error_message: str, finished_at: datetime) -> None:
        row = await self._session.get(TaskRunModel, task_run_id)
        if row is None:
            raise ValueError(f"TaskRun {task_run_id} not found")
        row.status = "failed"
        row.error_message = error_message
        row.finished_at = finished_at
        row.retry_count += 1
        await self._session.commit()
