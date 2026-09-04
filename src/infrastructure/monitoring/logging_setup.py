import logging

import structlog
from rich.logging import RichHandler


def configure_logging(app_env: str = "local", log_level: str = "INFO") -> None:
    """Configure structlog to render through stdlib logging.

    dev (app_env == "local"): colored, human-readable console output via
    rich.logging.RichHandler — see ARCHITECTURE.md §Appendix A.5.
    prod: JSON lines (Loki/Promtail-friendly) — §5.4.
    """

    shared_processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]

    structlog.configure(
        processors=shared_processors + [structlog.stdlib.ProcessorFormatter.wrap_for_formatter],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    if app_env == "local":
        # RichHandler already colors/formats the line, so keep the renderer plain.
        renderer: structlog.types.Processor = structlog.dev.ConsoleRenderer(colors=False)
        handler: logging.Handler = RichHandler(
            rich_tracebacks=True,
            show_time=False,
            show_path=False,
            markup=False,
        )
    else:
        renderer = structlog.processors.JSONRenderer()
        handler = logging.StreamHandler()

    handler.setFormatter(structlog.stdlib.ProcessorFormatter(processor=renderer))

    root_logger = logging.getLogger()
    root_logger.handlers = [handler]
    root_logger.setLevel(log_level)

    # Quiet down noisy third-party loggers at INFO.
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
