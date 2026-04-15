# backend/app/core/logging.py
"""Structured logging configuration using structlog."""

import logging

import structlog


def configure_logging() -> None:
    """
    Configure structlog for the application.

    - Development: ConsoleRenderer (human-readable), DEBUG level
    - Production:  JSONRenderer (machine-parseable for log aggregators), INFO level

    JSON output in production is required for Railway / Datadog log parsing.
    Do not switch to ConsoleRenderer in production — fields will be lost.
    """
    # Import here to avoid a circular import at module load time
    # (config imports nothing from logging, but logging must not be imported
    #  before settings are populated in some startup orderings).
    from backend.app.core.config import settings

    min_level = logging.DEBUG if not settings.is_production else logging.INFO

    shared_processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.StackInfoRenderer(),
    ]

    if settings.is_production:
        shared_processors.append(structlog.processors.JSONRenderer())
    else:
        shared_processors.append(structlog.dev.ConsoleRenderer())

    structlog.configure(
        processors=shared_processors,
        wrapper_class=structlog.make_filtering_bound_logger(min_level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """Get a named logger instance."""
    return structlog.get_logger(name)  # type: ignore[no-any-return]
