import pytest

from vehicle_platform.agents.prompts import CLAIM_BINDING_POLICY, SYSTEM_POLICY, TOOL_CONTEXT_POLICY
from vehicle_platform.agents.schemas import Specialist
from vehicle_platform.agents.specialists.policy import specialist_policy


@pytest.mark.parametrize("specialist", list(Specialist))
def test_specialists_receive_actual_application_claim_constraints(specialist):
    instructions = specialist_policy(specialist)
    assert CLAIM_BINDING_POLICY in instructions
    assert TOOL_CONTEXT_POLICY in instructions
    assert "same-configuration pulls" in instructions
    assert "compare_configurations" in instructions
    assert "Evidence.id" in instructions
    assert "both applicable configuration snapshots" in instructions


def test_parent_receives_same_constraints_and_collection_completeness_rules():
    assert CLAIM_BINDING_POLICY in SYSTEM_POLICY
    assert TOOL_CONTEXT_POLICY in SYSTEM_POLICY
    assert SYSTEM_POLICY.startswith("grounded-v6:")
    assert "complete is true" in SYSTEM_POLICY
    assert "returned_count only" in SYSTEM_POLICY


def test_capture_refusal_preserves_unresolved_measurement_gaps():
    assert "never treat a refusal to execute capture as resolving those gaps" in SYSTEM_POLICY


def test_shared_tool_prerequisites_preserve_canonical_context_and_cardinality():
    assert "2–10 distinct sessions sharing one configuration" in TOOL_CONTEXT_POLICY
    assert "2–20 distinct pulls sharing one configuration" in TOOL_CONTEXT_POLICY
    assert "at least two pulls per group" in TOOL_CONTEXT_POLICY
    assert "at most 20 pulls total" in TOOL_CONTEXT_POLICY
    assert "never Evidence.id" in TOOL_CONTEXT_POLICY


def test_null_comparisons_and_raw_points_keep_measurement_identity():
    assert "Null comparison metrics are unavailable measurements" in CLAIM_BINDING_POLICY
    assert "signal and observed_at alongside its value" in CLAIM_BINDING_POLICY


def test_performance_objective_prioritizes_outcomes_and_preserves_comparison_gaps():
    policy = specialist_policy(Specialist.PERFORMANCE)
    assert "measured acceleration, comparable RPM-window duration" in policy
    assert "comparison deltas are null" in policy
    assert "without inferring an" in policy
    assert "Performance findings prioritize" not in specialist_policy(Specialist.THERMAL)


def test_binding_priority_keeps_quantity_before_incidental_metadata():
    assert (
        "numerical measurements that answer the question before incidental metadata"
        in CLAIM_BINDING_POLICY
    )
