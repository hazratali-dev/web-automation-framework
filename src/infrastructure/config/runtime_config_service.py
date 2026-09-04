import asyncio

from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.interfaces.runtime_config_port import RuntimeConfigPort
from src.infrastructure.database.models.runtime_config import RuntimeConfig as RuntimeConfigModel


class RuntimeConfigCache:
    """Process-wide write-through cache (§5.6) shared by every
    DbRuntimeConfigService instance, regardless of which DB session
    constructed it — so a config write from one request/batch is visible to
    every other concurrent reader immediately, no TTL lag."""

    def __init__(self) -> None:
        self._values: dict[str, str] = {}
        self._lock = asyncio.Lock()

    async def get(self, key: str) -> str | None:
        async with self._lock:
            return self._values.get(key)

    async def set(self, key: str, value: str) -> None:
        async with self._lock:
            self._values[key] = value


# Shared across all DbRuntimeConfigService instances in this process (§5.6).
_shared_cache = RuntimeConfigCache()


class DbRuntimeConfigService(RuntimeConfigPort):
    """Phase 2 was a direct DB read/write on every call. Phase 4 adds the
    write-through cache in front of it (§5.6) — same public interface, so
    Proxy Manager / Browser Engine / Scheduler code that already depends on
    RuntimeConfigPort needed zero changes."""

    def __init__(self, session: AsyncSession, cache: RuntimeConfigCache | None = None) -> None:
        self._session = session
        self._cache = cache or _shared_cache

    async def get(self, key: str, default: str | None = None) -> str | None:
        cached = await self._cache.get(key)
        if cached is not None:
            return cached
        row = await self._session.get(RuntimeConfigModel, key)
        if row is None:
            return default
        await self._cache.set(key, row.value)
        return row.value

    async def get_int(self, key: str, default: int) -> int:
        value = await self.get(key)
        if value is None:
            return default
        try:
            return int(value)
        except ValueError:
            return default

    async def set(self, key: str, value: str) -> None:
        row = await self._session.get(RuntimeConfigModel, key)
        if row is None:
            row = RuntimeConfigModel(key=key, value=value)
            self._session.add(row)
        else:
            row.value = value
        await self._session.commit()
        # Write-through: DB commit above, then cache — never the other way
        # round, so a reader can never observe the cache ahead of the DB.
        await self._cache.set(key, value)
