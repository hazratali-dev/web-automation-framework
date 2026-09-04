import uuid
from dataclasses import dataclass
from datetime import datetime


@dataclass
class Metric:
    """Mirrors the `metrics` table (§3) — one performance data point."""

    task_run_id: uuid.UUID
    metric_name: str  # lcp/fcp/ttfb/cls/load_time_ms
    metric_value: float
    unit: str | None = None
    recorded_at: datetime | None = None
    id: int | None = None
