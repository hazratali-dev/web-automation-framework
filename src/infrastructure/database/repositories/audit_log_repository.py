import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.models.audit_log import AuditLog as AuditLogModel


class SqlAlchemyAuditLogRepository:
    """§8 — write path for `audit_logs`. No user/auth layer exists yet in
    this pass (§Phase 5 scope note — dashboard is currently single-user,
    unauthenticated), so `user_id` stays NULL for now; every sensitive
    dashboard action (config change, task pause/resume, credentials
    set/delete) still gets an audit row so the *what/when* is on record even
    before the *who* (JWT auth) lands."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, action: str, resource: str, extra: dict | None = None, user_id: uuid.UUID | None = None) -> None:
        row = AuditLogModel(user_id=user_id, action=action, resource=resource, extra=extra)
        self._session.add(row)
        await self._session.commit()
