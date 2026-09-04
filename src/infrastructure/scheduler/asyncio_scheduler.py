import uuid
from collections.abc import Callable

import structlog
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from src.domain.interfaces.scheduler_port import SchedulerPort
from src.domain.interfaces.task_runner_port import TaskRunnerPort
from src.infrastructure.database.repositories.task_repository import SqlAlchemyTaskRepository

logger = structlog.get_logger(__name__)

SYNC_INTERVAL_SECONDS = 60.0


class AsyncioScheduler(SchedulerPort):
    """dev's SchedulerPort adapter (§5.3, §Appendix A.4): APScheduler's
    `AsyncIOScheduler` running one cron job per active, schedule_cron-having
    Task, in this same process. A periodic `sync()` job keeps that job list
    matched to the DB (new tasks, cron edits, pause/archive) without needing
    an API push to tell it something changed."""

    def __init__(self, session_factory: Callable, task_runner: TaskRunnerPort) -> None:
        self._session_factory = session_factory
        self._task_runner = task_runner
        self._scheduler = AsyncIOScheduler()
        self._scheduled_task_ids: set[uuid.UUID] = set()

    async def start(self) -> None:
        await self.sync()
        self._scheduler.add_job(
            self.sync, "interval", seconds=SYNC_INTERVAL_SECONDS, id="__sync__", replace_existing=True
        )
        self._scheduler.start()
        logger.info("scheduler_started")

    async def stop(self) -> None:
        self._scheduler.shutdown(wait=False)
        logger.info("scheduler_stopped")

    async def sync(self) -> None:
        async with self._session_factory() as session:
            tasks = await SqlAlchemyTaskRepository(session).list_scheduled()

        current_ids = {task.id for task in tasks}

        # Drop jobs for tasks that got paused/archived/deleted since the last sync.
        for stale_id in self._scheduled_task_ids - current_ids:
            self._scheduler.remove_job(str(stale_id))
        removed = self._scheduled_task_ids - current_ids

        for task in tasks:
            self._scheduler.add_job(
                self._trigger,
                CronTrigger.from_crontab(task.schedule_cron),
                id=str(task.id),
                args=[task.id],
                replace_existing=True,  # picks up a changed schedule_cron too
            )

        self._scheduled_task_ids = current_ids
        logger.info("scheduler_synced", scheduled=len(current_ids), removed=len(removed))

    async def _trigger(self, task_id: uuid.UUID) -> None:
        # Re-check status fresh — it may have been paused after this job was
        # scheduled but before it actually fired (§5.3 pause/resume).
        async with self._session_factory() as session:
            task = await SqlAlchemyTaskRepository(session).get(task_id)
        if task is None or task.status != "active":
            logger.info("scheduled_trigger_skipped", task_id=str(task_id), status=task.status if task else "deleted")
            return
        logger.info("scheduled_trigger_fired", task_id=str(task_id))
        await self._task_runner.submit(task_id)
