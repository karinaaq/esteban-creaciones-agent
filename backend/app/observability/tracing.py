from __future__ import annotations

from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode

from app.observability.payloads import set_span_io

TRACER_NAME = "esteban.creaciones"

__all__ = ["get_tracer", "set_span_error", "set_span_io"]


def get_tracer():
    return trace.get_tracer(TRACER_NAME, "0.1.0")


def set_span_error(span, exc: BaseException) -> None:
    span.record_exception(exc)
    span.set_status(Status(StatusCode.ERROR, str(exc)[:200]))
