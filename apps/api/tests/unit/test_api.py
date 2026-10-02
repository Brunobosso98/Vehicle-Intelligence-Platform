import json
import logging
from io import StringIO

import httpx
import pytest
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from vehicle_platform.core.config import Settings
from vehicle_platform.infrastructure.database import DependencyUnavailable
from vehicle_platform.main import create_app
from vehicle_platform.observability.telemetry import JSONFormatter, Telemetry


class Probe:
    def __init__(self, failure: Exception | None = None) -> None:
        self.failure = failure

    async def check(self) -> None:
        if self.failure:
            raise self.failure


@pytest.mark.parametrize("failure,expected", [(None, 200), (DependencyUnavailable("secret"), 503)])
async def test_live_independent_and_ready(
    settings: Settings, failure: Exception | None, expected: int
) -> None:
    app = create_app(settings, Probe(failure))
    async with (
        app.router.lifespan_context(app),
        httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client,
    ):
        assert (await client.get("/health/live")).json() == {"status": "ok"}
        ready = await client.get("/health/ready", headers={"X-Request-ID": "integration-123"})
        assert ready.status_code == expected
        assert ready.headers["x-request-id"] == "integration-123"
        if failure:
            assert ready.json()["error"]["code"] == "DATABASE_UNAVAILABLE"
            assert "secret" not in ready.text
        else:
            assert ready.json()["database"] == "ready"
        version = await client.get("/version")
        assert version.json()["version"] == "0.1.0"
        assert "database_url" not in version.text
        missing = await client.get("/unknown")
        assert missing.status_code == 404
        assert missing.json()["error"]["request_id"] == missing.headers["x-request-id"]


async def test_unexpected_exception_sanitized(settings: Settings) -> None:
    app = create_app(settings, Probe(RuntimeError("password=very-secret")))
    async with (
        app.router.lifespan_context(app),
        httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app, raise_app_exceptions=False),
            base_url="http://test",
        ) as client,
    ):
        response = await client.get("/health/ready", headers={"X-Request-ID": "bad id with spaces"})
        assert response.status_code == 500
        assert response.json()["error"]["code"] == "INTERNAL_ERROR"
        assert "very-secret" not in response.text
        assert response.headers["x-request-id"] != "bad id with spaces"
        assert response.headers["x-content-type-options"] == "nosniff"


async def test_validation_handler(settings: Settings) -> None:
    app = create_app(settings, Probe())

    @app.get("/test/{value}")
    async def typed(value: int) -> dict[str, int]:
        return {"value": value}

    async with (
        app.router.lifespan_context(app),
        httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client,
    ):
        response = await client.get("/test/not-an-int")
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "VALIDATION_ERROR"


async def test_logging_recipe_and_preflight_contracts(settings: Settings) -> None:
    app = create_app(settings, Probe())
    async with (
        app.router.lifespan_context(app),
        httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client,
    ):
        objectives = (await client.get("/api/v1/logging/objectives")).json()
        assert {item["key"] for item in objectives} >= {"performance_pull", "general_health"}
        recipe = (await client.get("/api/v1/logging/recipes/performance-pull")).json()
        assert len(recipe["configuration_hash"]) == 64
        required = {
            item["signal"] for item in recipe["requirements"] if item["importance"] == "required"
        }
        response = await client.post(
            "/api/v1/logging/recipes/performance-pull/preflight",
            json={
                "adapter": "synthetic",
                "signals": {signal: "supported" for signal in required},
                "maximum_requests_per_second": 30,
            },
        )
        assert response.status_code == 200
        assert response.json()["readiness"] == "degraded"


async def test_real_trace_metric_and_log_correlation(settings: Settings) -> None:
    signals = Telemetry(settings)
    exporter = InMemorySpanExporter()
    signals.traces.add_span_processor(SimpleSpanProcessor(exporter))
    stream = StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(JSONFormatter("test"))
    signals.logger.handlers = [handler]
    app = create_app(settings, Probe(), signals)
    async with (
        app.router.lifespan_context(app),
        httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client,
    ):
        trace_id = "12345678901234567890123456789012"
        await client.get(
            "/health/live",
            headers={
                "X-Request-ID": "trace-test",
                "traceparent": f"00-{trace_id}-1234567890123456-01",
            },
        )
        metric = await client.get("/metrics")
        assert "http_server_requests" in metric.text
        assert "http_server_duration" in metric.text
        spans = exporter.get_finished_spans()
        span = next(s for s in spans if s.name == "GET /health/live")
        assert span.context is not None
        assert format(span.context.trace_id, "032x") == trace_id
        assert span.attributes is not None and span.attributes["request.id"] == "trace-test"
        entry = json.loads(stream.getvalue().splitlines()[0])
        assert entry["trace_id"] == trace_id and entry["request_id"] == "trace-test"


async def test_non_http_passthrough(settings: Settings) -> None:
    from starlette.types import Receive, Scope, Send

    from vehicle_platform.api.middleware import CorrelationMiddleware

    called = []

    async def inner(scope: Scope, receive: Receive, send: Send) -> None:
        called.append(scope["type"])

    async def receive():
        return {"type": "lifespan.startup"}

    async def send(message):
        pass

    signals = Telemetry(settings)
    await CorrelationMiddleware(inner, signals)({"type": "lifespan"}, receive, send)
    signals.shutdown()
    assert called == ["lifespan"]


def test_json_logs_do_not_render_exception_secrets() -> None:
    record = logging.LogRecord("test", logging.ERROR, "", 0, "failed", (), None)
    record.exc_info = (RuntimeError, RuntimeError("secret"), None)
    parsed = json.loads(JSONFormatter("test").format(record))
    assert parsed["exception_type"] == "RuntimeError"
    assert "secret" not in json.dumps(parsed)


async def test_otlp_http_delivers_real_request_span(settings: Settings) -> None:
    import asyncio
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
    from threading import Thread

    from opentelemetry.proto.collector.trace.v1.trace_service_pb2 import ExportTraceServiceRequest

    received: list[bytes] = []

    class Receiver(BaseHTTPRequestHandler):
        def do_POST(self) -> None:
            received.append(self.rfile.read(int(self.headers["Content-Length"])))
            self.send_response(200)
            self.end_headers()

        def log_message(self, format: str, *args: object) -> None:
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Receiver)
    worker = Thread(target=server.serve_forever, daemon=True)
    worker.start()
    config = settings.model_copy(
        update={"otel_exporter_otlp_endpoint": f"http://127.0.0.1:{server.server_port}"}
    )
    signals = Telemetry(config)
    app = create_app(config, Probe(), signals)
    try:
        async with (
            app.router.lifespan_context(app),
            httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app), base_url="http://test"
            ) as client,
        ):
            await client.get("/health/live", headers={"X-Request-ID": "otlp-request"})
            assert await asyncio.to_thread(signals.traces.force_flush, 3000)
            envelope = ExportTraceServiceRequest()
            envelope.ParseFromString(received[0])
            span = envelope.resource_spans[0].scope_spans[0].spans[0]
            assert span.name == "GET /health/live"
            assert any(
                a.key == "request.id" and a.value.string_value == "otlp-request"
                for a in span.attributes
            )
    finally:
        await asyncio.to_thread(server.shutdown)
        server.server_close()
        worker.join(timeout=2)


async def test_unknown_methods_do_not_expand_metric_cardinality(settings: Settings) -> None:
    app = create_app(settings, Probe())
    async with (
        app.router.lifespan_context(app),
        httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client,
    ):
        assert (await client.request("BREW", "/health/live")).status_code == 405
        metric = (await client.get("/metrics")).text
        assert (
            'http_request_method="_OTHER"' in metric and 'http_request_method="BREW"' not in metric
        )


async def test_non_ascii_correlation_header_is_regenerated(settings: Settings) -> None:
    app = create_app(settings, Probe())
    async with (
        app.router.lifespan_context(app),
        httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client,
    ):
        response = await client.get("/health/live", headers=[(b"x-request-id", b"\xff")])
        assert response.status_code == 200
        assert len(response.headers["x-request-id"]) == 36


def test_phase3_metrics_use_only_bounded_labels(settings: Settings) -> None:
    signals = Telemetry(settings)
    signals.event_analysis_runs.add(1, {"outcome": "completed"})
    signals.event_detector_duration.record(
        0.01, {"detector": "pull-behavior-detector", "outcome": "event_detected"}
    )
    signals.events_produced.add(1, {"category": "performance"})
    signals.event_detector_unavailable.add(
        1, {"detector": "pull-behavior-detector", "outcome": "detector_not_applicable"}
    )
    signals.event_insufficient_data.add(
        1, {"detector": "pull-behavior-detector", "outcome": "insufficient_data"}
    )
    signals.events_consolidated.add(1, {"event_type": "boost_drop"})
    signals.event_analysis_failures.add(1, {"classification": "bounded_limit"})
    metrics = signals.render_metrics().decode()
    assert "events_analysis_runs_total" in metrics
    assert "events_detector_duration_seconds" in metrics
    assert 'category="performance"' in metrics
    assert "session_id" not in metrics and "vehicle_id" not in metrics and "vin" not in metrics
    signals.shutdown()


def test_phase4_metrics_use_only_bounded_labels(settings: Settings) -> None:
    signals = Telemetry(settings)
    signals.acquisition_active.add(1, {"state": "active"})
    signals.acquisition_observations.add(20, {"source": "synthetic"})
    signals.acquisition_persisted.add(19, {"outcome": "accepted"})
    signals.stream_publish_failures.add(1, {"classification": "unavailable"})
    signals.consumer_lag.record(2, {"topic": "telemetry.raw.v1"})
    signals.acquisition_dropped.add(1, {"reason": "spool_full"})
    signals.acquisition_duplicates.add(1, {"source": "consumer"})
    signals.acquisition_reconnects.add(1, {"adapter": "synthetic"})
    signals.spool_occupancy.record(1024, {"level": "normal"})
    signals.live_analysis_latency.record(.01, {"outcome": "provisional"})
    signals.finalization_duration.record(.2, {"outcome": "completed"})
    signals.provisional_events.add(1, {"category": "performance"})
    metrics = signals.render_metrics().decode()
    assert "acquisition_observations_received" in metrics
    assert "acquisition_consumer_lag" in metrics
    assert "session_id" not in metrics and "vehicle_id" not in metrics and "vin" not in metrics
    signals.shutdown()
