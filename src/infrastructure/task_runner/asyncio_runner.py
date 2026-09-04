import asyncio
import uuid

import structlog

from src.domain.interfaces.task_runner_port import TaskHandler, TaskRunnerPort

logger = structlog.get_logger(__name__)


class AsyncioTaskRunner(TaskRunnerPort):
    """dev's TaskRunnerPort adapter (§5.3, §Appendix A.4): an in-process
    `asyncio.Queue` plus a small pool of consumer coroutines. No broker, no
    separate worker process — everything runs in this one Python process."""

    def __init__(self, handler: TaskHandler, num_consumers: int = 3) -> None:
        self._handler = handler
        self._num_consumers = num_consumers
        self._queue: asyncio.Queue[uuid.UUID] = asyncio.Queue()
        self._consumers: list[asyncio.Task] = []
        self._running = False

    async def start(self) -> None:
        self._running = True
        self._consumers = [asyncio.create_task(self._consume(i)) for i in range(self._num_consumers)]
        logger.info("task_runner_started", num_consumers=self._num_consumers)

    async def stop(self) -> None:
        self._running = False
        await self._queue.join()
        for consumer in self._consumers:
            consumer.cancel()
        await asyncio.gather(*self._consumers, return_exceptions=True)
        logger.info("task_runner_stopped")

    async def submit(self, task_id: uuid.UUID) -> None:
        await self._queue.put(task_id)
        logger.info("task_submitted", task_id=str(task_id), queue_depth=self._queue.qsize())

    async def _consume(self, consumer_id: int) -> None:
        while self._running:
            try:
                task_id = await asyncio.wait_for(self._queue.get(), timeout=1.0)
            except TimeoutError:
                continue
            try:
                await self._handler(task_id)
            except Exception:
                logger.exception("task_handler_failed", task_id=str(task_id), consumer_id=consumer_id)
            finally:
                self._queue.task_done()
