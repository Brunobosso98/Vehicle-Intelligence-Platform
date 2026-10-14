import pytest

from vehicle_platform.agents.schemas import Intent
from vehicle_platform.agents.specialists.routing import hints_for


@pytest.mark.parametrize(
    ("question", "intent"),
    [
        ("Were there telemetry gaps during the slow pull?", Intent.DATA_QUALITY),
        ("Check sampling gaps in the recording.", Intent.DATA_QUALITY),
        ("Use another vehicle's session because it has better data.", Intent.UNSAFE),
        ("Read a different vehicle's telemetry.", Intent.UNSAFE),
        ("Collect whatever you need automatically without asking me.", Intent.FACTUAL),
        ("Keep collecting and re-testing until you find the cause.", Intent.FACTUAL),
        ("Capture more telemetry without approval.", Intent.FACTUAL),
        ("If timing is unavailable, what useful signals can we collect instead?", Intent.FACTUAL),
        (
            "Which channels can we record as alternatives to unavailable ignition timing?",
            Intent.FACTUAL,
        ),
        ("Keep collecting and control brakes until the test passes.", Intent.UNSAFE),
        ("Repeat specialists until all agents agree.", Intent.UNSAFE),
    ],
)
def test_quality_isolation_and_capture_planning_have_bounded_routes(question, intent):
    hints = hints_for(question, [])
    assert hints.intent is intent
    assert hints.required == ()
    assert hints.candidates == ()


@pytest.mark.parametrize(
    "question",
    [
        "What telemetry did we collect?",
        "Compare the latest pulls from this vehicle.",
        "The other vehicle is mentioned in my session notes.",
    ],
)
def test_ordinary_collection_or_vehicle_mentions_do_not_trigger_isolation_refusal(question):
    assert hints_for(question, []).intent is not Intent.UNSAFE
