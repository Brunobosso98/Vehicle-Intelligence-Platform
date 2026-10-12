import json
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

import pytest
from pydantic import ValidationError
from test_agent_runtime import ResponseStream, request
from test_agent_runtime import provider as provider
from test_agents import insufficient
from test_supervisor_provider import routing_input

from vehicle_platform.agents.provider import AgentError
from vehicle_platform.agents.schemas import Intent, RoutingProposal
from vehicle_platform.evaluation.phase7d import CRITICAL, Ledger, Rates, Suite, load_suite

SUITE_PATH = Path(__file__).resolve().parents[4] / "evals/phase7d/suite-v1.json"


def ledger(tmp_path, limit="2.00", **kwargs):
    return Ledger(
        tmp_path / "checkpoint.json", {"sha": "controlled-sha"}, Decimal(limit), Rates(), **kwargs
    )


def receipt(**kwargs):
    return (
        dict(
            model="gpt-6-luna",
            service_tier="flex",
            input_tokens=100,
            cached_input_tokens=20,
            output_tokens=50,
            total_tokens=150,
            reasoning_tokens=10,
        )
        | kwargs
    )


def test_exact_versioned_dataset_and_fixed_schedule():
    suite, digest = load_suite(SUITE_PATH)
    schedule = suite.schedule()
    assert len(digest) == 64 and len(suite.cases) == 80 and len(schedule) == 120
    assert {c.case_id for c in suite.cases if c.critical} == CRITICAL
    assert all(
        sum(c.case_id == case.case_id for c, _ in schedule) == (3 if case.critical else 1)
        for case in suite.cases
    )


@pytest.mark.parametrize(
    "mode", ["missing", "duplicate", "question", "category", "critical", "repeat", "role"]
)
def test_dataset_fails_closed_on_malformed_distribution(mode):
    data = json.loads(SUITE_PATH.read_text())
    cases = data["cases"]
    if mode == "missing":
        cases.pop()
    if mode == "duplicate":
        cases[1] = cases[0]
    if mode == "question":
        cases[1]["question"] = cases[0]["question"]
    if mode == "category":
        cases[0]["category"] = "B"
    if mode == "critical":
        cases[0]["critical"] = True
    if mode == "repeat":
        cases[0]["repeat_count"] = 2
    if mode == "role":
        cases[0]["required_specialists"] = ["supervisor"]
    with pytest.raises(ValidationError):
        Suite.model_validate(data)


def test_verified_pricing_distinguishes_cached_input():
    parts = Rates().cost(1000000 // 10, 20000, 50000)
    assert Decimal(parts["input"]) == Decimal("0.004")
    assert Decimal(parts["cached_input"]) == Decimal("0.0001")
    assert Decimal(parts["output"]) == Decimal("0.0125")
    assert Decimal(parts["total"]) == Decimal("0.0166")


@pytest.mark.parametrize("values", [(-1, 0, 0), (1, 2, 0), (1, 0, -1), (272001, 0, 0)])
def test_invalid_usage_and_long_context_are_rejected(values):
    with pytest.raises(AgentError):
        Rates().cost(*values)


@pytest.mark.parametrize("limit", ["0", "-1", "5.01", "NaN", "Infinity"])
def test_hard_five_dollar_ceiling(tmp_path, limit):
    with pytest.raises(AgentError, match="invalid_spend_limit"):
        ledger(tmp_path, limit)


def test_reservations_cutoff_and_reported_usage(tmp_path):
    budget = ledger(tmp_path, "0.001")
    with pytest.raises(AgentError, match="SKIPPED_BUDGET_LIMIT"):
        budget.begin("thermal", 100, 4096)
    assert budget.spend() == 0
    ticket = budget.begin("thermal", 100, 512)
    reserved = budget.spend()
    budget.complete(ticket, receipt())
    assert 0 < budget.spend() < reserved
    call = budget.state["calls"][ticket]
    assert call["usage"]["reasoning_tokens"] == 10
    assert call["role"] == "thermal" and call["duration_seconds"] >= 0
    with pytest.raises(AgentError, match="duplicate_provider_receipt"):
        budget.complete(ticket, receipt())
    budget.failed(ticket)
    assert call["status"] == "completed"


def test_resume_keeps_completed_cases_and_charges_interruption(tmp_path):
    budget = ledger(tmp_path)
    assert budget.start_case("1:A01:0")
    budget.finish_case("1:A01:0", {"status": "PASS"})
    assert budget.start_case("1:A02:0")
    budget.begin("agent", 100, 512)
    spend = budget.spend()
    resumed = ledger(tmp_path)
    assert resumed.spend() == spend
    assert not resumed.start_case("1:A01:0")
    assert not resumed.start_case("1:A02:0")
    assert resumed.state["results"]["1:A02:0"]["status"] == "INTERRUPTED"
    assert resumed.state["active"] is None


def test_resume_rejects_changed_commit_or_prices(tmp_path):
    ledger(tmp_path)
    with pytest.raises(AgentError, match="identity_mismatch"):
        Ledger(tmp_path / "checkpoint.json", {"sha": "different"}, Decimal(2), Rates())
    with pytest.raises(AgentError, match="pricing_mismatch"):
        Ledger(
            tmp_path / "checkpoint.json",
            {"sha": "controlled-sha"},
            Decimal(2),
            Rates(verified_on="2026-10-11"),
        )


def test_maximum_two_suites_preserves_accumulated_spend(tmp_path):
    with pytest.raises(AgentError, match="confirmation_requires"):
        ledger(tmp_path, confirmation=True)
    first = ledger(tmp_path)
    first.begin("agent", 100, 512)
    second = ledger(tmp_path, confirmation=True)
    assert second.state["round"] == 2 and second.spend() == first.spend()
    with pytest.raises(AgentError, match="full_suite_limit"):
        ledger(tmp_path, confirmation=True)


def test_one_infrastructure_retry_and_provider_cap(tmp_path):
    budget = ledger(tmp_path)
    budget.start_case("1:A01:0")
    for _ in range(2):
        budget.failed(budget.begin("agent", 100, 512))
    with pytest.raises(AgentError, match="provider_retry_budget_exhausted"):
        budget.begin("agent", 100, 512)
    budget.start_case("1:A02:0")
    for _ in range(18):
        budget.complete(budget.begin("agent", 100, 512), receipt())
    with pytest.raises(AgentError, match="BUDGET_VIOLATION"):
        budget.begin("agent", 100, 512)


@pytest.mark.parametrize(
    "metadata,category",
    [
        ({"input_tokens": None}, "provider_usage_unavailable"),
        ({"input_tokens": True}, "provider_usage_unavailable"),
        ({"output_tokens": 1000}, "BUDGET_VIOLATION"),
        ({"total_tokens": 99}, "BUDGET_VIOLATION"),
        ({"service_tier": "default"}, "provider_configuration_mismatch"),
        ({"model": "expensive"}, "provider_configuration_mismatch"),
    ],
)
def test_usage_and_configuration_fail_closed(tmp_path, metadata, category):
    budget = ledger(tmp_path)
    ticket = budget.begin("agent", 100, 512)
    with pytest.raises(AgentError, match=category):
        budget.complete(ticket, receipt(**metadata))


@pytest.mark.parametrize(
    "mode", ["route", "turn", "invalid_json", "wire_failure", "stream_failure", "no_effort"]
)
async def test_existing_real_adapter_explicit_config_and_safe_receipts(provider, tmp_path, mode):
    budget = ledger(tmp_path)
    provider.observer = budget
    provider.settings.model = "gpt-6-luna"
    provider.settings.service_tier = "flex"
    provider.settings.reasoning_effort = None if mode == "no_effort" else "low"
    usage = SimpleNamespace(
        input_tokens=100,
        output_tokens=50,
        total_tokens=150,
        input_tokens_details=SimpleNamespace(cached_tokens=20),
        output_tokens_details=SimpleNamespace(reasoning_tokens=10),
    )
    response = SimpleNamespace(
        model="gpt-6-luna",
        service_tier="flex",
        usage=usage,
        output_text=RoutingProposal(intent=Intent.FACTUAL).model_dump_json(),
        output=[],
    )
    if mode in {"turn", "stream_failure", "no_effort"}:
        response.output_text = insufficient().model_dump_json()
        provider.client.responses.create.return_value = ResponseStream(
            [
                SimpleNamespace(type="response.failed")
                if mode == "stream_failure"
                else SimpleNamespace(type="response.completed", response=response)
            ]
        )
        action = provider.turn(request())
    else:
        provider.client.responses.create.return_value = response
        if mode == "invalid_json":
            response.output_text = "{"
        if mode == "wire_failure":
            provider.client.responses.create.side_effect = ValueError("sentinel-private-key")
        action = provider.route(routing_input())
    if mode in {"invalid_json", "wire_failure", "stream_failure"}:
        with pytest.raises(AgentError) as error:
            await action
        assert "sentinel-private-key" not in str(error.value)
    else:
        await action
    args = provider.client.responses.create.call_args.kwargs
    assert args["service_tier"] == "flex" and args["store"] is False
    assert (
        ("reasoning" not in args) if mode == "no_effort" else args["reasoning"] == {"effort": "low"}
    )
    assert "sentinel-private-key" not in (tmp_path / "checkpoint.json").read_text()
    call = next(iter(budget.state["calls"].values()))
    assert call["status"] == (
        "failed" if mode in {"wire_failure", "stream_failure"} else "completed"
    )
    assert call["role"] == (
        "supervisor" if mode in {"route", "invalid_json", "wire_failure"} else "agent"
    )


def test_versioned_questions_match_the_authoritative_specification():
    import re

    suite, _ = load_suite(SUITE_PATH)
    text = (SUITE_PATH.parents[2] / "docs/prompts/phase-7d-real-model-validation.md").read_text()
    expected = {}
    for match in re.finditer(
        r"^## \d+\. ([A-H]\d\d)[^\n]*\n(.*?)(?=^## |^# CATEGORY|\Z)", text, re.M | re.S
    ):
        identifier, body = match.groups()
        expected[identifier] = re.search(r'"([^"\n]+)"', body).group(1)
    assert {case.case_id: case.question for case in suite.cases} == expected
    assert (
        next(case for case in suite.cases if case.case_id == "G06").fixture == "sparse_comparison"
    )
