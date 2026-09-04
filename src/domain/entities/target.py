import uuid
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Target:
    """Mirrors the `targets` table (§3) — a site to monitor/analyze/simulate."""

    name: str
    base_url: str
    target_type: str = "own_site"  # own_site / competitor
    config: dict | None = None  # viewport, headers, timeout overrides — §5.5
    is_active: bool = True
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    created_at: datetime | None = None
