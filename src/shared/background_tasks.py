import asyncio

import structlog

logger = structlog.get_logger(__name__)


class BackgroundTaskTracker:
    """A plain `asyncio.create_task()` result can be silently garbage-collected
    if nothing keeps a reference to it (a well-known asyncio footgun) — this
    keeps one, and logs (rather than swallows) any exception the task raises,
    since a fire-and-forget endpoint (e.g. simulate-visitors, §5.5) has no
    other way to surface a background failure."""

    def __init__(self) -> None:
        self._tasks: set[asyncio.Task] = set()

    def create(self, coro) -> asyncio.Task:
        task = asyncio.create_task(coro)
        self._tasks.add(task)
        task.add_done_callback(self._on_done)
        return task

    def _on_done(self, task: asyncio.Task) -> None:
        self._tasks.discard(task)
        if task.cancelled():
            return
        exc = task.exception()
        if exc is not None:
            logger.error("background_task_failed", error=str(exc))

    async def cancel_all(self) -> None:
        for task in list(self._tasks):
            task.cancel()
        await asyncio.gather(*self._tasks, return_exceptions=True)
