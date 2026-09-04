import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.use_cases.target_credentials_use_cases import (
    DeleteTargetCredentialsUseCase,
    SetTargetCredentialsUseCase,
)
from src.infrastructure.database.repositories.target_repository import SqlAlchemyTargetRepository
from src.infrastructure.database.session import get_db
from src.interfaces.api.schemas.target_schemas import TargetCredentialsRequest

router = APIRouter(prefix="/api/targets", tags=["targets"])


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
        await use_case.execute(target_id, body.email, body.password)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Target not found") from None


@router.delete("/{target_id}/credentials", status_code=status.HTTP_204_NO_CONTENT)
async def delete_target_credentials(target_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> None:
    use_case = DeleteTargetCredentialsUseCase(SqlAlchemyTargetRepository(db))
    try:
        await use_case.execute(target_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Target not found") from None
