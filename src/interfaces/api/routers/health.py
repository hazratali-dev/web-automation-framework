from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.settings import Settings, get_settings
from src.infrastructure.database.session import get_db

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check(
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict:
    """Liveness + DB-connectivity check — the Phase 1 exit criterion."""
    try:
        await db.execute(text("SELECT 1"))
        database_status = "ok"
    except Exception:  # pragma: no cover - defensive, DB is expected to be up
        database_status = "unreachable"

    return {
        "status": "ok",
        "app_env": settings.app_env,
        "database": database_status,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
