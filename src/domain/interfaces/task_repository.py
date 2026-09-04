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

    @abstractmethod
    async def list_scheduled(self) -> list[Task]:
        """Active tasks that have a `schedule_cron` set — what the Scheduler
        (§5.3) needs to (re)sync its job list against."""
        ...

    @abstractmethod
    async def update_status(self, task_id: uuid.UUID, status: str) -> None:
        """active / paused / archived — §5.3 pause/resume."""
        ...

    @abstractmethod
    async def list_all(self, target_id: uuid.UUID | None = None) -> list[Task]:
        """§5.5 — GET /api/tasks (task list view), optionally filtered to one target."""
        ...

    async def get_or_create(self, task: Task) -> Task:
        existing = await self.get_by_target_and_type(task.target_id, task.task_type)
        if existing is not None:
            return existing
        return await self.add(task)
