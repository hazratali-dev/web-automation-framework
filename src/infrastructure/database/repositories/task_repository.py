import uuid

import structlog
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.task import Task
from src.domain.interfaces.task_repository import TaskRepository
from src.infrastructure.database.models.task import Task as TaskModel

logger = structlog.get_logger(__name__)


def _to_entity(row: TaskModel) -> Task:
    return Task(
        id=row.id,
        target_id=row.target_id,
        task_type=row.task_type,
        schedule_cron=row.schedule_cron,
        priority=row.priority,
        status=row.status,
        created_at=row.created_at,
    )


class SqlAlchemyTaskRepository(TaskRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, task: Task) -> Task:
        row = TaskModel(
            id=task.id,
            target_id=task.target_id,
            task_type=task.task_type,
            schedule_cron=task.schedule_cron,
            priority=task.priority,
            status=task.status,
        )
        self._session.add(row)
        await self._session.commit()
        await self._session.refresh(row)
        return _to_entity(row)

    async def get(self, task_id: uuid.UUID) -> Task | None:
        row = await self._session.get(TaskModel, task_id)
        return _to_entity(row) if row else None

    async def get_by_target_and_type(self, target_id: uuid.UUID, task_type: str) -> Task | None:
        result = await self._session.execute(
            select(TaskModel).where(TaskModel.target_id == target_id, TaskModel.task_type == task_type)
        )
        row = result.scalars().first()
        return _to_entity(row) if row else None

    async def get_or_create(self, task: Task) -> Task:
        """See SqlAlchemyTargetRepository.get_or_create — same concurrent
        visitor-batch race, resolved the same way via the
        (target_id, task_type) unique constraint."""
        existing = await self.get_by_target_and_type(task.target_id, task.task_type)
        if existing is not None:
            return existing
        try:
            return await self.add(task)
        except IntegrityError:
            await self._session.rollback()
            logger.info("task_get_or_create_race_resolved", target_id=str(task.target_id), task_type=task.task_type)
            existing = await self.get_by_target_and_type(task.target_id, task.task_type)
            if existing is None:
                raise
            return existing

    async def list_scheduled(self) -> list[Task]:
        result = await self._session.execute(
            select(TaskModel).where(TaskModel.status == "active", TaskModel.schedule_cron.is_not(None))
        )
        return [_to_entity(r) for r in result.scalars().all()]

    async def update_status(self, task_id: uuid.UUID, status: str) -> None:
        row = await self._session.get(TaskModel, task_id)
        if row is None:
            raise ValueError(f"Task {task_id} not found")
        row.status = status
        await self._session.commit()

    async def list_all(self, target_id: uuid.UUID | None = None) -> list[Task]:
        query = select(TaskModel)
        if target_id is not None:
            query = query.where(TaskModel.target_id == target_id)
        result = await self._session.execute(query)
        return [_to_entity(r) for r in result.scalars().all()]
