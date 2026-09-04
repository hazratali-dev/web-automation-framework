from abc import ABC, abstractmethod


class SchedulerPort(ABC):
    """§5.3 — dev: APScheduler AsyncIOScheduler, in-process
    (infrastructure/scheduler/asyncio_scheduler.py). prod: dynamic DB-driven
    Celery Beat (Phase 6)."""

    @abstractmethod
    async def start(self) -> None: ...

    @abstractmethod
    async def stop(self) -> None: ...

    @abstractmethod
    async def sync(self) -> None:
        """Re-read tasks from the DB and (re)schedule/unschedule jobs to
        match — picks up new tasks, cron changes, and pause/archive (§5.3)."""
        ...
