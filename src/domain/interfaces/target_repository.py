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

    @abstractmethod
    async def list_all(self) -> list[Target]:
        """§5.5 — GET /api/targets (target list / "add target" dashboard view)."""
        ...

    @abstractmethod
    async def update_config(self, target_id: uuid.UUID, config: dict) -> None:
        """Replaces the whole `config` JSON blob (§5.5, §Product-readiness
        credentials). Callers read-modify-write via get() + this, so the
        merge logic (e.g. "just add/remove the credentials_encrypted key")
        lives at the call site, not here."""
        ...

    @abstractmethod
    async def update_basic_info(
        self,
        target_id: uuid.UUID,
        *,
        name: str | None = None,
        base_url: str | None = None,
        target_type: str | None = None,
    ) -> None:
        """§UI-refactor — the Edit action in the Targets table. Only the
        fields actually passed get changed."""
        ...

    @abstractmethod
    async def delete(self, target_id: uuid.UUID) -> None: ...

    async def get_or_create(self, target: Target) -> Target:
        existing = await self.get_by_base_url(target.base_url)
        if existing is not None:
            return existing
        return await self.add(target)
