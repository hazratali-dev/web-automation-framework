import uuid
from abc import ABC, abstractmethod
from datetime import datetime

from src.domain.entities.metric import Metric
from src.domain.entities.session import BrowserSession
from src.domain.entities.task_run import TaskRun


class TaskRunRepository(ABC):
    """§5.2 lifecycle: create (queued) -> mark_running -> complete/fail.
    complete()/fail() persist the terminal state; complete() also bulk-writes
    the child BrowserSession + Metric rows produced by the run."""

    @abstractmethod
    async def create(self, task_run: TaskRun) -> TaskRun: ...

    @abstractmethod
    async def mark_running(self, task_run_id: uuid.UUID, started_at: datetime) -> None: ...

    @abstractmethod
    async def complete(
        self,
        task_run: TaskRun,
        sessions: list[BrowserSession],
        metrics: list[Metric],
    ) -> None: ...

    @abstractmethod
    async def fail(self, task_run_id: uuid.UUID, error_message: str, finished_at: datetime) -> None: ...
