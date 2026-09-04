import uuid
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Proxy:
    """Framework-agnostic proxy entity — mirrors the `proxies` table (§3),
    but knows nothing about SQLAlchemy/Playwright/Celery."""

    host: str
    port: int
    protocol: str = "http"  # "http" or "socks5"
    username: str | None = None
    password: str | None = None  # plaintext in-memory only; encrypted at rest (§8)
    provider: str | None = None
    country: str | None = None
    is_active: bool = True
    consecutive_failures: int = 0
    success_count: int = 0
    failure_count: int = 0
    avg_latency_ms: int | None = None
    last_checked_at: datetime | None = None
    id: uuid.UUID = field(default_factory=uuid.uuid4)
    created_at: datetime | None = None

    @property
    def success_rate(self) -> float:
        total = self.success_count + self.failure_count
        if total == 0:
            return 1.0  # no history yet — give new proxies a fair chance (§5.1)
        return self.success_count / total

    def proxy_url(self) -> str:
        """httpx-style proxy URL, e.g. http://user:pass@host:port."""
        auth = f"{self.username}:{self.password}@" if self.username else ""
        return f"{self.protocol}://{auth}{self.host}:{self.port}"

    def record_success(self, latency_ms: int) -> None:
        self.success_count += 1
        self.consecutive_failures = 0
        self.avg_latency_ms = latency_ms
        self.is_active = True

    def record_failure(self, *, deactivate_after: int = 3) -> None:
        self.failure_count += 1
        self.consecutive_failures += 1
        if self.consecutive_failures >= deactivate_after:
            self.is_active = False  # soft-delete, §5.1
