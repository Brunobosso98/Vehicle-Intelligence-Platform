import importlib
import json
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from test_agent_runtime import ResponseStream
from test_agent_runtime import provider as provider
from test_agents import insufficient
from test_phase7d_harness import receipt

from vehicle_platform.agents.provider import AgentError
from vehicle_platform.evaluation.phase7d import Ledger, Rates, load_suite


@pytest.fixture
def cli(monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[4] / "scripts"))
    module = importlib.import_module("phase7d_eval")
    return module


@pytest.mark.parametrize(
    "mode,confirm,key,model,tier,effort,category",
    [
        ("eval", False, False, "gpt-6-luna", "flex", "low", "explicit_paid_confirmation_required"),
        ("smoke", True, False, "gpt-6-luna", "flex", "low", "VIP_AGENT_API_KEY_missing"),
        (
            "eval",
            True,
            True,
            "expensive",
            "flex",
            "low",
            "explicit_baseline_configuration_required",
        ),
        (
            "eval",
            True,
            True,
            "gpt-6-luna",
            "default",
            "low",
            "explicit_baseline_configuration_required",
        ),
        (
            "eval",
            True,
            True,
            "gpt-6-luna",
            "flex",
            "high",
            "explicit_baseline_configuration_required",
        ),
    ],
)
def test_paid_entrypoint_fails_before_provider_or_docker(
    cli, monkeypatch, tmp_path, mode, confirm, key, model, tier, effort, category
):
    monkeypatch.setattr(
        "sys.argv",
        ["phase7d_eval.py", mode, "--output", str(tmp_path)]
        + (["--confirm-paid-eval"] if confirm else []),
    )
    monkeypatch.delenv("VIP_AGENT_API_KEY", raising=False)
    if key:
        monkeypatch.setenv("VIP_AGENT_API_KEY", "local-test-secret")
    for name, value in [("MODEL", model), ("SERVICE_TIER", tier), ("REASONING_EFFORT", effort)]:
        monkeypatch.setenv("VIP_AGENT_" + name, value)
    forbidden = AsyncMock(side_effect=AssertionError("Paid provider unexpectedly constructed"))
    monkeypatch.setattr(cli, "OpenAIProvider", forbidden)
    with pytest.raises(AgentError, match=category):
        cli.main()
    forbidden.assert_not_called()
    assert not (tmp_path / "checkpoint.json").exists()


def test_report_without_credentials_is_explicit_not_run(cli, monkeypatch, tmp_path, capsys):
    monkeypatch.setattr("sys.argv", ["phase7d_eval.py", "report", "--output", str(tmp_path)])
    cli.main()
    assert json.loads((tmp_path / "report.json").read_text())["status"] == "NOT RUN"
    assert "NOT RUN" in capsys.readouterr().out


def test_identity_requires_clean_exact_commit(cli, monkeypatch, provider):
    suite, digest = load_suite(cli.ROOT / "evals/phase7d/suite-v1.json")
    replies = iter(["sha\n", " M source.py\n"])
    monkeypatch.setattr(cli.subprocess, "check_output", lambda *args, **kwargs: next(replies))
    with pytest.raises(AgentError, match="clean_commit"):
        cli.identity(provider.settings, digest, suite)
    replies = iter(["sha\n", ""])
    result = cli.identity(provider.settings, digest, suite)
    assert result["repository_sha"] == "sha" and result["sdk_version"]
    assert result["api"] == "Responses"


async def test_exactly_one_smoke_exercises_real_adapter_without_network(
    cli, monkeypatch, provider, tmp_path
):
    budget = Ledger(tmp_path / "checkpoint.json", {"sha": "sha"}, Decimal(2), Rates())
    provider.observer = budget
    provider.settings.model = "gpt-6-luna"
    provider.settings.service_tier = "flex"
    provider.settings.reasoning_effort = "low"
    usage = SimpleNamespace(
        input_tokens=100,
        output_tokens=50,
        total_tokens=150,
        input_tokens_details=SimpleNamespace(cached_tokens=20),
        output_tokens_details=SimpleNamespace(reasoning_tokens=10),
    )
    first = SimpleNamespace(
        model="gpt-6-luna",
        service_tier="flex",
        usage=usage,
        output=[
            SimpleNamespace(
                type="function_call",
                name="get_fixture",
                call_id="controlled-call",
                arguments='{"fixture_id":"controlled-smoke"}',
            )
        ],
    )
    second = SimpleNamespace(
        model="gpt-6-luna",
        service_tier="flex",
        usage=usage,
        output=[],
        output_text=insufficient().model_dump_json(),
    )
    provider.client.responses.create.side_effect = [
        first,
        ResponseStream([SimpleNamespace(type="response.completed", response=second)]),
    ]
    monkeypatch.setattr(cli, "OpenAIProvider", lambda *args: provider)
    await cli.smoke(provider.settings, budget)
    assert budget.state["smoke"]["status"] == "PASS" and len(budget.state["calls"]) == 2
    await cli.smoke(provider.settings, budget)
    assert provider.client.responses.create.await_count == 2
    second_request = provider.client.responses.create.call_args_list[1].kwargs
    assert any(
        item.get("type") == "function_call_output" and item.get("call_id") == "controlled-call"
        for item in second_request["input"]
    )
    assert next(iter(budget.state["calls"].values()))["requested_tools"] == ["get_fixture"]
    provider.client.close.assert_awaited_once()


async def test_interrupted_smoke_is_not_automatically_repeated(cli, tmp_path, provider):
    budget = Ledger(tmp_path / "checkpoint.json", {"sha": "sha"}, Decimal(2), Rates())
    budget.begin("smoke", 100, 512)
    with pytest.raises(AgentError, match="smoke_failed_or_interrupted"):
        await cli.smoke(provider.settings, budget)
    provider.client.responses.create.assert_not_called()
    budget.state["smoke"] = {"status": "FAILED"}
    with pytest.raises(AgentError, match="smoke_failed_or_interrupted"):
        await cli.smoke(provider.settings, budget)


async def test_smoke_failure_is_persisted_and_client_closed(cli, monkeypatch, provider, tmp_path):
    budget = Ledger(tmp_path / "checkpoint.json", {"sha": "sha"}, Decimal(2), Rates())
    provider.observer = budget
    provider._create = AsyncMock(side_effect=AgentError("provider_authentication"))
    monkeypatch.setattr(cli, "OpenAIProvider", lambda *args: provider)
    with pytest.raises(AgentError, match="provider_authentication"):
        await cli.smoke(provider.settings, budget)
    assert budget.state["smoke"]["category"] == "provider_authentication"
    provider.client.close.assert_awaited_once()


def test_receipts_do_not_accept_missing_usage_as_free(tmp_path):
    budget = Ledger(tmp_path / "checkpoint.json", {"sha": "sha"}, Decimal(2), Rates())
    ticket = budget.begin("investigation", 100, 512)
    reserved = budget.spend()
    with pytest.raises(AgentError, match="provider_usage_unavailable"):
        budget.complete(ticket, receipt(cached_input_tokens=None))
    budget.failed(ticket)
    assert budget.spend() == reserved


async def test_first_smoke_request_normalizes_sdk_auth_error_without_key(
    cli, monkeypatch, provider, tmp_path
):
    import httpx
    from openai import AuthenticationError

    budget = Ledger(tmp_path / "checkpoint.json", {"sha": "sha"}, Decimal(2), Rates())
    provider.observer = budget
    wire_request = httpx.Request("POST", "https://example.invalid")
    provider.client.responses.create.side_effect = AuthenticationError(
        "sentinel-private-key", response=httpx.Response(401, request=wire_request), body=None
    )
    monkeypatch.setattr(cli, "OpenAIProvider", lambda *args: provider)
    with pytest.raises(AgentError, match="provider_authentication") as error:
        await cli.smoke(provider.settings, budget)
    assert "sentinel-private-key" not in str(error.value)
    assert "sentinel-private-key" not in (tmp_path / "checkpoint.json").read_text()
    assert budget.state["smoke"]["status"] == "FAILED"


def test_paid_baseline_rejects_mock_or_unverified_endpoint(cli, monkeypatch, tmp_path):
    monkeypatch.setattr(
        "sys.argv", ["phase7d_eval.py", "smoke", "--confirm-paid-eval", "--output", str(tmp_path)]
    )
    for key, value in {
        "VIP_AGENT_API_KEY": "local-test-secret",
        "VIP_AGENT_MODEL": "gpt-6-luna",
        "VIP_AGENT_SERVICE_TIER": "flex",
        "VIP_AGENT_REASONING_EFFORT": "low",
        "OPENAI_BASE_URL": "https://example.invalid",
    }.items():
        monkeypatch.setenv(key, value)
    with pytest.raises(AgentError, match="official_openai_endpoint_required"):
        cli.main()
    assert not (tmp_path / "checkpoint.json").exists()


@pytest.mark.parametrize(
    "errors,expected",
    [
        (["specialist_timeout"], "RUNTIME_FAILURE"),
        (["tool_timeout"], "RUNTIME_FAILURE"),
        (["provider_timeout"], "PROVIDER_FAILURE"),
        (["provider_retry_budget_exhausted"], "RUNTIME_FAILURE"),
        (["provider_configuration_mismatch"], "PROVIDER_FAILURE"),
        (["BUDGET_VIOLATION"], "HARNESS_FAILURE"),
        (["invalid_supervisor_routing"], None),
        (["EXISTING_EVIDENCE_SUFFICIENT"], None),
        (["SKIPPED_BUDGET_LIMIT"], "SKIPPED_BUDGET_LIMIT"),
    ],
)
def test_runtime_failures_are_not_provider_outages(cli, errors, expected):
    assert cli.failure_kind(errors) == expected


def test_individual_bounded_failures_do_not_stop_suite(cli):
    assert not cli.stop_suite({"status": "RUNTIME_FAILURE"}, 0)
    assert not cli.stop_suite(
        {"status": "PROVIDER_FAILURE", "provider_categories": ["provider_timeout"]}, 1
    )
    assert cli.stop_suite(
        {"status": "PROVIDER_FAILURE", "provider_categories": ["provider_timeout"]}, 3
    )
    assert cli.stop_suite(
        {"status": "PROVIDER_FAILURE", "provider_categories": ["provider_authentication"]}, 1
    )
    assert cli.stop_suite({"status": "HARNESS_FAILURE"}, 0)
    assert cli.stop_suite(
        {"status": "PROVIDER_FAILURE", "provider_categories": ["provider_configuration_mismatch"]},
        1,
    )


@pytest.mark.parametrize("failure_count", [0, 1, 2])
async def test_stream_reconnect_is_bounded_read_only_same_run(cli, failure_count):
    import httpx

    errors = []
    for _ in range(failure_count):
        wrapped = RuntimeError("response already started")
        wrapped.__cause__ = AgentError("database_unavailable")
        errors.append(wrapped)
    response = httpx.Response(200, request=httpx.Request("GET", "http://test/stream"))
    api = SimpleNamespace(get=AsyncMock(side_effect=errors + [response]))
    if failure_count == 2:
        with pytest.raises(RuntimeError):
            await cli.read_public_stream(api, "/runs/durable-run/stream")
    else:
        assert await cli.read_public_stream(api, "/runs/durable-run/stream") == failure_count
    assert api.get.await_count == min(failure_count + 1, 2)
    assert all(call.args == ("/runs/durable-run/stream",) for call in api.get.await_args_list)


async def test_stream_reconnect_does_not_retry_unrelated_runtime_error(cli):
    api = SimpleNamespace(get=AsyncMock(side_effect=RuntimeError("unrelated failure")))
    with pytest.raises(RuntimeError):
        await cli.read_public_stream(api, "/runs/durable-run/stream")
    assert api.get.await_count == 1


def test_operator_extra_requires_explicit_confirmed_eval_mode(cli, monkeypatch, tmp_path):
    monkeypatch.setattr(
        "sys.argv",
        [
            "phase7d_eval.py",
            "eval",
            "--confirm-paid-eval",
            "--operator-extra-suite",
            "--output",
            str(tmp_path),
        ],
    )
    with pytest.raises(AgentError, match="operator_extra_requires_confirmed_eval"):
        cli.main()
    assert not (tmp_path / "checkpoint.json").exists()


@pytest.mark.parametrize("mode", ["smoke", "report"])
def test_affected_selection_cannot_change_smoke_or_report(cli, monkeypatch, tmp_path, mode):
    monkeypatch.setattr(
        "sys.argv", ["phase7d_eval.py", mode, "--case-id", "B01", "--output", str(tmp_path)]
    )
    with pytest.raises(AgentError, match="affected_cases_require_eval"):
        cli.main()
    assert not (tmp_path / "checkpoint.json").exists()


@pytest.mark.parametrize("case_ids", [["Z99"], ["B01", "B01"]])
def test_invalid_affected_selection_sends_no_paid_calls(cli, monkeypatch, tmp_path, case_ids):
    args = ["phase7d_eval.py", "eval", "--confirm-paid-eval", "--output", str(tmp_path)]
    for case_id in case_ids:
        args.extend(["--case-id", case_id])
    monkeypatch.setattr("sys.argv", args)
    for key, value in {
        "API_KEY": "unit-test-only-key",
        "MODEL": "gpt-6-luna",
        "SERVICE_TIER": "flex",
        "REASONING_EFFORT": "low",
    }.items():
        monkeypatch.setenv("VIP_AGENT_" + key, value)
    forbidden = AsyncMock(side_effect=AssertionError("No provider calls allowed"))
    monkeypatch.setattr(cli, "OpenAIProvider", forbidden)
    with pytest.raises(AgentError, match="invalid_affected_case_selection"):
        cli.main()
    forbidden.assert_not_called()
    assert not (tmp_path / "checkpoint.json").exists()


def test_affected_schedule_is_explicit_bounded_and_not_full_acceptance(
    cli, monkeypatch, tmp_path, capsys
):
    monkeypatch.setattr(
        "sys.argv",
        [
            "phase7d_eval.py",
            "eval",
            "--confirm-paid-eval",
            "--case-id",
            "A04",
            "--case-id",
            "C08",
            "--output",
            str(tmp_path),
        ],
    )
    for key, value in {
        "API_KEY": "unit-test-only-key",
        "MODEL": "gpt-6-luna",
        "SERVICE_TIER": "flex",
        "REASONING_EFFORT": "low",
    }.items():
        monkeypatch.setenv("VIP_AGENT_" + key, value)
    monkeypatch.setattr(cli, "identity", lambda *args: {"repository_sha": "unit-test-commit"})
    monkeypatch.setattr(cli, "smoke", AsyncMock())
    evaluate = AsyncMock()
    monkeypatch.setattr(cli, "evaluate", evaluate)
    cli.main()
    assert evaluate.call_args.kwargs == {"case_ids": {"A04", "C08"}}
    state = json.loads((tmp_path / "checkpoint.json").read_text())
    assert state["identities"][-1]["scheduled_case_ids"] == ["A04", "C08"]
    summary = json.loads((tmp_path / "report.json").read_text())
    assert summary["status"] == "NOT VERIFIED" and summary["unique_cases_executed"] == 0
    preflight = json.loads(capsys.readouterr().out.splitlines()[0])
    assert preflight["scope"] == "affected_cases" and preflight["max_runs"] == 4
    assert preflight["unique_cases"] == 2 and preflight["max_calls"] == 75


def test_projection_calibration_requires_full_attempted_schedule(cli):
    from phase7d_preflight import observed_role_turns

    suite, _ = load_suite(cli.ROOT / "evals/phase7d/suite-v1.json")
    keys = [f"1:{case.case_id}:{repeat}" for case, repeat in suite.schedule()]
    results = {key: {"status": "PASS"} for key in keys}
    calls = {
        str(index): {"case_key": key, "role": "data_quality"} for index, key in enumerate(keys)
    }
    budget = SimpleNamespace(state={"results": results, "calls": calls})
    assert observed_role_turns(budget, suite) == ({"data_quality": 1}, 1)

    # One outlier does not redefine the median; every actual call remains accounted.
    calls["extra"] = {"case_key": keys[0], "role": "data_quality"}
    assert observed_role_turns(budget, suite) == ({"data_quality": 1}, 1)
    results[keys[-1]] = {"status": "NOT_RUN_EXTERNAL_BLOCKER"}
    assert observed_role_turns(budget, suite) == ({}, None)
    results[keys[-1]] = {"status": "PROVIDER_FAILURE"}
    assert observed_role_turns(budget, suite) == ({"data_quality": 1}, 1)
    results["2:A04:0"] = {"status": "PASS"}
    assert observed_role_turns(budget, suite) == ({"data_quality": 1}, 1)


def test_projection_uses_measured_domain_free_scope_without_lowering_domain_bounds(cli):
    from phase7d_preflight import sampled_input_size

    samples = [
        {"role": "synthesis", "input_bytes": 40000, "domain_free": True},
        {"role": "synthesis", "input_bytes": 100000, "domain_free": False},
        {"role": "investigation", "input_bytes": 60000},
    ]
    assert sampled_input_size(samples, "synthesis", True) == 40000
    assert sampled_input_size(samples, "agent", True) == 40000
    assert sampled_input_size(samples, "synthesis", False) == 100000
    assert sampled_input_size(samples, "investigation", False) == 60000
    assert sampled_input_size(samples, "unseen_role", False) == 100000


def test_projection_prefers_current_case_and_preserves_unseen_role_fallback(cli):
    from phase7d_preflight import sampled_input_size

    samples = [
        {"case_id": "A01", "role": "synthesis", "input_bytes": 40000},
        {"case_id": "B01", "role": "synthesis", "input_bytes": 100000},
        {"case_id": "B01", "role": "investigation", "input_bytes": 60000},
    ]
    assert sampled_input_size(samples, "synthesis", False, "A01") == 40000
    assert sampled_input_size(samples, "agent", False, "A01") == 40000
    assert sampled_input_size(samples, "synthesis", False, "B01") == 100000
    assert sampled_input_size(samples, "investigation", False, "A01") == 60000
    assert sampled_input_size(samples, "unseen_role", False, "A01") == 100000


@pytest.mark.parametrize("mode", ["smoke", "report"])
def test_operator_budget_progress_is_eval_only(cli, monkeypatch, tmp_path, mode):
    monkeypatch.setattr(
        "sys.argv",
        ["phase7d_eval.py", mode, "--operator-budget-progress", "--output", str(tmp_path)],
    )
    with pytest.raises(AgentError, match="operator_budget_progress_requires_eval"):
        cli.main()
    assert not (tmp_path / "checkpoint.json").exists()


def test_operator_budget_progress_preserves_hard_limit_and_explicit_identity(
    cli, monkeypatch, tmp_path, capsys
):
    monkeypatch.setattr(
        "sys.argv",
        [
            "phase7d_eval.py",
            "eval",
            "--confirm-paid-eval",
            "--operator-budget-progress",
            "--output",
            str(tmp_path),
        ],
    )
    for key, value in {
        "API_KEY": "unit-test-only-key",
        "MODEL": "gpt-6-luna",
        "SERVICE_TIER": "flex",
        "REASONING_EFFORT": "low",
    }.items():
        monkeypatch.setenv("VIP_AGENT_" + key, value)
    monkeypatch.setenv("VIP_7D_MAX_SPEND_USD", "2.00")
    monkeypatch.setattr(cli, "identity", lambda *args: {"repository_sha": "unit-commit"})
    monkeypatch.setattr(cli, "smoke", AsyncMock())
    evaluate = AsyncMock()
    monkeypatch.setattr(cli, "evaluate", evaluate)
    cli.main()
    assert evaluate.call_args.kwargs == {"operator_budget_progress": True}
    budget = evaluate.call_args.args[1]
    assert budget.limit == Decimal("2.00")
    assert budget.state["identities"][-1]["operator_budget_progress"] is True
    assert json.loads(capsys.readouterr().out.splitlines()[0])["operator_budget_progress"] is True
    budget.state["calls"]["old-reservation"] = {
        "case_key": "prior-round",
        "status": "failed",
        "cost": {"total": "1.9999"},
    }
    with pytest.raises(AgentError, match="SKIPPED_BUDGET_LIMIT"):
        budget.begin("agent", 100, 512)
    assert budget.spend() == Decimal("1.9999")
    assert len(budget.state["calls"]) == 1
