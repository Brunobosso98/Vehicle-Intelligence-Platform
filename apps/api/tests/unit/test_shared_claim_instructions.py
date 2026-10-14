import pytest

from vehicle_platform.agents.prompts import CLAIM_BINDING_POLICY, SYSTEM_POLICY
from vehicle_platform.agents.schemas import Specialist
from vehicle_platform.agents.specialists.policy import specialist_policy


@pytest.mark.parametrize("specialist", list(Specialist))
def test_specialists_receive_actual_application_claim_constraints(specialist):
    instructions = specialist_policy(specialist)
    assert CLAIM_BINDING_POLICY in instructions
    assert "same-configuration pulls" in instructions
    assert "compare_configurations" in instructions
    assert "Evidence.id" in instructions
    assert "both applicable configuration snapshots" in instructions


def test_parent_receives_same_constraints_and_collection_completeness_rules():
    assert CLAIM_BINDING_POLICY in SYSTEM_POLICY
    assert SYSTEM_POLICY.startswith("grounded-v4:")
    assert "complete is true" in SYSTEM_POLICY
    assert "returned_count only" in SYSTEM_POLICY
