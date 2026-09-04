import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.use_cases.target_credentials_use_cases import (
    CREDENTIALS_CONFIG_KEY,
    DeleteTargetCredentialsUseCase,
    SetTargetCredentialsUseCase,
)
from src.domain.entities.target import Target
from src.infrastructure.database.repositories.audit_log_repository import SqlAlchemyAuditLogRepository
from src.infrastructure.database.repositories.target_repository import SqlAlchemyTargetRepository
from src.infrastructure.database.repositories.task_repository import SqlAlchemyTaskRepository
from src.infrastructure.database.session import get_db
from src.interfaces.api.schemas.target_schemas import (
    TargetConfigUpdateRequest,
    TargetCreateRequest,
    TargetCredentialsRequest,
    TargetResponse,
)

router = APIRouter(prefix="/api/targets", tags=["targets"])


def _to_response(target: Target) -> TargetResponse:
    config = target.config or {}
    return TargetResponse(
        id=target.id,
        name=target.name,
        base_url=target.base_url,
        target_type=target.target_type,
        is_active=target.is_active,
        has_credentials=bool(config.get(CREDENTIALS_CONFIG_KEY)),
        created_at=target.created_at,
    )


@router.post("", status_code=status.HTTP_201_CREATED, response_model=TargetResponse)
async def create_target(body: TargetCreateRequest, db: AsyncSession = Depends(get_db)) -> TargetResponse:
    repo = SqlAlchemyTargetRepository(db)
    target = await repo.get_or_create(Target(name=body.name, base_url=body.base_url, target_type=body.target_type))
    return _to_response(target)


@router.get("", response_model=list[TargetResponse])
async def list_targets(db: AsyncSession = Depends(get_db)) -> list[TargetResponse]:
    repo = SqlAlchemyTargetRepository(db)
    return [_to_response(t) for t in await repo.list_all()]


@router.patch("/{target_id}", response_model=TargetResponse)
async def update_target(
    target_id: uuid.UUID, body: TargetConfigUpdateRequest, db: AsyncSession = Depends(get_db)
) -> TargetResponse:
    """§5.5 config (viewport/headers/timeout) + §UI-refactor basic-info edit
    (name/base_url/target_type) in one endpoint — never touches
    credentials_encrypted (that has its own dedicated endpoint below).
    Config changes are read-modify-write, so other config keys already set
    survive this update."""
    repo = SqlAlchemyTargetRepository(db)
    target = await repo.get(target_id)
    if target is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Target not found")

    if body.name is not None or body.base_url is not None or body.target_type is not None:
        await repo.update_basic_info(
            target_id, name=body.name, base_url=body.base_url, target_type=body.target_type
        )

    if body.viewport is not None or body.headers is not None or body.timeout_seconds is not None:
        config = dict(target.config or {})
        if body.viewport is not None:
            config["viewport"] = body.viewport
        if body.headers is not None:
            config["headers"] = body.headers
        if body.timeout_seconds is not None:
            config["timeout_seconds"] = body.timeout_seconds
        await repo.update_config(target_id, config)

    await SqlAlchemyAuditLogRepository(db).add(
        action="update_target", resource=f"target:{target_id}", extra=body.model_dump(exclude_none=True)
    )

    target = await repo.get(target_id)
    return _to_response(target)


@router.delete("/{target_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_target(target_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> None:
    """§UI-refactor — the Delete action in the Targets table. Refuses if any
    task still references this target (409) rather than silently cascading
    — losing task/run history by accident is worse than one extra click to
    delete the tasks first."""
    target_repo = SqlAlchemyTargetRepository(db)
    if await target_repo.get(target_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Target not found")

    existing_tasks = await SqlAlchemyTaskRepository(db).list_all(target_id)
    if existing_tasks:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Target has {len(existing_tasks)} task(s) — delete those first",
        )

    await target_repo.delete(target_id)
    await SqlAlchemyAuditLogRepository(db).add(action="delete_target", resource=f"target:{target_id}")


@router.patch("/{target_id}/credentials", status_code=status.HTTP_204_NO_CONTENT)
async def set_target_credentials(
    target_id: uuid.UUID,
    body: TargetCredentialsRequest,
    db: AsyncSession = Depends(get_db),
) -> None:
    """§Product-readiness — encrypts (Fernet) and stores login credentials
    for a target, dashboard-managed instead of code/.env. No response body,
    so credentials are never echoed back either (§8)."""
    use_case = SetTargetCredentialsUseCase(SqlAlchemyTargetRepository(db))
    try:
        await use_case.execute(target_id, body.email, body.password, body.login_type)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Target not found") from None

    # action/resource only — never the email/password (§8).
    await SqlAlchemyAuditLogRepository(db).add(
        action="set_target_credentials", resource=f"target:{target_id}", extra={"login_type": body.login_type}
    )


@router.delete("/{target_id}/credentials", status_code=status.HTTP_204_NO_CONTENT)
async def delete_target_credentials(target_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> None:
    use_case = DeleteTargetCredentialsUseCase(SqlAlchemyTargetRepository(db))
    try:
        await use_case.execute(target_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Target not found") from None

    await SqlAlchemyAuditLogRepository(db).add(action="delete_target_credentials", resource=f"target:{target_id}")
