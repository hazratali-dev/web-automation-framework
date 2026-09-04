import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.task import Task
from src.domain.interfaces.task_repository import TaskRepository
from src.infrastructure.database.models.task import Task as TaskModel


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
        row = result.scalar_one_or_none()
        return _to_entity(row) if row else None
