import asyncio
import contextlib
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.application.use_cases.browser_use_cases import make_task_execution_handler
from src.config.settings import get_settings
from src.infrastructure.browser.engine import BrowserEngine
from src.infrastructure.browser.headless_watcher import watch_headless_config
from src.infrastructure.config.runtime_config_service import DbRuntimeConfigService
from src.infrastructure.database.session import AsyncSessionLocal
from src.infrastructure.live_preview.memory_preview_store import MemoryPreviewStore
from src.infrastructure.monitoring.logging_setup import configure_logging
from src.infrastructure.resilience.circuit_breaker import CircuitBreakerRegistry
from src.infrastructure.scheduler.asyncio_scheduler import AsyncioScheduler
from src.infrastructure.status_store.memory_store import MemoryStatusStore
from src.infrastructure.task_runner.asyncio_runner import AsyncioTaskRunner
from src.interfaces.api import websocket
from src.interfaces.api.routers import config, health, metrics, proxies, targets, tasks
from src.shared.background_tasks import BackgroundTaskTracker

settings = get_settings()
configure_logging(settings.app_env, settings.log_level)

logger = structlog.get_logger(__name__)


async def _initial_headless_value() -> bool:
    """Reads runtime_config.headless once at startup so the engine launches
    with the dashboard's last-set preference instead of always defaulting
    (§UI-update); the headless_watcher background task keeps it in sync
    after that."""
    async with AsyncSessionLocal() as session:
        value = await DbRuntimeConfigService(session).get("headless", "false")
    return (value or "false").strip().lower() in ("1", "true", "yes", "on")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """§5.5 — the whole framework runs in this one uvicorn process (§Appendix
    A): the BrowserEngine, the asyncio task_runner/scheduler from Phase 4, and
    the in-memory status/preview stores all start here once and live on
    app.state for every request/WebSocket handler to share."""
    logger.info("app_starting", app_env=settings.app_env, database_url=settings.database_url)

    engine = BrowserEngine(headless=await _initial_headless_value())
    await engine.start()

    status_store = MemoryStatusStore()
    preview_store = MemoryPreviewStore()
    circuit_registry = CircuitBreakerRegistry()

    handler = make_task_execution_handler(
        engine,
        AsyncSessionLocal,
        circuit_registry=circuit_registry,
        status_store=status_store,
        preview_store=preview_store,
    )
    task_runner = AsyncioTaskRunner(handler)
    await task_runner.start()

    scheduler = AsyncioScheduler(AsyncSessionLocal, task_runner)
    await scheduler.start()

    headless_watcher_task = asyncio.create_task(watch_headless_config(engine, AsyncSessionLocal))

    app.state.engine = engine
    app.state.status_store = status_store
    app.state.preview_store = preview_store
    app.state.circuit_registry = circuit_registry
    app.state.task_runner = task_runner
    app.state.scheduler = scheduler
    app.state.session_factory = AsyncSessionLocal
    app.state.background_tasks = BackgroundTaskTracker()

    yield

    headless_watcher_task.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await headless_watcher_task
    await app.state.background_tasks.cancel_all()
    await scheduler.stop()
    await task_runner.stop()
    await engine.stop()
    logger.info("app_stopping")


app = FastAPI(
    title="Web Automation Framework",
    version="0.1.0",
    lifespan=lifespan,
)

# Dashboard (Vite dev server) runs on a different origin — §Phase 5.
# Dev-only convenience list; prod (§6) serves the dashboard from behind the
# same nginx/traefik origin, so this won't even be needed there.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(targets.router)
app.include_router(tasks.router)
app.include_router(proxies.router)
app.include_router(metrics.router)
app.include_router(config.router)
app.include_router(websocket.router)
