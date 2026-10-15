from uuid import uuid4

import pytest

from vehicle_platform.agents.evidence import EvidenceRegistry
from vehicle_platform.agents.schemas import Binding, Classification, Finding
from vehicle_platform.agents.specialists.runtime import quality_observation_bindings
from vehicle_platform.mcp.schemas import Envelope


def observation(paths, *, event_type="telemetry_gap", tool="get_event"):
    vehicle = uuid4()
    registry = EvidenceRegistry(uuid4(), vehicle, 10)
    source = registry.add(
        tool,
        uuid4(),
        Envelope(
            data={
                "id": str(uuid4()),
                "event_type": event_type,
                "started_at": "2026-01-01T00:00:00Z",
                "ended_at": "2026-01-01T00:00:02Z",
                "evidence": {
                    "gap_seconds": 2.0,
                    "analysis_confidence_reduced": True,
                    "mechanical_cause": "unsupported diagnosis",
                },
            },
            context={"vehicle_id": vehicle},
        ),
    )[0]
    facts = {fact.path: fact for fact in source.facts}
    finding = Finding(
        classification=Classification.OBSERVATION,
        template="recorded_fact",
        evidence_ids=[source.id],
        bindings=[
            Binding(
                evidence_id=source.id, path=path, value=facts[path].value, unit=facts[path].unit
            )
            for path in paths
        ],
        statement="validated source observation",
    )
    return registry, finding


def test_quality_gap_details_preserve_event_identity_and_recorded_values():
    paths = [
        "/evidence/gap_seconds",
        "/started_at",
        "/ended_at",
        "/evidence/analysis_confidence_reduced",
    ]
    registry, finding = observation(paths)
    result = quality_observation_bindings(finding, registry)
    assert [binding.path for binding in result] == ["/event_type", *paths]
    assert result[0].value == "telemetry_gap"
    assert result[1].value == 2.0
    assert result[-1].value is True
    assert all(binding.evidence_id in finding.evidence_ids for binding in result)


@pytest.mark.parametrize(
    ("event_type", "tool"),
    [("boost_drop", "get_event"), ("telemetry_gap", "get_vehicle")],
)
def test_quality_synthesis_rejects_mechanical_events_and_unrelated_source_tools(event_type, tool):
    registry, finding = observation(["/evidence/gap_seconds"], event_type=event_type, tool=tool)
    assert quality_observation_bindings(finding, registry) == []


def test_quality_synthesis_excludes_unsupported_mechanical_details():
    registry, finding = observation(["/evidence/mechanical_cause"])
    assert quality_observation_bindings(finding, registry) == []


def test_quality_event_identity_is_not_duplicated():
    registry, finding = observation(["/event_type", "/evidence/gap_seconds"])
    result = quality_observation_bindings(finding, registry)
    assert [binding.path for binding in result] == ["/event_type", "/evidence/gap_seconds"]
