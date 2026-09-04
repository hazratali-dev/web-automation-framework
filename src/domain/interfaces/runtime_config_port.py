from abc import ABC, abstractmethod


class RuntimeConfigPort(ABC):
    """Port for reading/writing `runtime_config` (§3, §5.6) — dynamic settings
    like `proxy_strategy`. This minimal Phase 2 version reads straight from the
    DB on every call; Phase 4 layers a write-through in-memory cache on top of
    the same interface without touching callers (Proxy Manager, Browser Engine)."""

    @abstractmethod
    async def get(self, key: str, default: str | None = None) -> str | None: ...

    @abstractmethod
    async def get_int(self, key: str, default: int) -> int: ...

    @abstractmethod
    async def set(self, key: str, value: str) -> None: ...

    @abstractmethod
    async def list_all(self) -> dict[str, str]:
        """§5.5 — GET /api/config: every key/value currently in `runtime_config`."""
        ...
