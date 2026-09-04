import uuid

import structlog
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.target import Target
from src.domain.interfaces.target_repository import TargetRepository
from src.infrastructure.database.models.target import Target as TargetModel

logger = structlog.get_logger(__name__)


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
        row = result.scalars().first()
        return _to_entity(row) if row else None

    async def update_config(self, target_id: uuid.UUID, config: dict) -> None:
        row = await self._session.get(TargetModel, target_id)
        if row is None:
            raise ValueError(f"Target {target_id} not found")
        row.config = config
        await self._session.commit()

    async def get_or_create(self, target: Target) -> Target:
        """Overrides the ABC's naive check-then-act default: concurrent
        visitor-batch sessions (§Phase 4) can race here, both seeing "not
        found" and both trying to insert. The `base_url` unique constraint
        turns the loser's insert into an IntegrityError instead of a silent
        duplicate row — we catch that and just fetch what the winner created."""
        existing = await self.get_by_base_url(target.base_url)
        if existing is not None:
            return existing
        try:
            return await self.add(target)
        except IntegrityError:
            await self._session.rollback()
            logger.info("target_get_or_create_race_resolved", base_url=target.base_url)
            existing = await self.get_by_base_url(target.base_url)
            if existing is None:
                raise
            return existing
