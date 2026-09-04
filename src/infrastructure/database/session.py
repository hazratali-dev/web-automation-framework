from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.config.settings import get_settings
from src.infrastructure.database.url import to_async_url

settings = get_settings()

engine = create_async_engine(to_async_url(settings.database_url), echo=False)

AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)


async def get_db() -> AsyncIterator[AsyncSession]:
    """FastAPI dependency — yields a request-scoped AsyncSession."""
    async with AsyncSessionLocal() as session:
        yield session
