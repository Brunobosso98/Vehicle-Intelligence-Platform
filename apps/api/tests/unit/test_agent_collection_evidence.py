from datetime import UTC, datetime
from uuid import uuid4

import pytest

from vehicle_platform.agents.evidence import EvidenceRegistry
from vehicle_platform.agents.grounding import validate
from vehicle_platform.agents.provider import AgentError
from vehicle_platform.agents.schemas import Binding, Claim, Classification, Draft, VehicleContext
from vehicle_platform.mcp.schemas import Envelope, Warning


@pytest.mark.parametrize("size", [0, 3])
@pytest.mark.parametrize("truncated", [False, True])
def test_collection_preserves_count_completeness_and_rows(size, truncated):
    vehicle, session, call = uuid4(), uuid4(), uuid4()
    registry = EvidenceRegistry(uuid4(), vehicle, 10)
    records = [{"id": str(uuid4()), "vehicle_id": str(vehicle)} for _ in range(size)]
    items = registry.add(
        "list_session_events",
        call,
        Envelope(
            data=records,
            context={"vehicle_id": vehicle, "session_id": session},
            returned=size,
            truncated=truncated,
            warnings=[Warning(code="truncated_result")] if truncated else [],
        ),
    )
    assert len(items) == size + 1
    assert [str(item.entity_id) for item in items[:-1]] == [record["id"] for record in records]
    collection = items[-1]
    projected = {fact.path: fact.value for fact in collection.facts}
    prefix = "/collection/list_session_events/"
    assert projected[prefix + "returned_count"] == size
    assert projected[prefix + "complete"] is not truncated
    assert (prefix + "total_count" in projected) is not truncated
    assert collection.entity_id is None
    assert collection.session_id == session
    assert collection.tool_call_id == call
    assert collection.truncated is truncated
    assert collection.warnings == (["truncated_result"] if truncated else [])


def test_empty_collection_count_can_be_grounded_without_fabricated_event():
    vehicle = uuid4()
    registry = EvidenceRegistry(uuid4(), vehicle, 1)
    collection = registry.add(
        "list_session_events",
        uuid4(),
        Envelope(data=[], context={"vehicle_id": vehicle}, returned=0),
    )[0]
    draft = Draft(
        confidence="high",
        claims=[
            Claim(
                classification=Classification.OBSERVATION,
                template="recorded_fact",
                evidence_ids=[collection.id],
                bindings=[
                    Binding(
                        evidence_id=collection.id,
                        path="/collection/list_session_events/total_count",
                        value=0,
                    )
                ],
            )
        ],
        missing_evidence=[],
    )
    answer = validate(draft, registry, VehicleContext(vehicle_id=vehicle, as_of=datetime.now(UTC)))
    assert answer.findings[0].bindings[0].value == 0
    assert "0" in answer.answer
    assert collection.event_id is None


def test_collection_rejects_foreign_record_before_publishing_any_evidence():
    vehicle = uuid4()
    registry = EvidenceRegistry(uuid4(), vehicle, 10)
    with pytest.raises(AgentError, match="incompatible_context"):
        registry.add(
            "list_sessions",
            uuid4(),
            Envelope(
                context={"vehicle_id": vehicle},
                data=[
                    {"id": str(uuid4()), "vehicle_id": str(vehicle)},
                    {"id": str(uuid4()), "vehicle_id": str(uuid4())},
                ],
            ),
        )
    assert registry.items == {}


def test_collection_metadata_consumes_evidence_budget():
    vehicle = uuid4()
    registry = EvidenceRegistry(uuid4(), vehicle, 1)
    with pytest.raises(AgentError, match="evidence_budget_exhausted"):
        registry.add(
            "list_sessions",
            uuid4(),
            Envelope(data=[{"id": str(uuid4())}], context={"vehicle_id": vehicle}),
        )
    assert registry.items == {}


def test_dictionary_result_does_not_gain_collection_metadata():
    vehicle = uuid4()
    registry = EvidenceRegistry(uuid4(), vehicle, 1)
    item = registry.add(
        "get_vehicle", uuid4(), Envelope(data={"id": str(vehicle)}, context={"vehicle_id": vehicle})
    )[0]
    assert item.evidence_type == "get_vehicle"
    assert [fact.path for fact in item.facts] == ["/id"]
