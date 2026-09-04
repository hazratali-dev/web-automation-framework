from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.interfaces.runtime_config_port import RuntimeConfigPort
from src.infrastructure.database.models.runtime_config import RuntimeConfig as RuntimeConfigModel


class DbRuntimeConfigService(RuntimeConfigPort):
    """Phase 2: direct DB read/write on every call — correct, but not cheap if
    called on every single proxy selection under high load. Phase 4 adds a
    write-through in-memory cache behind this same interface (§5.6); nothing
    that depends on RuntimeConfigPort needs to change when that lands."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, key: str, default: str | None = None) -> str | None:
        row = await self._session.get(RuntimeConfigModel, key)
        return row.value if row is not None else default

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
