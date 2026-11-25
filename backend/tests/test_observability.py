from app.config import Settings
from app.observability import get_tracer, setup_observability, shutdown_observability
from app.observability.metrics import record_chat, record_guardrail_block
from app.observability.setup import _configured


def test_setup_disabled_is_noop(monkeypatch):
    monkeypatch.setattr("app.observability.setup._configured", False)
    settings = Settings(
        otel_enabled=False,
        otel_exporter="otlp",
    )
    setup_observability(settings, app=None)
    tracer = get_tracer()
    with tracer.start_as_current_span("test.noop") as span:
        assert span is not None
    shutdown_observability()


def test_setup_console_exporter(monkeypatch):
    monkeypatch.setattr("app.observability.setup._configured", False)
    settings = Settings(
        otel_enabled=True,
        otel_exporter="console",
        otel_service_name="test-rag",
        otel_metrics_export_interval_ms=60_000,
    )
    setup_observability(settings, app=None)
    tracer = get_tracer()
    with tracer.start_as_current_span("test.console") as span:
        span.set_attribute("test", True)
    record_chat(intent="rag", agent="rag", generated=True)
    record_guardrail_block(code="injection")
    shutdown_observability()
    assert _configured is False
