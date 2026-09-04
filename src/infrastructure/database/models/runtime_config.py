from datetime import datetime

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.database.models.base import Base, utcnow


class RuntimeConfig(Base):
    """Key-value store for dynamic, runtime-configurable settings — §3, §5.6.

    Default rows (seeded by the initial migration):
      max_concurrent_browsers = "5"
      proxy_strategy           = "round_robin"
      default_timeout_seconds  = "30"
    """

    __tablename__ = "runtime_config"

    key: Mapped[str] = mapped_column(String, primary_key=True)
    value: Mapped[str] = mapped_column(String, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )
