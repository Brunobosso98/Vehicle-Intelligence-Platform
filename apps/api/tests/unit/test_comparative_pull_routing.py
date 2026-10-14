from datetime import UTC, datetime
from uuid import uuid4

import pytest

from vehicle_platform.agents.provider import AgentError
from vehicle_platform.agents.schemas import Intent, RoutingProposal, Specialist, VehicleContext
from vehicle_platform.agents.specialists.routing import decide, hints_for


@pytest.mark.parametrize(
    "question",
    [
        "The later pull was clearly worse.",
        "Was the opening pull better than the closing pull?",
        "Show the quicker pull.",
        "A puxada foi pior?",
        "A melhor puxada foi a inicial?",
    ],
)
def test_comparative_pull_performance_stays_with_performance(question):
    hints = hints_for(question, [])
    assert hints.intent is Intent.PERFORMANCE
    assert set(hints.candidates) == {Specialist.PERFORMANCE}


@pytest.mark.parametrize(
    ("question", "intent"),
    [
        ("Which pull had worse intake temperatures?", Intent.THERMAL),
        ("Which pull had worse fuel pressure?", Intent.FUEL_AIR_BOOST),
        ("How many pulls were detected?", Intent.FACTUAL),
    ],
)
def test_comparative_word_does_not_change_other_domains_or_metadata(question, intent):
    hints = hints_for(question, [])
    assert hints.intent is intent
    assert Specialist.PERFORMANCE not in hints.candidates


def test_comparing_a_logger_does_not_imply_comparing_pull_performance():
    hints = hints_for("Was the logger better for capturing this pull?", [])
    assert hints.intent is not Intent.PERFORMANCE
    assert Specialist.PERFORMANCE not in hints.required


def test_comparative_pull_keeps_scoped_intent_when_model_proposes_multiple_mechanisms():
    hints = hints_for("The closing pull was worse.", [])
    context = VehicleContext(vehicle_id=uuid4(), as_of=datetime.now(UTC))
    decision = decide(
        hints,
        RoutingProposal(intent=Intent.MULTI_MECHANISM, specialists=[Specialist.PERFORMANCE]),
        context,
    )
    assert decision.intent is Intent.PERFORMANCE
    assert decision.selected == [Specialist.PERFORMANCE]
    assert decision.data_quality_gate


def test_comparative_pull_rejects_model_escalation_to_unrelated_specialists():
    hints = hints_for("The closing pull was worse.", [])
    context = VehicleContext(vehicle_id=uuid4(), as_of=datetime.now(UTC))
    with pytest.raises(AgentError, match="invalid_supervisor_routing"):
        decide(
            hints,
            RoutingProposal(
                intent=Intent.MULTI_MECHANISM,
                specialists=[Specialist.PERFORMANCE, Specialist.THERMAL],
            ),
            context,
        )
