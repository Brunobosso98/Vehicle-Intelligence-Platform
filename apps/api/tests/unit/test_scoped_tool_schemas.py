from copy import deepcopy
from uuid import uuid4

import pytest
from jsonschema import Draft202012Validator
from test_agents import fixture as fixture
from test_agents import registry
from test_supervisor_contracts import request_for

from vehicle_platform.agents.schemas import Specialist
from vehicle_platform.agents.specialists.tool_scope import scoped_tool_definitions


def tool(name, properties, required):
    return {
        "name": name,
        "description": "Read-only canonical data",
        "parameters": {"type": "object", "properties": properties, "required": required},
    }


def scope(fixture):
    records = registry(fixture)
    request = request_for(fixture, records, Specialist.PERFORMANCE)
    source = next(iter(records.items.values()))
    evidence = [
        source.model_copy(
            update={"session_id": request.session_ids[0], "pull_id": uuid4(), "event_id": uuid4()}
        )
        for _ in range(2)
    ]
    return request, evidence


@pytest.mark.parametrize("field", ["vehicle_id", "session_id", "pull_id", "event_id"])
def test_tool_ids_accept_registered_scope_and_reject_guessed_ids(fixture, field):
    request, evidence = scope(fixture)
    definition = tool("get_pull", {field: {"type": "string"}}, [field])
    original = deepcopy(definition)
    narrowed = scoped_tool_definitions(request, [definition], evidence)[0]
    schema = narrowed["parameters"]
    registered = schema["properties"][field]["enum"][0]
    assert Draft202012Validator(schema).is_valid({field: registered})
    assert not Draft202012Validator(schema).is_valid({field: str(uuid4())})
    assert definition == original


def test_comparison_arrays_preserve_cardinality_and_unique_registered_ids(fixture):
    request, evidence = scope(fixture)
    definition = tool(
        "compare_pulls",
        {"pull_ids": {"type": "array", "minItems": 2, "maxItems": 20, "items": {"type": "string"}}},
        ["pull_ids"],
    )
    narrowed = scoped_tool_definitions(request, [definition], evidence)[0]["parameters"]
    validate = Draft202012Validator(narrowed).is_valid
    ids = [str(e.pull_id) for e in evidence]
    assert validate({"pull_ids": ids})
    assert not validate({"pull_ids": ids[:1]})
    assert not validate({"pull_ids": [ids[0], ids[0]]})
    assert not validate({"pull_ids": [ids[0], str(uuid4())]})
    assert not scoped_tool_definitions(request, [definition], evidence[:1])


@pytest.mark.parametrize("foreign", ["vehicle_id", "run_id", "session_id"])
def test_foreign_or_out_of_scope_evidence_cannot_supply_tool_ids(fixture, foreign):
    request, evidence = scope(fixture)
    definition = tool("get_pull_summary", {"pull_id": {"type": "string"}}, ["pull_id"])
    evidence = [e.model_copy(update={foreign: uuid4()}) for e in evidence]
    assert scoped_tool_definitions(request, [definition], evidence) == []


def test_nullable_configuration_filter_keeps_null_and_owned_configuration(fixture):
    request, evidence = scope(fixture)
    definition = tool(
        "list_sessions",
        {"configuration_id": {"anyOf": [{"type": "string"}, {"type": "null"}]}},
        [],
    )
    narrowed = scoped_tool_definitions(request, [definition], evidence)[0]["parameters"]
    validate = Draft202012Validator(narrowed).is_valid
    assert validate({"configuration_id": None})
    assert validate({"configuration_id": str(request.context.configurations[0]["id"])})
    assert not validate({"configuration_id": str(uuid4())})
