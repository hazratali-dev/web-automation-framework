def to_async_url(url: str) -> str:
    """Normalize a plain DATABASE_URL (e.g. sqlite:///local.db, postgresql://...)
    into one that uses an async DBAPI driver, so the same .env value works for
    both the app and Alembic without the user having to spell out the driver."""
    if url.startswith("sqlite://") and "+aiosqlite" not in url:
        return url.replace("sqlite://", "sqlite+aiosqlite://", 1)
    if url.startswith("postgresql://") and "+asyncpg" not in url:
        return url.replace("postgresql://", "postgresql+asyncpg://", 1)
    return url
