import logging
import sys
from typing import Any, Dict
import structlog
from app.core.config import settings


def setup_structured_logging() -> None:
    """
    Configure structured JSON logging across the application using structlog.
    Ensures standard logging and uvicorn loggers output structured JSON when not in debug debug-console mode.
    """
    shared_processors: list[Any] = [
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
    ]

    if settings.ENVIRONMENT == "production":
        # Production JSON structured logs
        renderer = structlog.processors.JSONRenderer()
    else:
        # Development human-readable console logs with colors
        renderer = structlog.dev.ConsoleRenderer(colors=True)

    structlog.configure(
        processors=shared_processors + [renderer],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=logging.DEBUG if settings.DEBUG else logging.INFO,
    )


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """
    Get a structured bound logger instance for a given module name.
    """
    return structlog.get_logger(name)
