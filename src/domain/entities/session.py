import uuid
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class BrowserSession:
    """Mirrors the `sessions` table (§3) — one browser context's identity
    (fingerprint) within a task_run."""

    task_run_id: uuid.UUID
    browser_type: str  # chromium/firefox/webkit
    user_agent: str | None = None
    viewport: dict | None = None
    fingerprint_config: dict | None = None
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    created_at: datetime | None = None
