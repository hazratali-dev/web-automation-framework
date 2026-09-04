import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.target import Target
from src.domain.interfaces.target_repository import TargetRepository
from src.infrastructure.database.models.target import Target as TargetModel


def _to_entity(row: TargetModel) -> Target:
    return Target(
        id=row.id,
        name=row.name,
        base_url=row.base_url,
        target_type=row.target_type,
        config=row.config,
        is_active=row.is_active,
        created_at=row.created_at,
    )


class SqlAlchemyTargetRepository(TargetRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, target: Target) -> Target:
        row = TargetModel(
            id=target.id,
            name=target.name,
            base_url=target.base_url,
            target_type=target.target_type,
            config=target.config,
            is_active=target.is_active,
        )
        self._session.add(row)
        await self._session.commit()
        await self._session.refresh(row)
        return _to_entity(row)

    async def get(self, target_id: uuid.UUID) -> Target | None:
        row = await self._session.get(TargetModel, target_id)
        return _to_entity(row) if row else None

    async def get_by_base_url(self, base_url: str) -> Target | None:
        result = await self._session.execute(select(TargetModel).where(TargetModel.base_url == base_url))
        row = result.scalar_one_or_none()
        return _to_entity(row) if row else None
