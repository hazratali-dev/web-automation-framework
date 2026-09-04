import uuid
from abc import ABC, abstractmethod

from src.domain.entities.target import Target


class TargetRepository(ABC):
    @abstractmethod
    async def add(self, target: Target) -> Target: ...

    @abstractmethod
    async def get(self, target_id: uuid.UUID) -> Target | None: ...

    @abstractmethod
    async def get_by_base_url(self, base_url: str) -> Target | None: ...

    async def get_or_create(self, target: Target) -> Target:
        existing = await self.get_by_base_url(target.base_url)
        if existing is not None:
            return existing
        return await self.add(target)
