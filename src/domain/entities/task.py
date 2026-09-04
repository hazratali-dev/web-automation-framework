import uuid
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Task:
    """Mirrors the `tasks` table (§3)."""

    target_id: uuid.UUID
    task_type: str  # performance_check / competitor_analysis / ux_simulation
    schedule_cron: str | None = None
    priority: int = 5
    status: str = "active"  # active / paused / archived — §5.3
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    created_at: datetime | None = None
