import uuid

from sqlalchemy import ForeignKey, Index, Integer, String, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.database.models.base import Base, TimestampMixin


class Task(Base, TimestampMixin):
    __tablename__ = "tasks"
    __table_args__ = (
        Index("ix_tasks_target_id_status", "target_id", "status"),
        # get_or_create() (§Phase 3/4) relies on this to survive concurrent
        # visitor batches racing to create the same (target, task_type) task.
        UniqueConstraint("target_id", "task_type", name="uq_tasks_target_id_task_type"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    target_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("targets.id"), nullable=False)
    task_type: Mapped[str] = mapped_column(String, nullable=False)  # performance_check/competitor_analysis/ux_simulation
    schedule_cron: Mapped[str | None] = mapped_column(String, nullable=True)
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=5)
    # active/paused/archived — pause/resume control, §5.3
    status: Mapped[str] = mapped_column(String, nullable=False, default="active")
