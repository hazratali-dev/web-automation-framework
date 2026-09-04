from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.config.runtime_config_service import DbRuntimeConfigService
from src.infrastructure.database.repositories.audit_log_repository import SqlAlchemyAuditLogRepository
from src.infrastructure.database.session import get_db
from src.interfaces.api.schemas.config_schemas import RuntimeConfigItem, RuntimeConfigUpdateRequest

router = APIRouter(prefix="/api/config", tags=["config"])


@router.get("", response_model=list[RuntimeConfigItem])
async def list_config(db: AsyncSession = Depends(get_db)) -> list[RuntimeConfigItem]:
    """§5.5, §5.6 — every runtime_config key/value (concurrency cap, proxy
    strategy, default timeout)."""
    service = DbRuntimeConfigService(db)
    return [RuntimeConfigItem(key=k, value=v) for k, v in sorted((await service.list_all()).items())]


@router.patch("/{key}", response_model=RuntimeConfigItem)
async def update_config(key: str, body: RuntimeConfigUpdateRequest, db: AsyncSession = Depends(get_db)) -> RuntimeConfigItem:
    """§5.6 — write-through: DB + shared cache both updated before this
    returns, so the very next batch/proxy-selection sees the new value
    (§5.2/§5.1 timing table)."""
    service = DbRuntimeConfigService(db)
    await service.set(key, body.value)

    await SqlAlchemyAuditLogRepository(db).add(
        action="update_runtime_config", resource=f"config:{key}", extra={"value": body.value}
    )

    return RuntimeConfigItem(key=key, value=body.value)
