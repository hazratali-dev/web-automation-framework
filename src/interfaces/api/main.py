from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI

from src.config.settings import get_settings
from src.infrastructure.monitoring.logging_setup import configure_logging
from src.interfaces.api.routers import health

settings = get_settings()
configure_logging(settings.app_env, settings.log_level)

logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("app_starting", app_env=settings.app_env, database_url=settings.database_url)
    yield
    logger.info("app_stopping")


app = FastAPI(
    title="Web Automation Framework",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(health.router)
