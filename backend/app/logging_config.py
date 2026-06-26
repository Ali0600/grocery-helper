"""Central logging setup. Call :func:`configure_logging` once at startup.

Plain stdout logging (Render captures stdout); level via the ``LOG_LEVEL`` env.
Kept dependency-free. Scrapers/locator use module loggers
(``logging.getLogger(__name__)``) so a swallowed live-scrape failure is visible
in the logs instead of silently degrading to sample data.
"""
from __future__ import annotations

from logging.config import dictConfig

from .core.config import settings


def configure_logging() -> None:
    dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "default": {
                    "format": "%(asctime)s %(levelname)-7s %(name)s | %(message)s",
                    "datefmt": "%Y-%m-%dT%H:%M:%S%z",
                },
            },
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "formatter": "default",
                    "stream": "ext://sys.stdout",
                },
            },
            # App + third-party loggers propagate to root; uvicorn keeps its own
            # handlers (propagate=False), so this won't double-log access lines.
            "root": {"handlers": ["console"], "level": settings.log_level.upper()},
        }
    )
