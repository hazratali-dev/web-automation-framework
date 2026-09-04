import uuid
from abc import ABC, abstractmethod


class PreviewStorePort(ABC):
    """§Live-preview — holds the latest screenshot bytes for each currently
    running browser session, keyed by task_run_id. Same in-memory-dict
    pattern as StatusStorePort (§5.5) — dev-only, process-wide shared."""

    @abstractmethod
    async def set(self, task_run_id: uuid.UUID, image_bytes: bytes) -> None: ...

    @abstractmethod
    async def get(self, task_run_id: uuid.UUID) -> bytes | None: ...

    @abstractmethod
    async def clear(self, task_run_id: uuid.UUID) -> None: ...

    @abstractmethod
    async def list_active_ids(self) -> list[str]: ...
