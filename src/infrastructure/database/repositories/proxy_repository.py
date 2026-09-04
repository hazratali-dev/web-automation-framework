import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.proxy import Proxy
from src.domain.interfaces.proxy_repository import ProxyRepository
from src.infrastructure.database.models.proxy import Proxy as ProxyModel
from src.infrastructure.proxy.encryption import decrypt_password, encrypt_password


def _to_entity(row: ProxyModel, *, password: str | None = None) -> Proxy:
    return Proxy(
        id=row.id,
        host=row.host,
        port=row.port,
        protocol=row.protocol,
        username=row.username,
        password=password,  # only populated when explicitly requested — §8
        provider=row.provider,
        country=row.country,
        is_active=row.is_active,
        consecutive_failures=row.consecutive_failures,
        success_count=row.success_count,
        failure_count=row.failure_count,
        avg_latency_ms=row.avg_latency_ms,
        last_checked_at=row.last_checked_at,
        created_at=row.created_at,
    )


class SqlAlchemyProxyRepository(ProxyRepository):
    """SQLite (dev) / PostgreSQL (prod) implementation of ProxyRepository —
    same code, dialect-agnostic (§Appendix A.1). Encrypts/decrypts the proxy
    password at the boundary so no other layer ever handles Fernet directly."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, proxy: Proxy) -> Proxy:
        row = ProxyModel(
            id=proxy.id,
            host=proxy.host,
            port=proxy.port,
            protocol=proxy.protocol,
            username=proxy.username,
            password_encrypted=encrypt_password(proxy.password) if proxy.password else None,
            provider=proxy.provider,
            country=proxy.country,
            is_active=proxy.is_active,
        )
        self._session.add(row)
        await self._session.commit()
        await self._session.refresh(row)
        return _to_entity(row)

    async def get(self, proxy_id: uuid.UUID) -> Proxy | None:
        row = await self._session.get(ProxyModel, proxy_id)
        return _to_entity(row) if row else None

    async def get_with_secret(self, proxy_id: uuid.UUID) -> Proxy | None:
        """Like get(), but with the password decrypted back onto the entity —
        needed to actually connect through the proxy (health checks, browser
        engine). Kept separate so ordinary reads never touch the secret."""
        row = await self._session.get(ProxyModel, proxy_id)
        if row is None:
            return None
        password = decrypt_password(row.password_encrypted) if row.password_encrypted else None
        return _to_entity(row, password=password)

    async def list_active(self) -> list[Proxy]:
        result = await self._session.execute(select(ProxyModel).where(ProxyModel.is_active.is_(True)))
        return [_to_entity(r) for r in result.scalars().all()]

    async def list_inactive(self) -> list[Proxy]:
        result = await self._session.execute(select(ProxyModel).where(ProxyModel.is_active.is_(False)))
        return [_to_entity(r) for r in result.scalars().all()]

    async def list_all(self) -> list[Proxy]:
        result = await self._session.execute(select(ProxyModel))
        return [_to_entity(r) for r in result.scalars().all()]

    async def update(self, proxy: Proxy) -> None:
        row = await self._session.get(ProxyModel, proxy.id)
        if row is None:
            raise ValueError(f"Proxy {proxy.id} not found")
        row.is_active = proxy.is_active
        row.consecutive_failures = proxy.consecutive_failures
        row.success_count = proxy.success_count
        row.failure_count = proxy.failure_count
        row.avg_latency_ms = proxy.avg_latency_ms
        row.last_checked_at = proxy.last_checked_at
        await self._session.commit()
