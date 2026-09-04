import uuid
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class TaskRun:
    """Mirrors the `task_runs` table (§3) — one execution of a Task."""

    task_id: uuid.UUID
    proxy_id: uuid.UUID | None = None
    status: str = "queued"  # queued/running/success/failed/retrying
    started_at: datetime | None = None
    finished_at: datetime | None = None
    duration_ms: int | None = None
    retry_count: int = 0
    error_message: str | None = None
    result: dict | None = None
    screenshot_path: str | None = None
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    created_at: datetime | None = None
