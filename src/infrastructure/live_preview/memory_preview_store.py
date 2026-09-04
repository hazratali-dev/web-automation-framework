import asyncio
import uuid

from src.domain.interfaces.preview_store_port import PreviewStorePort


class MemoryPreviewStore(PreviewStorePort):
    """dev's PreviewStorePort adapter — process-wide shared dict (same
    pattern as MemoryStatusStore, §5.5), so BrowserEngine's periodic
    screenshot capture and the /ws/preview endpoint see the same data
    without a broker."""

    _shared: dict[str, bytes] = {}
    _lock = asyncio.Lock()

    async def set(self, task_run_id: uuid.UUID, image_bytes: bytes) -> None:
        async with self._lock:
            self._shared[str(task_run_id)] = image_bytes

    async def get(self, task_run_id: uuid.UUID) -> bytes | None:
        async with self._lock:
            return self._shared.get(str(task_run_id))

    async def clear(self, task_run_id: uuid.UUID) -> None:
        async with self._lock:
            self._shared.pop(str(task_run_id), None)

    async def list_active_ids(self) -> list[str]:
        async with self._lock:
            return list(self._shared.keys())
