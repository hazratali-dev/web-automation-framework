import uuid
from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable

TaskHandler = Callable[[uuid.UUID], Awaitable[None]]


class TaskRunnerPort(ABC):
    """§5.3 — dev: in-process asyncio.Queue + consumer coroutines
    (infrastructure/task_runner/asyncio_runner.py). prod: Celery worker pool
    (Phase 6). Same port, so the scheduler and application code that submits
    work don't know or care which one is running underneath."""

    @abstractmethod
    async def start(self) -> None: ...

    @abstractmethod
    async def stop(self) -> None: ...

    @abstractmethod
    async def submit(self, task_id: uuid.UUID) -> None: ...
