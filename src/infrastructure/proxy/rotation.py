import random
import threading

from src.domain.entities.proxy import Proxy


class RoundRobinRotator:
    """Cycles through active proxies in a stable order. State is in-process
    memory (fine for the single-process dev/Phase-2-CLI scope, §Appendix A) —
    a distributed/persistent cursor is a later concern if multiple processes
    need a shared rotation order."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._cursor: dict[str, int] = {}

    def select(self, proxies: list[Proxy]) -> Proxy | None:
        if not proxies:
            return None
        ordered = sorted(proxies, key=lambda p: str(p.id))
        key = ",".join(str(p.id) for p in ordered)
        with self._lock:
            index = self._cursor.get(key, 0) % len(ordered)
            self._cursor[key] = index + 1
        return ordered[index]


def weighted_select(proxies: list[Proxy]) -> Proxy | None:
    """Picks a proxy at random, weighted by historical success_rate — proxies
    with no history yet default to weight 1.0 so they still get a fair chance
    (§5.1)."""
    if not proxies:
        return None
    weights = [max(p.success_rate, 0.01) for p in proxies]  # never fully zero out a proxy
    return random.choices(proxies, weights=weights, k=1)[0]


_round_robin = RoundRobinRotator()


def select_proxy(proxies: list[Proxy], strategy: str) -> Proxy | None:
    """Strategy is a plain string (`round_robin` / `weighted`) coming from
    `runtime_config.proxy_strategy` (§5.1, §5.6) — dynamic, re-read on every
    selection call, so a strategy switch takes effect immediately."""
    if strategy == "weighted":
        return weighted_select(proxies)
    return _round_robin.select(proxies)
