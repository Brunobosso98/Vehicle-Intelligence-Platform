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
