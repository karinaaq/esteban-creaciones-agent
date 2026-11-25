"""OpenTelemetry (SDK OSS + exporters gratis: console / OTLP → Jaeger local)."""

from app.observability.metrics import (
    record_chat,
    record_guardrail_block,
    record_llm_tokens,
)
from app.observability.payloads import set_span_io
from app.observability.setup import setup_observability, shutdown_observability
from app.observability.tracing import get_tracer, set_span_error

__all__ = [
    "get_tracer",
    "set_span_error",
    "set_span_io",
    "setup_observability",
    "shutdown_observability",
    "record_chat",
    "record_guardrail_block",
    "record_llm_tokens",
]
