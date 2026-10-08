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
from vehicle_platform.observability.exporter import SanitizingExporter


class JSONFormatter(logging.Formatter):
    def __init__(self, environment: str, service_name: str = "vehicle-platform-api") -> None:
        super().__init__()
        self.environment = environment
        self.service_name = service_name

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "service": self.service_name,
            "environment": self.environment,
            "event": record.getMessage(),
            "request_id": getattr(record, "request_id", None),
            "trace_id": getattr(record, "trace_id", None),
        }
        for key in (
            "tool_name",
            "transport",
            "status",
            "duration_seconds",
            "result_count",
            "truncated",
            "error_code",
            "agent_run_id",
            "provider",
            "model",
            "input_tokens",
            "output_tokens",
        ):
            value = getattr(record, key, None)
            if value is not None:
                payload[key] = value
        # Never render exception strings: drivers may embed credentials or SQL inputs.
        if record.exc_info and record.exc_info[0]:
            payload["exception_type"] = record.exc_info[0].__name__
        return json.dumps(payload)


class Telemetry:
    def __init__(
        self,
        settings: Settings,
        database: Database | None = None,
        service_name: str = "vehicle-platform-api",
    ) -> None:
        resource = Resource.create(
            {
                "service.name": service_name,
                "service.version": settings.app_version,
                "deployment.environment.name": settings.environment,
            }
        )
        self.traces = TracerProvider(resource=resource)
        if settings.otel_exporter_otlp_endpoint:
            self.traces.add_span_processor(
                BatchSpanProcessor(
                    SanitizingExporter(
                        OTLPSpanExporter(
                            endpoint=settings.otel_exporter_otlp_endpoint.rstrip("/")
                            + "/v1/traces",
                            timeout=2,
                        )
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
        # Labels are deliberately source/outcome only; never vehicle, VIN, session or sample IDs.
        self.imports = meter.create_counter("telemetry.imports", unit="{import}")
        self.import_rows = meter.create_counter("telemetry.import.rows", unit="{sample}")
        self.import_duration = meter.create_histogram("telemetry.import.duration", unit="s")
        self.db_batch_duration = meter.create_histogram("telemetry.db.batch.duration", unit="s")
        self.query_duration = meter.create_histogram("telemetry.query.duration", unit="s")
        self.query_points = meter.create_counter("telemetry.query.points", unit="{sample}")
        # Detector labels are bounded profile/version/outcome values; entity IDs are prohibited.
        self.detection_runs = meter.create_counter("analysis.detection.runs", unit="{run}")
        self.detection_duration = meter.create_histogram("analysis.detection.duration", unit="s")
        self.segments_produced = meter.create_counter(
            "analysis.segments.produced", unit="{segment}"
        )
        self.pulls_detected = meter.create_counter("analysis.pulls.detected", unit="{pull}")
        self.low_confidence_pulls = meter.create_counter(
            "analysis.pulls.low_confidence", unit="{pull}"
        )
        self.detector_failures = meter.create_counter(
            "analysis.detector.failures", unit="{failure}"
        )
        self.telemetry_windows_analyzed = meter.create_counter(
            "analysis.telemetry.windows", unit="{window}"
        )
        # Phase 3 labels are bounded detector/category/outcome vocabularies only.
        self.event_analysis_runs = meter.create_counter("events.analysis.runs", unit="{run}")
        self.event_detector_duration = meter.create_histogram("events.detector.duration", unit="s")
        self.events_produced = meter.create_counter("events.produced", unit="{event}")
        self.event_detector_unavailable = meter.create_counter(
            "events.detector.unavailable", unit="{detector}"
        )
        self.event_insufficient_data = meter.create_counter(
            "events.detector.insufficient_data", unit="{detector}"
        )
        self.events_consolidated = meter.create_counter("events.consolidated", unit="{event}")
        self.event_analysis_failures = meter.create_counter(
            "events.analysis.failures", unit="{failure}"
        )
        # Phase 4 attributes use bounded state/category vocabularies only.
        self.acquisition_active = meter.create_up_down_counter("acquisition.sessions.active")
        self.acquisition_observations = meter.create_counter("acquisition.observations.received")
        self.acquisition_persisted = meter.create_counter("acquisition.observations.persisted")
        self.collector_heartbeats = meter.create_counter("acquisition.collector.heartbeats")
        self.broker_publish_duration = meter.create_histogram(
            "acquisition.broker.publish.duration", unit="s"
        )
        self.stream_publish_failures = meter.create_counter("acquisition.stream.publish_failures")
        self.consumer_lag = meter.create_histogram("acquisition.consumer.lag", unit="{message}")
        self.acquisition_dropped = meter.create_counter("acquisition.observations.dropped")
        self.acquisition_duplicates = meter.create_counter("acquisition.observations.duplicate")
        self.acquisition_reconnects = meter.create_counter("acquisition.reconnects")
        self.spool_occupancy = meter.create_histogram("acquisition.spool.occupancy", unit="By")
        self.live_analysis_latency = meter.create_histogram(
            "acquisition.live_analysis.duration", unit="s"
        )
        self.finalization_duration = meter.create_histogram(
            "acquisition.finalization.duration", unit="s"
        )
        self.provisional_events = meter.create_counter("acquisition.provisional.events")
        # Phase 5 labels are bounded analytics type/status/rejection vocabularies only.
        self.analytics_runs = meter.create_counter("analytics.runs", unit="{run}")
        self.analytics_duration = meter.create_histogram("analytics.duration", unit="s")
        self.analytics_pull_comparisons = meter.create_counter("analytics.pull.comparisons")
        self.analytics_rejected_comparisons = meter.create_counter("analytics.comparisons.rejected")
        self.analytics_insufficient = meter.create_counter("analytics.insufficient_data")
        self.analytics_baseline_builds = meter.create_counter("analytics.baseline.builds")
        self.analytics_baseline_contributors = meter.create_histogram(
            "analytics.baseline.contributors", unit="{pull}"
        )
        self.analytics_trend_builds = meter.create_counter("analytics.trend.builds")
        self.analytics_failures = meter.create_counter("analytics.failures")
        self.sql_instrumentor: SQLAlchemyInstrumentor | None = None
        if database is not None:
            self.sql_instrumentor = SQLAlchemyInstrumentor()
            self.sql_instrumentor.instrument(
                engine=database.engine.sync_engine, tracer_provider=self.traces
            )
        self.logger = logging.getLogger(f"vehicle_platform.{id(self)}")
        self.logger.propagate = False
        handler = logging.StreamHandler()
        handler.setFormatter(JSONFormatter(settings.environment, service_name))
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
