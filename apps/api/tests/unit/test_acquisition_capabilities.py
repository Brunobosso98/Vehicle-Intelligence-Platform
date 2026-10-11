"""Source support comes from a current local collector or operator preflight."""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from vehicle_platform.acquisition.capabilities import AcquisitionCapabilitySource
from vehicle_platform.acquisition.domain import Support
from vehicle_platform.api.domain_contracts import PreflightRequest


@pytest.fixture
def source():
    db = MagicMock()
    db.execute, db.scalar, db.commit = AsyncMock(), AsyncMock(), AsyncMock()
    db.__aenter__ = AsyncMock(return_value=db)
    db.__aexit__ = AsyncMock(return_value=False)
    database = MagicMock()
    database.session.return_value = db
    return AcquisitionCapabilitySource(database), db


def report() -> PreflightRequest:
    return PreflightRequest(
        adapter="elm327-standard-read-only-v1",
        signals={"engine.rpm": "supported", "vehicle.speed": "unsupported"},
        maximum_requests_per_second=12,
    )


def query_row(value):
    result = MagicMock()
    result.mappings.return_value.one_or_none.return_value = value
    return result


async def test_register_requires_active_configuration_and_limits_source(source):
    service, db = source
    vehicle_id, configuration_id = uuid4(), uuid4()
    with pytest.raises(ValueError, match="invalid source"):
        await service.register(vehicle_id, configuration_id, "obd", "", report())
    db.scalar.return_value = None
    with pytest.raises(ValueError, match="active vehicle configuration"):
        await service.register(vehicle_id, configuration_id, "obd", "local", report())
    db.scalar.side_effect = [1, uuid4()]
    snapshot = await service.register(vehicle_id, configuration_id, "obd", "local", report())
    assert snapshot.preflight_id is not None
    assert snapshot.capabilities.signals["engine.rpm"] is Support.SUPPORTED
    assert db.commit.await_count == 1
    assert "ON CONFLICT ON CONSTRAINT" in str(db.scalar.call_args.args[0])


async def test_latest_prefers_newer_registered_report(source):
    service, db = source
    vehicle_id, configuration_id = uuid4(), uuid4()
    observed = datetime.now(UTC)
    identifier = uuid4()
    db.execute.side_effect = [
        query_row({"id": identifier, "observed_at": observed, "report": report().model_dump()}),
        query_row(None),
    ]
    latest = await service.latest(vehicle_id, configuration_id, "obd", "local")
    assert latest is not None and latest.preflight_id == identifier
    assert latest.capabilities.signals["vehicle.speed"] is Support.UNSUPPORTED
    assert await service.latest(vehicle_id, None, "obd", "local") is None
    with pytest.raises(ValueError, match="invalid source"):
        await service.latest(vehicle_id, configuration_id, "obd", "")


async def test_latest_rejects_stale_and_disconnected_reports(source):
    service, db = source
    vehicle_id, configuration_id = uuid4(), uuid4()
    stale = datetime.now(UTC) - timedelta(days=2)
    db.execute.side_effect = [
        query_row({"id": uuid4(), "observed_at": stale, "report": report().model_dump()}),
        query_row(
            {
                "id": uuid4(),
                "report": {
                    "received_at": datetime.now(UTC).isoformat(),
                    "adapter_state": "disconnected",
                    "capability_snapshot": report().model_dump(),
                },
            }
        ),
    ]
    assert await service.latest(vehicle_id, configuration_id, "obd", "local") is None


async def test_latest_uses_connected_collector_snapshot(source):
    service, db = source
    vehicle_id, configuration_id = uuid4(), uuid4()
    acquisition_id = uuid4()
    db.execute.side_effect = [
        query_row(None),
        query_row(
            {
                "id": acquisition_id,
                "report": {
                    "received_at": datetime.now(UTC).isoformat(),
                    "adapter_state": "connected",
                    "capability_snapshot": report().model_dump(),
                },
            }
        ),
    ]
    latest = await service.latest(vehicle_id, configuration_id, "obd", "local")
    assert latest is not None and latest.acquisition_id == acquisition_id
    assert latest.preflight_id is None
