import uuid

from sqlalchemy import JSON, ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.database.models.base import Base, TimestampMixin


class BrowserSession(Base, TimestampMixin):
    """Maps to the `sessions` table (§3). Named BrowserSession, not Session,
    to avoid clashing with SQLAlchemy's own Session class."""

    __tablename__ = "sessions"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    task_run_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("task_runs.id"), nullable=False)
    browser_type: Mapped[str] = mapped_column(String, nullable=False)  # chromium/firefox/webkit
    user_agent: Mapped[str | None] = mapped_column(String, nullable=True)
    viewport: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    fingerprint_config: Mapped[dict | None] = mapped_column(JSON, nullable=True)
