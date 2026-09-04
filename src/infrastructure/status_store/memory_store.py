import asyncio
import uuid

from src.domain.interfaces.status_store_port import StatusStorePort


class MemoryStatusStore(StatusStorePort):
    """dev's StatusStorePort adapter (§5.5, §Appendix A.3): a plain dict,
    shared process-wide (every instance points at the same underlying dict,
    same pattern as RuntimeConfigCache/§5.6) since the API and task execution
    run in the same process here — no cross-process boundary to cross.

    No TTL/eviction — acceptable for the ~5-10MB dev scale this is scoped
    for (§Appendix A.3); a long-lived dev server would eventually want a
    `clear()` call wired to a "clear finished" button, which is why that
    method exists on the port already."""

    _shared: dict[str, dict] = {}
    _lock = asyncio.Lock()

    async def set(self, task_run_id: uuid.UUID, status: dict) -> None:
        async with self._lock:
            self._shared[str(task_run_id)] = status

    async def get_all(self) -> dict[str, dict]:
        async with self._lock:
            return dict(self._shared)

    async def clear(self) -> None:
        async with self._lock:
            self._shared.clear()
