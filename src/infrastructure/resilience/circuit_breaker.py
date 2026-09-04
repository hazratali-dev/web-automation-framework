import asyncio
import time
from enum import Enum

import structlog

logger = structlog.get_logger(__name__)


class CircuitState(str, Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitOpenError(Exception):
    """Raised instead of attempting a call while the breaker is open (§7)."""


class AsyncCircuitBreaker:
    """A small, dependency-free async circuit breaker (§7 — "pybreaker-জাতীয়
    লাইব্রেরি"; implemented directly here rather than the `pybreaker` package
    itself, since its async support is inconsistent across versions and this
    state machine is simple enough to own outright).

    CLOSED -> (fail_max consecutive failures) -> OPEN
    OPEN -> (reset_timeout elapses) -> HALF_OPEN (next call is a probe)
    HALF_OPEN -> success -> CLOSED ; HALF_OPEN -> failure -> OPEN
    """

    def __init__(self, fail_max: int = 3, reset_timeout: float = 30.0) -> None:
        self._fail_max = fail_max
        self._reset_timeout = reset_timeout
        self._failure_count = 0
        self._state = CircuitState.CLOSED
        self._opened_at: float | None = None
        self._lock = asyncio.Lock()

    @property
    def state(self) -> CircuitState:
        if self._state == CircuitState.OPEN and self._opened_at is not None:
            if time.monotonic() - self._opened_at >= self._reset_timeout:
                return CircuitState.HALF_OPEN
        return self._state

    async def before_call(self) -> None:
        """Call before attempting the guarded operation. Raises
        CircuitOpenError if the breaker hasn't cooled down yet."""
        async with self._lock:
            if self.state == CircuitState.OPEN:
                raise CircuitOpenError(
                    f"circuit open ({self._failure_count} consecutive failures) — "
                    f"cooling down for {self._reset_timeout}s"
                )

    async def record_success(self) -> None:
        async with self._lock:
            if self._state != CircuitState.CLOSED:
                logger.info("circuit_breaker_closed", previous_state=self._state.value)
            self._failure_count = 0
            self._state = CircuitState.CLOSED
            self._opened_at = None

    async def record_failure(self) -> None:
        async with self._lock:
            self._failure_count += 1
            currently_half_open = self.state == CircuitState.HALF_OPEN
            if self._failure_count >= self._fail_max or currently_half_open:
                if self._state != CircuitState.OPEN:
                    logger.warning(
                        "circuit_breaker_opened",
                        failure_count=self._failure_count,
                        reset_timeout=self._reset_timeout,
                    )
                self._state = CircuitState.OPEN
                self._opened_at = time.monotonic()


class CircuitBreakerRegistry:
    """One breaker per key (`proxy:{id}` / `target:{id}`, §7) — created
    lazily and shared process-wide, similar in spirit to the runtime_config
    cache (§5.6)."""

    def __init__(self, fail_max: int = 3, reset_timeout: float = 30.0) -> None:
        self._fail_max = fail_max
        self._reset_timeout = reset_timeout
        self._breakers: dict[str, AsyncCircuitBreaker] = {}
        self._lock = asyncio.Lock()

    async def get(self, key: str) -> AsyncCircuitBreaker:
        async with self._lock:
            if key not in self._breakers:
                self._breakers[key] = AsyncCircuitBreaker(self._fail_max, self._reset_timeout)
            return self._breakers[key]


# Process-wide default, mirroring runtime_config_service's shared cache pattern.
default_registry = CircuitBreakerRegistry()
