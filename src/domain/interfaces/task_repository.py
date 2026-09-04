import uuid
from abc import ABC, abstractmethod

from src.domain.entities.task import Task


class TaskRepository(ABC):
    @abstractmethod
    async def add(self, task: Task) -> Task: ...

    @abstractmethod
    async def get(self, task_id: uuid.UUID) -> Task | None: ...

    @abstractmethod
    async def get_by_target_and_type(self, target_id: uuid.UUID, task_type: str) -> Task | None: ...

    async def get_or_create(self, task: Task) -> Task:
        existing = await self.get_by_target_and_type(task.target_id, task.task_type)
        if existing is not None:
            return existing
        return await self.add(task)
