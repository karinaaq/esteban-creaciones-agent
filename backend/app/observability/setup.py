from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from opentelemetry import metrics, trace
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import (
    ConsoleMetricExporter,
    PeriodicExportingMetricReader,
)
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.semconv.resource import ResourceAttributes

if TYPE_CHECKING:
    from fastapi import FastAPI

    from app.config import Settings

logger = logging.getLogger(__name__)

_configured = False


def setup_observability(settings: Settings, app: FastAPI | None = None) -> None:
    """
    Inicializa traces + metrics con exporters gratis:
    - console → stdout (dev)
    - otlp → Jaeger/collector local (OTLP gRPC, sin costo de SaaS)
    - none / OTEL_ENABLED=false → no-op
    """
    global _configured
    if _configured:
        return
    from app.observability.payloads import configure_payloads

    configure_payloads(
        enabled=settings.otel_capture_payloads,
        max_chars=settings.otel_payload_max_chars,
    )

    if not settings.otel_enabled or settings.otel_exporter == "none":
        logger.info("OpenTelemetry disabled (otel_enabled=%s exporter=%s)",
                    settings.otel_enabled, settings.otel_exporter)
        _configured = True
        return

    resource = Resource.create(
        {
            ResourceAttributes.SERVICE_NAME: settings.otel_service_name,
            ResourceAttributes.SERVICE_VERSION: "0.1.0",
            "deployment.environment": settings.otel_environment,
        }
    )

    tracer_provider = TracerProvider(resource=resource)
    meter_readers: list = []

    if settings.otel_exporter == "console":
        tracer_provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))
        meter_readers.append(
            PeriodicExportingMetricReader(
                ConsoleMetricExporter(),
                export_interval_millis=settings.otel_metrics_export_interval_ms,
            )
        )
    elif settings.otel_exporter == "otlp":
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
            OTLPSpanExporter,
        )

        endpoint = settings.otel_exporter_otlp_endpoint
        insecure = settings.otel_exporter_otlp_insecure
        span_exporter = OTLPSpanExporter(endpoint=endpoint, insecure=insecure)
        tracer_provider.add_span_processor(BatchSpanProcessor(span_exporter))
        # Jaeger all-in-one NO implementa OTLP MetricsService → no exportar
        # métricas por OTLP (evita StatusCode.UNIMPLEMENTED spam).
        # Los counters quedan in-process vía MeterProvider sin reader.
        logger.info(
            "OTLP metrics export disabled (Jaeger traces-only). "
            "Use OTEL_EXPORTER=console if you want metric stdout dumps."
        )
    else:
        raise ValueError(
            f"otel_exporter inválido: {settings.otel_exporter!r} "
            "(usar: none | console | otlp)"
        )

    trace.set_tracer_provider(tracer_provider)
    metrics.set_meter_provider(MeterProvider(resource=resource, metric_readers=meter_readers))

    if app is not None:
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

        FastAPIInstrumentor.instrument_app(
            app,
            excluded_urls="health",
        )

    _configured = True
    logger.info(
        "OpenTelemetry ready: exporter=%s service=%s endpoint=%s",
        settings.otel_exporter,
        settings.otel_service_name,
        settings.otel_exporter_otlp_endpoint if settings.otel_exporter == "otlp" else "-",
    )


def shutdown_observability() -> None:
    """Flush + shutdown providers (llamar al apagar la app)."""
    global _configured
    from app.observability.metrics import _instruments

    _instruments.cache_clear()
    tp = trace.get_tracer_provider()
    mp = metrics.get_meter_provider()
    for provider in (tp, mp):
        shutdown = getattr(provider, "shutdown", None)
        if callable(shutdown):
            try:
                shutdown()
            except Exception:  # noqa: BLE001
                logger.exception("Error shutting down OpenTelemetry provider")
    _configured = False
