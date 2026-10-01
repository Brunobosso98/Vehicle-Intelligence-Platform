import json
import logging
from datetime import UTC, datetime
from typing import Any

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.exporter.prometheus import PrometheusMetricReader
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from prometheus_client import CollectorRegistry, generate_latest

from vehicle_platform.core.config import Settings
from vehicle_platform.infrastructure.database import Database


class JSONFormatter(logging.Formatter):
    def __init__(self, environment: str) -> None:
        super().__init__()
        self.environment = environment

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "service": "vehicle-platform-api",
            "environment": self.environment,
            "event": record.getMessage(),
            "request_id": getattr(record, "request_id", None),
            "trace_id": getattr(record, "trace_id", None),
        }
        # Never render exception strings: drivers may embed credentials or SQL inputs.
        if record.exc_info and record.exc_info[0]:
            payload["exception_type"] = record.exc_info[0].__name__
        return json.dumps(payload)


class Telemetry:
    def __init__(self, settings: Settings, database: Database | None = None) -> None:
        resource = Resource.create(
            {
                "service.name": "vehicle-platform-api",
                "service.version": settings.app_version,
                "deployment.environment.name": settings.environment,
            }
        )
        self.traces = TracerProvider(resource=resource)
        if settings.otel_exporter_otlp_endpoint:
            self.traces.add_span_processor(
                BatchSpanProcessor(
                    OTLPSpanExporter(
                        endpoint=settings.otel_exporter_otlp_endpoint.rstrip("/") + "/v1/traces",
                        timeout=2,
                    )
                )
            )
        self.tracer = self.traces.get_tracer("vehicle_platform")
        self.registry = CollectorRegistry()
        reader = PrometheusMetricReader(registry=self.registry)
        self.metrics = MeterProvider(resource=resource, metric_readers=[reader])
        meter = self.metrics.get_meter("vehicle_platform")
        self.requests = meter.create_counter("http.server.requests", unit="{request}")
        self.latency = meter.create_histogram(
            "http.server.duration",
            unit="s",
            explicit_bucket_boundaries_advisory=(
                0.005,
                0.01,
                0.025,
                0.05,
                0.1,
                0.25,
                0.5,
                1,
                2.5,
                5,
                10,
            ),
        )
        self.readiness_failures = meter.create_counter("service.readiness.failures")
        self.sql_instrumentor: SQLAlchemyInstrumentor | None = None
        if database is not None:
            self.sql_instrumentor = SQLAlchemyInstrumentor()
            self.sql_instrumentor.instrument(
                engine=database.engine.sync_engine, tracer_provider=self.traces
            )
        self.logger = logging.getLogger(f"vehicle_platform.{id(self)}")
        self.logger.propagate = False
        handler = logging.StreamHandler()
        handler.setFormatter(JSONFormatter(settings.environment))
        self.logger.handlers = [handler]
        self.logger.setLevel(logging.INFO)

    def render_metrics(self) -> bytes:
        return generate_latest(self.registry)

    def shutdown(self) -> None:
        if self.sql_instrumentor is not None:
            self.sql_instrumentor.uninstrument()
        self.traces.shutdown()
        self.metrics.shutdown()

    def log(self, event: str, request_id: str, **fields: Any) -> None:
        context = trace.get_current_span().get_span_context()
        self.logger.info(
            event,
            extra={
                "request_id": request_id,
                "trace_id": format(context.trace_id, "032x"),
                **fields,
            },
        )
