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
            "investigation_id",
            "transition",
            "hypothesis_count",
            "gap_count",
            "signal_need_count",
            "recipe_version",
            "recipe_hash",
            "feasibility",
            "approval_state",
            "linked_session_count",
            "planning_seconds",
            "recipe_generation_seconds",
            "mcp_calls",
            "supervisor_state",
            "specialist",
            "selected",
            "skipped",
            "tool_call_count",
            "conflict_count",
            "sufficiency",
            "phase7b_proposed",
            "index_version",
            "candidates",
            "knowledge_gap",
            "prediction_endpoint",
            "prediction_status",
            "prediction_reason",
            "prediction_kind",
            "prediction_event",
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
        # Knowledge metrics count completed operations, including idempotent replays.
        # Never label them with document text, URLs, credentials or entity identities.
        self.knowledge_ingestions = meter.create_counter("knowledge_ingestion_total")
        self.knowledge_ingestion_failures = meter.create_counter(
            "knowledge_ingestion_failures_total"
        )
        self.knowledge_chunks = meter.create_counter("knowledge_chunks_total")
        self.embedding_requests = meter.create_counter("embedding_requests_total")
        self.embedding_tokens = meter.create_counter("embedding_tokens_total")
        self.embedding_cost = meter.create_counter("embedding_estimated_cost_usd")
        self.embedding_cache_hits = meter.create_counter("embedding_cache_hits_total")
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
        # Phase 9D labels are bounded result and status vocabularies only.
        self.prediction_requests = meter.create_counter("prediction_service.requests")
        self.prediction_receipts = meter.create_counter("prediction_service.receipts")
        self.prediction_failures = meter.create_counter("prediction_service.failures")
        self.prediction_budget_denials = meter.create_counter("prediction_service.budget_denials")
        self.prediction_approval_changes = meter.create_counter(
            "prediction_service.approval_changes"
        )
        self.prediction_duration = meter.create_histogram("prediction_service.duration", unit="s")
        self.prediction_artifact_load_duration = meter.create_histogram(
            "prediction_service.artifact_load.duration", unit="s"
        )
        self.prediction_in_flight = meter.create_up_down_counter(
            "prediction_service.requests.in_flight"
        )
        self.prediction_evidence_operations = meter.create_counter("prediction_evidence.operations")
        self.prediction_evidence_replays = meter.create_counter("prediction_evidence.replays")
        self.prediction_evidence_gaps = meter.create_counter("prediction_evidence.gaps")
        self.prediction_evidence_duration = meter.create_histogram(
            "prediction_evidence.duration", unit="s"
        )
        self.prediction_evidence_graph_size = meter.create_histogram(
            "prediction_evidence.graph_size", unit="{item}"
        )
        # Phase 9F metrics use only a bounded outcome label. Source, vehicle, session,
        # pull, receipt and evidence identifiers must never be metric attributes.
        self.agent_prediction_evidence_operations = meter.create_counter(
            "agent.prediction_evidence.operations", unit="{operation}"
        )
        self.agent_prediction_evidence_duration = meter.create_histogram(
            "agent.prediction_evidence.duration", unit="s"
        )
        self.agent_prediction_evidence_authorizations = meter.create_counter(
            "agent.prediction_evidence.authorizations", unit="{attempt}"
        )
        self.agent_prediction_evidence_grounding = meter.create_counter(
            "agent.prediction_evidence.grounding", unit="{claim}"
        )
        # Phase 9G labels are closed protocol, source-role, status and reason values only.
        # Never add vehicle, configuration, session, feature value, path or checksum labels.
        self.evaluation_runs = meter.create_counter("evaluation.runs", unit="{run}")
        self.evaluation_failures = meter.create_counter("evaluation.failures", unit="{failure}")
        self.evaluation_duration = meter.create_histogram("evaluation.duration", unit="s")
        self.evaluation_rows = meter.create_histogram("evaluation.dataset.rows", unit="{row}")
        self.evaluation_sessions = meter.create_histogram(
            "evaluation.dataset.sessions", unit="{session}"
        )
        self.evaluation_calibration_candidates = meter.create_counter(
            "evaluation.calibration.candidates", unit="{candidate}"
        )
        self.evaluation_abstentions = meter.create_counter("evaluation.abstentions", unit="{row}")
        self.evaluation_abstention_reasons = meter.create_counter(
            "evaluation.abstention.reasons", unit="{row}"
        )
        self.evaluation_integrity_violations = meter.create_counter(
            "evaluation.integrity.violations", unit="{violation}"
        )
        self.evaluation_artifact_bytes = meter.create_histogram(
            "evaluation.research_artifact.bytes", unit="By"
        )
        self.evaluation_drift_features = meter.create_counter(
            "evaluation.drift.features", unit="{feature}"
        )
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
        # Phase 9A labels are bounded vocabularies; entity IDs are excluded.
        self.feature_generation_runs = meter.create_counter(
            "features.generation.runs", unit="{run}"
        )
        self.feature_sets_generated = meter.create_counter("features.sets", unit="{set}")
        self.feature_generation_failures = meter.create_counter("features.generation.failures")
        self.feature_generation_duration = meter.create_histogram(
            "features.generation.duration", unit="s"
        )
        self.feature_null_values = meter.create_counter("features.values.null")
        self.leakage_rejections = meter.create_counter("features.leakage.rejections")
        self.dataset_builds = meter.create_counter("features.dataset.builds", unit="{build}")
        self.dataset_rows = meter.create_counter("features.dataset.rows", unit="{row}")
        self.dataset_exclusions = meter.create_counter("features.dataset.exclusions", unit="{row}")
        self.dataset_build_duration = meter.create_histogram(
            "features.dataset.build.duration", unit="s"
        )
        # Phase 9B labels are bounded task, candidate family, and outcome vocabularies.
        # Dataset/model IDs, VINs, pull IDs, and checksums must never be metric attributes.
        self.training_runs = meter.create_counter("ml.training.runs", unit="{run}")
        self.training_failures = meter.create_counter("ml.training.failures", unit="{failure}")
        self.label_exclusions = meter.create_counter("ml.labels.exclusions", unit="{row}")
        self.candidate_models = meter.create_counter("ml.candidate.models", unit="{model}")
        self.model_evaluations = meter.create_counter("ml.model.evaluations", unit="{evaluation}")
        self.dataset_rows_training = meter.create_histogram("ml.dataset.rows", unit="{row}")
        self.candidate_training_duration = meter.create_histogram(
            "ml.candidate.training.duration", unit="s"
        )
        self.model_artifact_size = meter.create_histogram("ml.artifact.size", unit="By")
        # Phase 9C labels are closed detector-family, method, lifecycle and status vocabularies.
        # Never add vehicle, configuration, session, pull, reference or artifact IDs here.
        self.anomaly_fit_runs = meter.create_counter("anomaly.detector.fits", unit="{fit}")
        self.anomaly_detection_runs = meter.create_counter("anomaly.detection.runs", unit="{run}")
        self.anomaly_findings = meter.create_counter("anomaly.findings", unit="{finding}")
        self.anomaly_fit_duration = meter.create_histogram(
            "anomaly.detector.fit.duration", unit="s"
        )
        self.anomaly_detection_duration = meter.create_histogram(
            "anomaly.detection.duration", unit="s"
        )
        self.anomaly_artifact_size = meter.create_histogram("anomaly.artifact.size", unit="By")
        self.anomaly_reference_rows = meter.create_histogram("anomaly.reference.rows", unit="{row}")
        self.anomaly_reference_exclusions = meter.create_counter(
            "anomaly.reference.exclusions", unit="{row}"
        )
        self.anomaly_score = meter.create_histogram("anomaly.score")
        self.anomaly_threshold = meter.create_histogram("anomaly.threshold")
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
