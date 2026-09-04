import uuid

from sqlalchemy import JSON, Boolean, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.database.models.base import Base, TimestampMixin


class Target(Base, TimestampMixin):
    __tablename__ = "targets"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String, nullable=False)
    # unique: get_or_create() (§Phase 3/4) relies on this to survive concurrent
    # visitor batches racing to create the same target — see get_or_create()
    # in the repository for how the resulting IntegrityError is handled.
    base_url: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    target_type: Mapped[str] = mapped_column(String, nullable=False)  # own_site/competitor
    # Dialect-agnostic generic JSON (Postgres: JSONB, SQLite: TEXT-backed) — §3, §Appendix A.1.
    # Holds viewport / headers / timeout overrides (§5.5 run-time updatable).
    config: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
