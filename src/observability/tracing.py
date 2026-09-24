"""OpenTelemetry tracing setup.

Spans are created around each pipeline stage transition so per-stage latency
budgets are measurable in production. If OpenTelemetry is not installed,
falls back to no-op context managers so the rest of the system still imports.
"""

from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Any, Iterator

try:
    from opentelemetry import trace
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
    from opentelemetry.trace import Span, Status, StatusCode, Tracer

    _OTEL_AVAILABLE = True
except ImportError:  # pragma: no cover - optional dependency
    _OTEL_AVAILABLE = False
    Span = Any  # type: ignore[misc, assignment]
    Tracer = Any  # type: ignore[misc, assignment]

_tracer: Any = None


class _NoOpSpan:
    def set_attribute(self, key: str, value: Any) -> None:
        return None

    def record_exception(self, exc: BaseException) -> None:
        return None

    def set_status(self, status: Any) -> None:
        return None


def configure_tracing(
    *,
    service_name: str = "job-agent",
    enable_console_export: bool = False,
) -> None:
    """Configure the global TracerProvider. Call once at process startup."""
    global _tracer
    if not _OTEL_AVAILABLE:
        _tracer = None
        return

    resource = Resource.create(
        {
            "service.name": service_name,
            "service.version": os.environ.get("APP_VERSION", "0.1.0"),
        }
    )
    provider = TracerProvider(resource=resource)

    if enable_console_export or os.environ.get("OTEL_CONSOLE_EXPORT", "").lower() in (
        "1",
        "true",
        "yes",
    ):
        provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))

    trace.set_tracer_provider(provider)
    _tracer = trace.get_tracer(service_name)


def get_tracer() -> Any:
    """Return the process tracer, configuring a no-op provider if none exists."""
    global _tracer
    if not _OTEL_AVAILABLE:
        return None
    if _tracer is None:
        configure_tracing()
    return _tracer


@contextmanager
def span(
    name: str,
    *,
    attributes: dict[str, Any] | None = None,
    record_exception: bool = True,
) -> Iterator[Any]:
    """Context manager that creates a span for a pipeline stage."""
    tracer = get_tracer()
    if tracer is None:
        yield _NoOpSpan()
        return

    with tracer.start_as_current_span(name) as current:
        if attributes:
            for key, value in attributes.items():
                if value is not None:
                    current.set_attribute(key, value)
        try:
            yield current
        except Exception as exc:
            if record_exception:
                current.record_exception(exc)
                current.set_status(Status(StatusCode.ERROR, str(exc)))
            raise
