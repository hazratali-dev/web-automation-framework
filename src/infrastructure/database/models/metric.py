import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Index, Integer, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.database.models.base import Base, utcnow


class Metric(Base):
    __tablename__ = "metrics"
    __table_args__ = (Index("ix_metrics_task_run_id_metric_name", "task_run_id", "metric_name"),)

    # BIGSERIAL in the design doc; SQLite's INTEGER PRIMARY KEY autoincrements as
    # ROWID, Postgres gets an IDENTITY column — both behave as an auto BIGSERIAL.
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    task_run_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("task_runs.id"), nullable=False)
    metric_name: Mapped[str] = mapped_column(String, nullable=False)  # lcp/fcp/ttfb/cls/load_time_ms
    metric_value: Mapped[float] = mapped_column(Float, nullable=False)
    unit: Mapped[str | None] = mapped_column(String, nullable=True)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
