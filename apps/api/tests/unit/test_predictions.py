from __future__ import annotations

import asyncio
import threading
import time
from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import UUID

import httpx
import pytest
from pydantic import SecretStr, ValidationError

from vehicle_platform.anomalies.domain import SourceRole
from vehicle_platform.core.config import Settings
from vehicle_platform.main import create_app
from vehicle_platform.ml.domain import MLTask
from vehicle_platform.predictions import cli as prediction_cli
from vehicle_platform.predictions.budgets import PredictionRequestBudgetMiddleware
from vehicle_platform.predictions.domain import (
    AnomalyRequest,
    NextPullRequest,
    PredictionError,
    PredictionStatus,
    ServingCandidate,
)
from vehicle_platform.predictions.service import BoundedInferenceWorker, PredictionService


def settings(**overrides: object) -> Settings:
    values: dict[str, object] = {
        "database_url": "postgresql+asyncpg://vehicle:secret@localhost:5432/vehicle",
        "environment": "test",
        "prediction_service_enabled": True,
        "prediction_operator_token": SecretStr("a" * 48),
        "prediction_request_timeout_seconds": 0.2,
        "prediction_body_timeout_seconds": 0.05,
        "prediction_max_body_bytes": 512,
        "prediction_max_concurrent_requests": 1,
    }
    values.update(overrides)
    return Settings(**values)


def scope(headers: list[tuple[bytes, bytes]] | None = None) -> dict[str, object]:
    return {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": "POST",
        "scheme": "http",
        "path": "/api/v1/prediction-service/next-pull",
        "raw_path": b"/api/v1/prediction-service/next-pull",
        "query_string": b"",
        "root_path": "",
        "headers": headers or [],
        "server": ("testserver", 80),
        "client": ("127.0.0.1", 1),
    }


def auth_headers(token: str = "a" * 48) -> list[tuple[bytes, bytes]]:
    return [
        (b"authorization", f"Bearer {token}".encode()),
        (b"content-type", b"application/json"),
    ]


def test_prediction_quality_excludes_not_applicable_features_from_coverage() -> None:
    service = object.__new__(PredictionService)
    snapshot = SimpleNamespace(
        values={
            "observed": {"value": 0.5, "missing_reason": None},
            "not-applicable": {"value": None, "missing_reason": "not_applicable"},
            "unavailable": {"value": None, "missing_reason": "unavailable_signal"},
        },
        quality_metadata={},
    )

    quality = service._quality(
        snapshot,
        features={"observed": 0.5, "not-applicable": None, "unavailable": None},
        missing={
            "not-applicable": "not_applicable",
            "unavailable": "unavailable_signal",
        },
    )

    assert quality.expected_feature_count == 2
    assert quality.observed_feature_count == 1
    assert quality.coverage == 0.5
    assert quality.missing_reason_counts == {"not_applicable": 1, "unavailable_signal": 1}


def test_prediction_request_accepts_json_wire_types_and_forbids_extra_fields() -> None:
    body = {
        "pull_id": str(UUID(int=1)),
        "vehicle_id": str(UUID(int=2)),
        "observation_cutoff": datetime.now(UTC).isoformat(),
        "source_role": "synthetic",
        "task": MLTask.THERMAL_DEGRADATION.value,
    }

    request = NextPullRequest.model_validate(body)

    assert request.pull_id == UUID(int=1)
    assert request.vehicle_id == UUID(int=2)
    assert request.source_role is SourceRole.SYNTHETIC
    assert request.task is MLTask.THERMAL_DEGRADATION
    with pytest.raises(ValidationError):
        NextPullRequest.model_validate({**body, "unexpected": "rejected"})


async def collect(
    middleware: PredictionRequestBudgetMiddleware, request_scope: dict[str, object], receive
):
    sent: list[dict[str, object]] = []

    async def send(message: dict[str, object]) -> None:
        sent.append(message)

    await middleware(request_scope, receive, send)
    return sent


@pytest.mark.asyncio
async def test_prediction_service_is_disabled_by_default_and_rejects_production_enablement() -> (
    None
):
    disabled = Settings(
        database_url="postgresql+asyncpg://vehicle:secret@localhost:5432/vehicle",
        environment="test",
    )
    assert not disabled.prediction_service_enabled
    with pytest.raises(ValidationError):
        Settings(
            database_url="postgresql+asyncpg://vehicle:secret@localhost:5432/vehicle",
            environment="production",
            prediction_service_enabled=True,
            prediction_operator_token=SecretStr("a" * 48),
        )


@pytest.mark.asyncio
async def test_prediction_auth_rejects_before_reading_the_body() -> None:
    async def app(scope, receive, send):
        raise AssertionError("unauthorized request reached the application")

    middleware = PredictionRequestBudgetMiddleware(app, settings())
    receive_calls = 0

    async def receive():
        nonlocal receive_calls
        receive_calls += 1
        return {"type": "http.request", "body": b"{}", "more_body": False}

    sent = await collect(middleware, scope(auth_headers("b" * 48)), receive)
    assert sent[0]["status"] == 401
    assert receive_calls == 0


@pytest.mark.asyncio
async def test_forwarded_private_address_cannot_authorize_a_public_peer() -> None:
    async def app(scope, receive, send):
        raise AssertionError("public peer reached the application")

    middleware = PredictionRequestBudgetMiddleware(app, settings())
    request_scope = scope(auth_headers())
    request_scope["client"] = ("8.8.8.8", 80)
    request_scope["headers"].append((b"x-forwarded-for", b"127.0.0.1"))

    async def receive():
        raise AssertionError("public peer body was read")

    sent = await collect(middleware, request_scope, receive)
    assert sent[0]["status"] == 403


@pytest.mark.asyncio
async def test_prediction_disabled_gate_rejects_before_body_or_app_access() -> None:
    disabled = Settings(
        database_url="postgresql+asyncpg://vehicle:secret@localhost:5432/vehicle",
        environment="test",
    )

    async def app(scope, receive, send):
        raise AssertionError("disabled prediction routes reached FastAPI")

    middleware = PredictionRequestBudgetMiddleware(app, disabled)

    async def receive():
        raise AssertionError("disabled request body was read")

    sent = await collect(middleware, scope(auth_headers()), receive)
    assert sent[0]["status"] == 503


@pytest.mark.asyncio
async def test_disabled_prediction_http_routes_are_unavailable_without_database_access() -> None:
    class NoDatabase:
        async def check(self) -> None:
            return None

    app = create_app(
        Settings(
            database_url="postgresql+asyncpg://vehicle:secret@localhost:5432/vehicle",
            environment="test",
        ),
        probe=NoDatabase(),
    )
    async with app.router.lifespan_context(app):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            openapi = await client.get("/openapi.json")
            unavailable = await client.get("/api/v1/prediction-service/versions")

    assert openapi.status_code == 200
    assert unavailable.status_code == 503
    assert unavailable.json()["error"]["code"] == "PREDICTION_SERVICE_DISABLED"


@pytest.mark.asyncio
async def test_prediction_request_body_is_bounded_before_fastapi_parsing() -> None:
    async def app(scope, receive, send):
        raise AssertionError("oversized request reached the application")

    middleware = PredictionRequestBudgetMiddleware(app, settings())
    request_scope = scope(auth_headers())
    request_scope["headers"].append((b"content-length", b"513"))

    async def receive():
        raise AssertionError("body should be rejected using its declared length")

    sent = await collect(middleware, request_scope, receive)
    assert sent[0]["status"] == 413


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("case", "expected_status"),
    [
        ("missing_content_type", 415),
        ("invalid_content_length", 400),
        ("duplicate_content_length", 400),
        ("negative_content_length", 413),
        ("streamed_body_too_large", 413),
        ("get_body_not_allowed", 413),
    ],
)
async def test_prediction_admission_rejects_invalid_body_envelopes(
    case: str, expected_status: int
) -> None:
    async def app(scope, receive, send):
        raise AssertionError("invalid request envelope reached FastAPI")

    middleware = PredictionRequestBudgetMiddleware(app, settings())
    request_scope = scope(auth_headers())
    if case == "missing_content_type":
        request_scope["headers"] = [
            header for header in request_scope["headers"] if header[0] != b"content-type"
        ]
    elif case == "invalid_content_length":
        request_scope["headers"].append((b"content-length", b"invalid"))
    elif case == "duplicate_content_length":
        request_scope["headers"].extend([(b"content-length", b"2"), (b"content-length", b"2")])
    elif case == "negative_content_length":
        request_scope["headers"].append((b"content-length", b"-1"))
    elif case == "get_body_not_allowed":
        request_scope["method"] = "GET"
        request_scope["headers"].append((b"content-length", b"1"))

    async def receive():
        if case == "streamed_body_too_large":
            return {
                "type": "http.request",
                "body": b"x" * 513,
                "more_body": False,
            }
        if case in {
            "missing_content_type",
            "invalid_content_length",
            "duplicate_content_length",
            "negative_content_length",
            "get_body_not_allowed",
        }:
            raise AssertionError("request body was read before envelope validation")
        raise AssertionError("unexpected request body read")

    sent = await collect(middleware, request_scope, receive)
    assert sent[0]["status"] == expected_status


@pytest.mark.asyncio
async def test_prediction_body_disconnect_ends_admission_without_running_fastapi() -> None:
    async def app(scope, receive, send):
        raise AssertionError("disconnected request reached FastAPI")

    middleware = PredictionRequestBudgetMiddleware(app, settings())

    async def receive():
        return {"type": "http.disconnect"}

    sent = await collect(middleware, scope(auth_headers()), receive)
    assert sent == []
    assert middleware.in_flight == 0


@pytest.mark.asyncio
async def test_prediction_get_without_body_reaches_the_read_only_route() -> None:
    async def app(scope, receive, send):
        await send({"type": "http.response.start", "status": 204, "headers": []})
        await send({"type": "http.response.body", "body": b""})

    middleware = PredictionRequestBudgetMiddleware(app, settings())
    request_scope = scope(auth_headers())
    request_scope["method"] = "GET"
    request_scope["path"] = "/api/v1/prediction-service/versions"
    request_scope["raw_path"] = b"/api/v1/prediction-service/versions"

    async def receive():
        return {"type": "http.disconnect"}

    sent = await collect(middleware, request_scope, receive)
    assert sent[0]["status"] == 204
    assert middleware.in_flight == 0


@pytest.mark.asyncio
@pytest.mark.parametrize("invalid_authorization", [b"\xff", b"Bearer " + b"x" * 2050])
async def test_prediction_authorization_rejects_invalid_encoding_and_oversize(
    invalid_authorization: bytes,
) -> None:
    async def app(scope, receive, send):
        raise AssertionError("invalid authorization reached FastAPI")

    middleware = PredictionRequestBudgetMiddleware(app, settings())
    request_scope = scope(auth_headers())
    request_scope["headers"] = [
        (name, value) for name, value in request_scope["headers"] if name != b"authorization"
    ] + [(b"authorization", invalid_authorization)]

    async def receive():
        raise AssertionError("unauthorized request body was read")

    sent = await collect(middleware, request_scope, receive)
    assert sent[0]["status"] == 401


@pytest.mark.asyncio
@pytest.mark.parametrize("peer", [None, ("invalid-address", 80)])
async def test_prediction_network_fence_rejects_missing_or_invalid_peer(peer) -> None:
    async def app(scope, receive, send):
        raise AssertionError("invalid peer reached FastAPI")

    middleware = PredictionRequestBudgetMiddleware(app, settings())
    request_scope = scope(auth_headers())
    request_scope["client"] = peer

    async def receive():
        raise AssertionError("invalid peer body was read")

    sent = await collect(middleware, request_scope, receive)
    assert sent[0]["status"] == 403


@pytest.mark.asyncio
async def test_prediction_body_timeout_is_a_bounded_408() -> None:
    async def app(scope, receive, send):
        raise AssertionError("incomplete body reached the application")

    middleware = PredictionRequestBudgetMiddleware(app, settings())

    async def slow_receive():
        await asyncio.Future()

    sent = await collect(middleware, scope(auth_headers()), slow_receive)
    assert sent[0]["status"] == 408


@pytest.mark.asyncio
async def test_prediction_request_timeout_is_a_bounded_504() -> None:
    async def app(scope, receive, send):
        await receive()
        await asyncio.Future()

    middleware = PredictionRequestBudgetMiddleware(
        app,
        settings(prediction_request_timeout_seconds=0.05),
    )

    async def receive():
        return {"type": "http.request", "body": b"{}", "more_body": False}

    sent = await collect(middleware, scope(auth_headers()), receive)
    assert sent[0]["status"] == 504
    assert middleware.in_flight == 0


@pytest.mark.asyncio
async def test_prediction_timeout_does_not_send_a_second_response_after_headers() -> None:
    async def app(scope, receive, send):
        await send({"type": "http.response.start", "status": 204, "headers": []})
        await asyncio.Future()

    middleware = PredictionRequestBudgetMiddleware(
        app,
        settings(prediction_request_timeout_seconds=0.05),
    )

    async def receive():
        return {"type": "http.request", "body": b"{}", "more_body": False}

    sent = await collect(middleware, scope(auth_headers()), receive)
    assert [
        message.get("status") for message in sent if message["type"] == "http.response.start"
    ] == [204]
    assert middleware.in_flight == 0


@pytest.mark.asyncio
async def test_prediction_concurrency_slot_is_reserved_while_body_is_read() -> None:
    entered = asyncio.Event()
    release = asyncio.Event()

    async def app(scope, receive, send):
        await send({"type": "http.response.start", "status": 204, "headers": []})
        await send({"type": "http.response.body", "body": b""})

    middleware = PredictionRequestBudgetMiddleware(app, settings())

    async def slow_receive():
        entered.set()
        await release.wait()
        return {"type": "http.request", "body": b"{}", "more_body": False}

    first_scope = scope(auth_headers())
    first_scope["headers"].append((b"content-length", b"2"))
    first = asyncio.create_task(collect(middleware, first_scope, slow_receive))
    await entered.wait()

    async def second_receive():
        raise AssertionError("second request should be rejected before body read")

    second_scope = scope(auth_headers())
    second = await collect(middleware, second_scope, second_receive)
    assert second[0]["status"] == 429
    release.set()
    first_result = await first
    assert first_result[0]["status"] == 204
    assert middleware.in_flight == 0


@pytest.mark.asyncio
async def test_prediction_rate_budget_rejects_before_reading_second_body() -> None:
    async def app(scope, receive, send):
        await send({"type": "http.response.start", "status": 204, "headers": []})
        await send({"type": "http.response.body", "body": b""})

    middleware = PredictionRequestBudgetMiddleware(
        app,
        settings(prediction_requests_per_minute=1),
    )

    async def receive():
        return {"type": "http.request", "body": b"{}", "more_body": False}

    first = await collect(middleware, scope(auth_headers()), receive)
    assert first[0]["status"] == 204

    async def forbidden_read():
        raise AssertionError("rate-limited request body was read")

    second = await collect(middleware, scope(auth_headers()), forbidden_read)
    assert second[0]["status"] == 429


@pytest.mark.asyncio
async def test_prediction_disconnect_cancels_downstream_request_and_releases_slot() -> None:
    body_read = asyncio.Event()
    disconnect = asyncio.Event()
    downstream_cancelled = asyncio.Event()

    async def app(scope, receive, send):
        await receive()
        body_read.set()
        try:
            await asyncio.Future()
        except asyncio.CancelledError:
            downstream_cancelled.set()
            raise

    middleware = PredictionRequestBudgetMiddleware(app, settings())

    async def receive():
        if not body_read.is_set():
            return {"type": "http.request", "body": b"{}", "more_body": False}
        await disconnect.wait()
        return {"type": "http.disconnect"}

    request_scope = scope(auth_headers())
    request_scope["headers"].append((b"content-length", b"2"))
    request = asyncio.create_task(collect(middleware, request_scope, receive))
    await body_read.wait()
    disconnect.set()
    await request

    assert downstream_cancelled.is_set()
    assert middleware.in_flight == 0


def test_prediction_request_types_reject_mixed_role_and_naive_cutoff() -> None:
    with pytest.raises(ValidationError):
        NextPullRequest.model_validate(
            {
                "pull_id": "00000000-0000-0000-0000-000000000001",
                "observation_cutoff": "2026-10-20T12:00:00",
                "source_role": "synthetic",
                "task": "NEXT_PULL_THERMAL_DEGRADATION",
            }
        )
    with pytest.raises(ValidationError):
        AnomalyRequest.model_validate(
            {
                "pull_id": "00000000-0000-0000-0000-000000000001",
                "observation_cutoff": "2026-10-20T12:00:00Z",
                "source_role": "mixed",
                "family": "thermal",
            }
        )


def test_prediction_network_setting_rejects_public_ranges() -> None:
    with pytest.raises(ValidationError):
        Settings(
            database_url="postgresql+asyncpg://vehicle:secret@localhost:5432/vehicle",
            prediction_trusted_networks="0.0.0.0/0",
        )


@pytest.mark.asyncio
async def test_prediction_worker_timeout_does_not_leak_a_cpu_permit() -> None:
    worker = BoundedInferenceWorker(concurrency=1, timeout_seconds=0.2)
    finished = threading.Event()

    def slow_value() -> str:
        time.sleep(0.35)
        finished.set()
        return "done"

    with pytest.raises(PredictionError) as raised:
        await worker(slow_value)
    assert raised.value.status_code == 504
    await asyncio.to_thread(finished.wait, 1)
    assert finished.is_set()
    assert await worker(lambda: PredictionStatus.READY_SCORE.value) == "READY_SCORE"
    await worker.shutdown()


@pytest.mark.asyncio
async def test_prediction_worker_cancellation_keeps_cpu_slot_until_work_finishes() -> None:
    worker = BoundedInferenceWorker(concurrency=1, timeout_seconds=1)
    started = threading.Event()
    finished = threading.Event()

    def slow_value() -> str:
        started.set()
        time.sleep(0.08)
        finished.set()
        return "done"

    request = asyncio.create_task(worker(slow_value))
    await asyncio.to_thread(started.wait, 1)
    request.cancel()
    with pytest.raises(asyncio.CancelledError):
        await request
    assert await worker(lambda: "second") == "second"
    assert finished.is_set()
    await worker.shutdown()


@pytest.mark.asyncio
async def test_prediction_worker_runs_off_the_event_loop() -> None:
    worker = BoundedInferenceWorker(concurrency=1, timeout_seconds=1)
    ticks = 0

    async def heartbeat() -> None:
        nonlocal ticks
        for _ in range(5):
            await asyncio.sleep(0.005)
            ticks += 1

    async def exercise() -> None:
        await asyncio.gather(worker(time.sleep, 0.04), heartbeat())

    await exercise()
    await worker.shutdown()
    assert ticks == 5


@pytest.mark.asyncio
async def test_prediction_cli_requires_explicit_yes_and_matching_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeDatabase:
        async def close(self) -> None:
            return None

    class FakeService:
        async def close(self) -> None:
            return None

        async def approve_candidate(self, *args: object, **kwargs: object) -> tuple[UUID, UUID]:
            pytest.fail("approval must not run without explicit confirmation")

    monkeypatch.setattr(prediction_cli, "Settings", lambda: settings())
    monkeypatch.setattr(prediction_cli, "Database", lambda *args, **kwargs: FakeDatabase())
    monkeypatch.setattr(prediction_cli, "PredictionService", lambda *args, **kwargs: FakeService())

    for confirmation, expected_code in (
        ("test", "PREDICTION_EXPLICIT_CONFIRMATION_REQUIRED"),
        ("development", "PREDICTION_ENVIRONMENT_CONFIRMATION_REQUIRED"),
    ):
        args = prediction_cli.build_parser().parse_args(
            [
                "approve",
                "--kind",
                "next_pull",
                "--version-id",
                str(UUID(int=1)),
                "--source-role",
                "synthetic",
                "--reason",
                "A sufficiently detailed controlled test approval reason.",
                "--operator-id",
                "unit-operator",
                "--review-reference",
                "phase9d-unit-review",
                "--confirm-environment",
                confirmation,
            ]
        )
        if confirmation == "test":
            with pytest.raises(SystemExit):
                prediction_cli.build_parser().parse_args(
                    [
                        "approve",
                        "--kind",
                        "next_pull",
                        "--version-id",
                        str(UUID(int=1)),
                        "--source-role",
                        "synthetic",
                        "--reason",
                        "A sufficiently detailed controlled test approval reason.",
                        "--operator-id",
                        "unit-operator",
                        "--review-reference",
                        "phase9d-unit-review",
                    ]
                )
            args.yes = False
        else:
            args.yes = True
        with pytest.raises(PredictionError) as raised:
            await prediction_cli._run(args)
        assert raised.value.code == expected_code


@pytest.mark.asyncio
async def test_prediction_cli_approval_records_operator_evidence(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    binding_id = UUID(int=2)
    event_id = UUID(int=3)
    captured: dict[str, object] = {}

    class FakeDatabase:
        async def close(self) -> None:
            return None

    class FakeService:
        async def close(self) -> None:
            return None

        async def approve_candidate(self, *args: object, **kwargs: object) -> tuple[UUID, UUID]:
            captured["args"] = args
            captured.update(kwargs)
            return binding_id, event_id

    monkeypatch.setattr(prediction_cli, "Settings", lambda: settings())
    monkeypatch.setattr(prediction_cli, "Database", lambda *args, **kwargs: FakeDatabase())
    monkeypatch.setattr(prediction_cli, "PredictionService", lambda *args, **kwargs: FakeService())
    args = prediction_cli.build_parser().parse_args(
        [
            "approve",
            "--kind",
            "next_pull",
            "--version-id",
            str(UUID(int=1)),
            "--source-role",
            "synthetic",
            "--reason",
            "A sufficiently detailed controlled test approval reason.",
            "--operator-id",
            "unit-operator",
            "--review-reference",
            "phase9d-unit-review",
            "--yes",
            "--confirm-environment",
            "test",
        ]
    )

    result = await prediction_cli._run(args)

    assert result == {
        "status": "APPROVED",
        "binding_id": str(binding_id),
        "event_id": str(event_id),
    }
    assert captured["review_reference"] == "phase9d-unit-review"
    assert captured["environment_confirmation"] == "test"


@pytest.mark.asyncio
async def test_prediction_cli_lists_inspects_and_transitions_reviewed_bindings(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    binding_id = UUID(int=4)
    version_id = UUID(int=5)
    candidate = ServingCandidate(
        result_kind="next_pull",
        subject_key="NEXT_PULL_THERMAL_DEGRADATION",
        version_id=version_id,
        source_role=SourceRole.SYNTHETIC,
        lifecycle_state="CANDIDATE",
        artifact_checksum="a" * 64,
        feature_set_version="phase9a-pull-v2",
        feature_set_checksum="b" * 64,
        schema_checksum="c" * 64,
        evaluation_class="accepted",
        validation_status="PASS",
        interpretation="Controlled engineering evaluation only.",
    )
    binding = SimpleNamespace(
        latest_event_type=SimpleNamespace(value="REVOKED"),
        id=binding_id,
        model_version_id=None,
        detector_version_id=version_id,
    )
    captured: dict[str, object] = {}

    class FakeDatabase:
        async def close(self) -> None:
            return None

    class FakeService:
        async def close(self) -> None:
            return None

        async def versions(self, *, limit: int, offset: int = 0) -> list[dict[str, object]]:
            captured["page"] = (limit, offset)
            return [
                {"result_kind": "next_pull", "source_role": SourceRole.SYNTHETIC},
                {"result_kind": "anomaly", "source_role": SourceRole.REAL_VEHICLE},
            ]

        async def inspect_candidate(self, kind: str, selected_version: UUID):
            captured["candidate"] = (kind, selected_version)
            return candidate

        async def transition(self, selected_binding: UUID, action: str, **kwargs: object):
            captured["transition"] = (selected_binding, action, kwargs)
            return binding, UUID(int=6)

    monkeypatch.setattr(prediction_cli, "Settings", lambda: settings())
    monkeypatch.setattr(prediction_cli, "Database", lambda *args, **kwargs: FakeDatabase())
    monkeypatch.setattr(prediction_cli, "PredictionService", lambda *args, **kwargs: FakeService())

    listed = await prediction_cli._run(
        prediction_cli.build_parser().parse_args(
            ["list", "--kind", "next_pull", "--source-role", "synthetic"]
        )
    )
    inspected = await prediction_cli._run(
        prediction_cli.build_parser().parse_args(
            ["inspect", "--kind", "next_pull", "--version-id", str(version_id)]
        )
    )
    revoked = await prediction_cli._run(
        prediction_cli.build_parser().parse_args(
            [
                "revoke",
                "--binding-id",
                str(binding_id),
                "--reason",
                "Revoke the reviewed controlled test binding.",
                "--operator-id",
                "unit-operator",
                "--yes",
                "--confirm-environment",
                "test",
            ]
        )
    )

    assert listed["status"] == "OK" and len(listed["active_bindings"]) == 1
    assert inspected["status"] == "VERIFIED_CANDIDATE"
    assert captured["candidate"] == ("next_pull", version_id)
    assert revoked["status"] == "REVOKED"
    assert revoked["model_version_id"] is None
    assert revoked["detector_version_id"] == str(version_id)
    assert captured["transition"][1] == "revoke"


@pytest.mark.asyncio
async def test_prediction_cli_lists_active_bindings_without_filters(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeDatabase:
        async def close(self) -> None:
            return None

    class FakeService:
        async def close(self) -> None:
            return None

        async def versions(self, *, limit: int, offset: int = 0) -> list[dict[str, object]]:
            return [
                {"result_kind": "next_pull", "source_role": SourceRole.SYNTHETIC},
                {"result_kind": "anomaly", "source_role": SourceRole.REAL_VEHICLE},
            ]

    monkeypatch.setattr(prediction_cli, "Settings", lambda: settings())
    monkeypatch.setattr(prediction_cli, "Database", lambda *args, **kwargs: FakeDatabase())
    monkeypatch.setattr(prediction_cli, "PredictionService", lambda *args, **kwargs: FakeService())

    result = await prediction_cli._run(prediction_cli.build_parser().parse_args(["list"]))

    assert len(result["active_bindings"]) == 2


@pytest.mark.asyncio
async def test_prediction_cli_refuses_production_controls_before_database_access(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        prediction_cli,
        "Settings",
        lambda: Settings(
            database_url=("postgresql+asyncpg://vehicle:secret@localhost:5432/vehicle?ssl=require"),
            environment="production",
        ),
    )
    monkeypatch.setattr(
        prediction_cli,
        "Database",
        lambda *args, **kwargs: pytest.fail("production controls must fail before DB access"),
    )

    with pytest.raises(PredictionError) as raised:
        await prediction_cli._run(SimpleNamespace(command="list"))

    assert raised.value.status_code == 403
    assert raised.value.code == "PREDICTION_PRODUCTION_CONTROL_DISABLED"
