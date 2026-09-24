"""Structured logging via structlog.

Configured once at process startup. Emits JSON in production; human-readable
key=value in development. Every log line carries request_id (and job_id /
application_id when available) so pipeline stages are correlatable.
"""

from __future__ import annotations

import logging
import sys
from typing import Any

import structlog


def configure_logging(*, json_output: bool = True, log_level: str = "INFO") -> None:
    """Configure structlog and the stdlib root logger for the process.

    Must be called once, early, in each process entrypoint (api, worker, telegram).
    """
    level = getattr(logging, log_level.upper(), logging.INFO)

    shared_processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]

    if json_output:
        renderer: structlog.types.Processor = structlog.processors.JSONRenderer()
    else:
        renderer = structlog.dev.ConsoleRenderer(colors=sys.stderr.isatty())

    structlog.configure(
        processors=[
            *shared_processors,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    formatter = structlog.stdlib.ProcessorFormatter(
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            renderer,
        ],
        foreign_pre_chain=shared_processors,
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)

    # Quiet noisy libraries.
    for name in ("httpx", "httpcore", "asyncio", "sqlalchemy.engine"):
        logging.getLogger(name).setLevel(logging.WARNING)


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    """Return a bound logger. Prefer this over logging.getLogger."""
    return structlog.get_logger(name)


def bind_context(**kwargs: Any) -> None:
    """Bind key/value pairs into the current contextvars for all subsequent logs."""
    structlog.contextvars.bind_contextvars(**kwargs)


def clear_context() -> None:
    """Clear all contextvars bindings (call at end of a request or job)."""
    structlog.contextvars.clear_contextvars()
