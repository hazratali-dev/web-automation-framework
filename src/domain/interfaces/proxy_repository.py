import uuid
from abc import ABC, abstractmethod

from src.domain.entities.proxy import Proxy


class ProxyRepository(ABC):
    """Port — persistence for Proxy entities. Implemented by
    infrastructure/database/repositories/proxy_repository.py (SQLite dev /
    PostgreSQL prod — same adapter, dialect-agnostic, §Appendix A.1)."""

    @abstractmethod
    async def add(self, proxy: Proxy) -> Proxy: ...

    @abstractmethod
    async def get(self, proxy_id: uuid.UUID) -> Proxy | None: ...

    @abstractmethod
    async def get_with_secret(self, proxy_id: uuid.UUID) -> Proxy | None:
        """Like get(), but with the password decrypted onto the entity."""
        ...

    @abstractmethod
    async def list_active(self) -> list[Proxy]: ...

    @abstractmethod
    async def list_inactive(self) -> list[Proxy]: ...

    @abstractmethod
    async def list_all(self) -> list[Proxy]: ...

    @abstractmethod
    async def update(self, proxy: Proxy) -> None: ...
