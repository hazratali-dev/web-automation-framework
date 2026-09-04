import uuid
from abc import ABC, abstractmethod


class StatusStorePort(ABC):
    """§5.5 — dev: in-memory dict, shared process-wide (same pattern as
    RuntimeConfigCache, §5.6). prod: Redis pub/sub (Phase 6), since Celery
    workers are separate processes/containers and can't share memory."""

    @abstractmethod
    async def set(self, task_run_id: uuid.UUID, status: dict) -> None: ...

    @abstractmethod
    async def get_all(self) -> dict[str, dict]: ...

    @abstractmethod
    async def clear(self) -> None: ...
