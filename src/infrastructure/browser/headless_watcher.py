import asyncio
from collections.abc import Callable

import structlog

from src.infrastructure.browser.engine import BrowserEngine
from src.infrastructure.config.runtime_config_service import DbRuntimeConfigService

logger = structlog.get_logger(__name__)

POLL_INTERVAL_SECONDS = 3.0


def _parse_bool(value: str) -> bool:
    return value.strip().lower() in ("1", "true", "yes", "on")


async def watch_headless_config(engine: BrowserEngine, session_factory: Callable) -> None:
    """§UI-update — polls runtime_config.headless and applies it via
    engine.set_headless(), which itself defers the actual browser restart
    until no session is in flight. Runs for the lifetime of the app
    (cancelled in main.py's lifespan shutdown)."""
    while True:
        try:
            async with session_factory() as session:
                value = await DbRuntimeConfigService(session).get("headless", "false")
            await engine.set_headless(_parse_bool(value))
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("headless_watcher_tick_failed")
        await asyncio.sleep(POLL_INTERVAL_SECONDS)
