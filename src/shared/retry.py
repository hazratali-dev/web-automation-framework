import random


def compute_backoff(attempt: int, *, base_delay: float = 1.0, max_delay: float = 30.0) -> float:
    """Exponential backoff + jitter (§7) — `attempt` is 1-indexed (the delay
    before retry #1, retry #2, ...)."""
    delay = min(base_delay * (2 ** (attempt - 1)), max_delay)
    jitter = random.uniform(0, delay * 0.3)
    return delay + jitter
