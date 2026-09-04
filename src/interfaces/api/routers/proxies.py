import uuid

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.proxy import Proxy
from src.infrastructure.database.repositories.proxy_repository import SqlAlchemyProxyRepository
from src.infrastructure.database.session import get_db

router = APIRouter(prefix="/api/proxies", tags=["proxies"])


class ProxyResponse(BaseModel):
    id: uuid.UUID
    host: str
    port: int
    protocol: str
    provider: str | None
    country: str | None
    is_active: bool
    consecutive_failures: int
    success_count: int
    failure_count: int
    success_rate: float
    avg_latency_ms: int | None


def _to_response(proxy: Proxy) -> ProxyResponse:
    return ProxyResponse(
        id=proxy.id,
        host=proxy.host,
        port=proxy.port,
        protocol=proxy.protocol,
        provider=proxy.provider,
        country=proxy.country,
        is_active=proxy.is_active,
        consecutive_failures=proxy.consecutive_failures,
        success_count=proxy.success_count,
        failure_count=proxy.failure_count,
        success_rate=proxy.success_rate,
        avg_latency_ms=proxy.avg_latency_ms,
    )


@router.get("", response_model=list[ProxyResponse])
async def list_proxies(db: AsyncSession = Depends(get_db)) -> list[ProxyResponse]:
    """§5.5 — proxy pool status view. Never returns credentials (username/
    password are not part of the Proxy entity's default read path, §8)."""
    repo = SqlAlchemyProxyRepository(db)
    return [_to_response(p) for p in await repo.list_all()]
