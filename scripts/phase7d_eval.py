"""Explicit, bounded Phase 7D operator entrypoint. Default CI never invokes paid modes."""

import argparse
import asyncio
import fcntl
import json
import os
import secrets
import subprocess
from contextlib import asynccontextmanager
from datetime import UTC, date, datetime
from decimal import Decimal
from importlib.metadata import version
from pathlib import Path
from time import perf_counter
from uuid import UUID

import httpx
from agent_fixtures import domain_fingerprint
from agent_runtime import Process, free_port
from phase7d_fixtures import seed_phase7d, vehicle_for
from phase7d_preflight import project
from pydantic import SecretStr
from supervisor_fixtures import recording_csv
from vehicle_platform.acquisition.adapters import ReplayAdapter
from vehicle_platform.agents.config import AgentSettings, redact_data
from vehicle_platform.agents.investigation.service import investigable
from vehicle_platform.agents.openai_provider import OpenAIProvider
from vehicle_platform.agents.provider import AgentError, ModelInput
from vehicle_platform.api.domain_contracts import PreflightRequest
from vehicle_platform.core.config import Settings
from vehicle_platform.evaluation.grading import grade, summarize
from vehicle_platform.evaluation.metering import ToolMeter
from vehicle_platform.evaluation.phase7d import Ledger, Rates, atomic_json, load_suite
from vehicle_platform.events.synthetic import anomaly_scenario
from vehicle_platform.main import create_app

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / ".validation/phase7d"
INFRASTRUCTURE = {"provider_timeout", "provider_unavailable", "provider_rate_limit"}
FATAL_PROVIDER = {
    "provider_authentication",
    "provider_configuration",
    "provider_configuration_mismatch",
    "provider_usage_unavailable",
}


def failure_kind(errors):
    if "SKIPPED_BUDGET_LIMIT" in errors:
        return "SKIPPED_BUDGET_LIMIT"
    if "BUDGET_VIOLATION" in errors or "invalid_usage_or_long_context" in errors:
        return "HARNESS_FAILURE"
    if any(error in INFRASTRUCTURE | FATAL_PROVIDER for error in errors):
        return "PROVIDER_FAILURE"
    if any(
        error
        in {
            "run_timeout",
            "investigation_timeout",
            "specialist_timeout",
            "tool_timeout",
            "provider_retry_budget_exhausted",
        }
        for error in errors
    ):
        return "RUNTIME_FAILURE"
    return None


def stop_suite(result, provider_streak):
    errors = result.get("provider_categories", [])
    return (
        result["status"] in {"HARNESS_FAILURE", "SKIPPED_BUDGET_LIMIT"}
        or any(error in FATAL_PROVIDER for error in errors)
        or provider_streak >= 3
    )


def identity(settings, digest, suite):
    sha = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
    ).strip()
    dirty = subprocess.check_output(
        ["git", "status", "--porcelain"], cwd=ROOT, text=True
    ).strip()
    if dirty:
        raise AgentError("evaluation_requires_clean_commit")
    return {
        "repository_sha": sha,
        "dataset_hash": digest,
        "dataset_version": suite.version,
        "fixture_version": suite.fixture_version,
        "model": settings.model,
        "service_tier": settings.service_tier,
        "reasoning_effort": settings.reasoning_effort,
        "sdk_version": version("openai"),
        "api": "Responses",
        "provider": settings.provider,
        "prompt_version": settings.prompt_version,
        "agent_version": settings.agent_version,
        "max_steps": settings.max_steps,
        "max_tool_calls": settings.max_tool_calls,
        "max_specialists": settings.max_specialists,
        "model_timeout": settings.model_timeout,
        "run_timeout": settings.run_timeout,
        "max_provider_retries": settings.max_provider_retries,
        "max_output_tokens": settings.max_output_tokens,
    }


async def smoke(settings, budget):
    if budget.state["smoke"] is not None:
        if budget.state["smoke"]["status"] != "PASS":
            raise AgentError("smoke_failed_or_interrupted")
        return
    if any(c["case_key"] == "smoke" for c in budget.state["calls"].values()):
        raise AgentError("smoke_failed_or_interrupted")
    budget.case_key = "smoke"
    provider = OpenAIProvider(settings, budget)
    try:
        response, ticket = await provider._create(
            "smoke",
            model=settings.model,
            store=False,
            max_output_tokens=512,
            input="Call get_fixture with fixture_id controlled-smoke.",
            tools=[
                {
                    "type": "function",
                    "name": "get_fixture",
                    "description": "Read controlled public fixture",
                    "parameters": {
                        "type": "object",
                        "properties": {"fixture_id": {"type": "string"}},
                        "required": ["fixture_id"],
                        "additionalProperties": False,
                    },
                    "strict": True,
                }
            ],
            tool_choice={"type": "function", "name": "get_fixture"},
        )
        provider._record(response, ticket)
        calls = [item for item in response.output if item.type == "function_call"]
        if (
            len(calls) != 1
            or calls[0].name != "get_fixture"
            or json.loads(calls[0].arguments) != {"fixture_id": "controlled-smoke"}
        ):
            raise AgentError("smoke_function_call_failed")
        turn = await provider.turn(
            ModelInput(
                question="There are no recorded vehicle measurements. Return an insufficient-evidence draft.",
                tools=[],
                context={},
                evidence=[],
                messages=[
                    {
                        "type": "function_call",
                        "call_id": calls[0].call_id,
                        "name": calls[0].name,
                        "arguments": calls[0].arguments,
                    },
                    {
                        "type": "function_call_output",
                        "call_id": calls[0].call_id,
                        "output": json.dumps(
                            {"fixture_id": "controlled-smoke", "measurements": []}
                        ),
                    },
                ],
            )
        )
        if turn.draft is None:
            raise AgentError("smoke_structured_output_failed")
        budget.state["smoke"] = {
            "status": "PASS",
            "completed_at": datetime.now(UTC).isoformat(),
            "function_call": calls[0].name,
            "structured_output": True,
            "store": False,
        }
        budget.save()
    except AgentError as error:
        budget.state["smoke"] = {"status": "FAILED", "category": error.category}
        budget.save()
        raise
    finally:
        await provider.close()


@asynccontextmanager
async def stack(url, settings, budget):
    if not url.rsplit("/", 1)[-1].startswith("vehicle_test"):
        raise AgentError("disposable_database_required")
    token = secrets.token_urlsafe(48)
    port = free_port()
    base = f"http://127.0.0.1:{port}"
    env = os.environ | {
        "DATABASE_URL": url,
        "ENVIRONMENT": "test",
        "VIP_MCP_TOKEN": token,
        "VIP_MCP_TRANSPORT": "streamable-http",
        "VIP_MCP_PORT": str(port),
        "VIP_MCP_RESOURCE_URL": base + "/mcp",
        "VIP_MCP_ISSUER_URL": base,
    }
    process = Process(
        [str(ROOT / "apps/api/.venv/bin/python"), "-m", "vehicle_platform.mcp.cli"],
        env,
        base + "/ready",
    )
    local = settings.model_copy(
        update={
            "enabled": True,
            "mcp_url": base + "/mcp",
            "mcp_token": SecretStr(token),
            "investigation_token": SecretStr(token),
        }
    )
    app = create_app(Settings(database_url=url, environment="test"))
    agents = app.state.agent_service
    agents.settings = local
    app.state.eval_tool_meter = ToolMeter()
    agents.client_factory = lambda: app.state.eval_tool_meter.client(local)
    agents.provider_factory = lambda: OpenAIProvider(local, budget)
    try:
        await process.start()
        async with (
            app.router.lifespan_context(app),
            httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app),
                base_url="http://controlled-api",
                timeout=185,
                trust_env=False,
            ) as api,
        ):
            yield api, app, token
    finally:
        await process.stop()
        process.close()


async def evaluate(settings, budget, suite, output):
    url = os.environ.get("TEST_DATABASE_URL", "")
    if not url:
        raise AgentError("disposable_database_required")
    # Reseeding on resume changes only controlled fixture IDs, never completed results.
    fixture = await seed_phase7d(url)
    fingerprint = await domain_fingerprint(url)
    async with stack(url, settings, budget) as (api, app, token):
        real_settings = app.state.agent_service.settings
        if budget.state.get("projection") is None:
            projected = await project(api, app, fixture, suite, budget, settings)
            print(json.dumps({"projected_suite_cost_usd": str(projected)}), flush=True)
        agents = app.state.agent_service
        agents.settings = real_settings
        agents.provider_factory = lambda: OpenAIProvider(agents.settings, budget)
        service = app.state.investigation_service
        scenario = anomaly_scenario("phase7d-source", ())
        content = recording_csv(
            scenario, scenario.frames[0].observed_at, "normal"
        ).encode()
        capabilities = await ReplayAdapter(content, speed=0).capabilities()
        source_id = "phase7d-controlled-replay"
        for vehicle, configuration in [
            (fixture["vehicle"], fixture["configurations"][1]),
            (
                fixture["sparse_comparison_vehicle"],
                fixture["sparse_comparison_configurations"][1],
            ),
        ]:
            if configuration:
                await service.register_source(
                    UUID(vehicle),
                    UUID(configuration),
                    "replay",
                    source_id,
                    PreflightRequest(
                        adapter=capabilities.adapter,
                        signals={k: v.value for k, v in capabilities.signals.items()},
                        maximum_requests_per_second=capabilities.maximum_requests_per_second,
                        discovery_supported=False,
                    ),
                )
        provider_streak = 0
        for case, repeat in suite.schedule():
            key = budget.key(case, repeat)
            if not budget.start_case(key):
                continue
            started = perf_counter()
            result = {
                "case_id": case.case_id,
                "category": case.category,
                "critical": case.critical,
                "repeat": repeat,
                "case_key": key,
            }
            print(
                json.dumps(
                    {
                        "event": "eval.case.started",
                        "case_key": key,
                        "spend_usd": str(budget.spend()),
                    }
                ),
                flush=True,
            )
            try:
                vehicle = vehicle_for(fixture, case)
                app.state.eval_tool_meter.start(key, vehicle)
                session = fixture["recordings"].get(case.fixture)
                path = f"/api/v1/vehicles/{vehicle}/agent-runs"
                async with asyncio.timeout(230):
                    created = await api.post(
                        path, json={"question": case.question, "session_id": session}
                    )
                    created.raise_for_status()
                    run_id = created.json()["id"]
                    result["run_id"] = run_id
                    # Save the durable run handle before waiting for streamed completion.
                    budget.state["active_run_id"] = run_id
                    budget.save()
                    stream = await api.get(f"{path}/{run_id}/stream")
                    stream.raise_for_status()
                    run = (await api.get(f"{path}/{run_id}")).json()
                    audit = (await api.get(f"{path}/{run_id}/audit")).json()
                    plan = None
                    investigation_error = None
                    if investigable(
                        await app.state.agent_service.repository.get(
                            UUID(vehicle), UUID(run_id)
                        )
                    ):
                        proposed = await api.post(
                            f"/api/v1/vehicles/{vehicle}/investigations",
                            headers={"X-Investigation-Token": token},
                            json={
                                "agent_run_id": run_id,
                                "adapter": "replay",
                                "source_id": source_id,
                            },
                        )
                        if proposed.status_code == 201:
                            plan = proposed.json()
                        else:
                            investigation_error = (
                                proposed.json()
                                .get("error", {})
                                .get("code", "investigation_failed")
                            )
                    receipts = [
                        c
                        for c in budget.state["calls"].values()
                        if c["case_key"] == key
                    ]
                    result.update(
                        grade(
                            case,
                            run,
                            {
                                "tool_calls": app.state.eval_tool_meter.calls.get(
                                    key, []
                                )
                            },
                            plan,
                            receipts,
                        ),
                        run_id=run_id,
                        investigation_error=investigation_error,
                        provider_call_count=len(receipts),
                        latency_breakdown={
                            "supervisor": (run.get("supervisor") or {}).get(
                                "routing_seconds"
                            ),
                            "specialists": {
                                item["specialist"]: item.get("duration_seconds")
                                for item in (run.get("supervisor") or {}).get(
                                    "specialists", []
                                )
                            },
                            "mcp": sum(
                                call.get("duration_seconds") or 0
                                for call in audit.get("tool_calls", [])
                            ),
                            "synthesis": sum(
                                call.get("duration_seconds") or 0
                                for call in receipts
                                if call["role"] in {"synthesis", "agent"}
                            ),
                        },
                    )
                    errors = [run.get("error_category"), investigation_error] + [
                        item.get("error_category")
                        for item in (run.get("supervisor") or {}).get("specialists", [])
                    ]
                    kind = failure_kind(errors)
                    if kind:
                        result["status"] = kind
                        category_field = (
                            "provider_categories"
                            if kind == "PROVIDER_FAILURE"
                            else "runtime_categories"
                            if kind == "RUNTIME_FAILURE"
                            else "harness_categories"
                        )
                        result[category_field] = [e for e in errors if e]
                    atomic_json(
                        output / f"{key.replace(':', '-')}.json",
                        redact_data(
                            {
                                "run": run,
                                "audit": audit,
                                "mcp_receipts": app.state.eval_tool_meter.calls.get(
                                    key, []
                                ),
                                "plan": plan,
                                "result": result,
                            },
                            settings,
                        ),
                    )
            except AgentError as error:
                result.update(
                    status=error.category
                    if error.category == "SKIPPED_BUDGET_LIMIT"
                    else "HARNESS_FAILURE",
                    category=case.category,
                    error_category=error.category,
                )
            except (TimeoutError, httpx.HTTPError):
                result.update(
                    status="RUNTIME_FAILURE",
                    infrastructure_category="evaluation_timeout_or_transport",
                )
            except RuntimeError as error:
                if not isinstance(error.__cause__, AgentError):
                    raise
                result.update(
                    status="HARNESS_FAILURE", error_category=error.__cause__.category
                )
            result["latency_seconds"] = perf_counter() - started
            budget.finish_case(key, redact_data(result, settings))
            print(
                json.dumps(
                    {
                        "event": "eval.case.completed",
                        "case_key": key,
                        "status": result["status"],
                        "spend_usd": str(budget.spend()),
                    }
                ),
                flush=True,
            )
            # Individual bounded failures are observations. Repeated provider outages
            # and configuration/harness failures stop additional paid requests.
            provider_streak = (
                provider_streak + 1 if result["status"] == "PROVIDER_FAILURE" else 0
            )
            if budget.spend() >= budget.limit or stop_suite(result, provider_streak):
                for remaining, r in suite.schedule():
                    remaining_key = budget.key(remaining, r)
                    if remaining_key not in budget.state["results"]:
                        budget.finish_case(
                            remaining_key,
                            {
                                "status": "SKIPPED_BUDGET_LIMIT"
                                if budget.spend() >= budget.limit
                                or result["status"] == "SKIPPED_BUDGET_LIMIT"
                                else "NOT_RUN_EXTERNAL_BLOCKER",
                                "case_id": remaining.case_id,
                                "category": remaining.category,
                                "repeat": r,
                            },
                        )
                break
    if await domain_fingerprint(url) != fingerprint:
        budget.state["global_blocker"] = "canonical_data_mutated"
        budget.save()
        raise AgentError("canonical_data_mutated")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=["smoke", "eval", "report"])
    parser.add_argument("--confirm-paid-eval", action="store_true")
    parser.add_argument("--confirmation-suite", action="store_true")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    with (args.output / "operator.lock").open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise SystemExit("Evaluation already running; no request sent") from None
        checkpoint = args.output / "checkpoint.json"
        if args.mode == "report":
            if not checkpoint.exists():
                summary = {
                    "status": "NOT RUN",
                    "blocker": "No real evaluation checkpoint exists",
                }
            else:
                summary = summarize(json.loads(checkpoint.read_text()))
            atomic_json(args.output / "report.json", summary)
            print(json.dumps(summary, indent=2))
            return
        if not args.confirm_paid_eval:
            raise AgentError("explicit_paid_confirmation_required")
        if not os.getenv("VIP_AGENT_API_KEY"):
            raise AgentError("VIP_AGENT_API_KEY_missing_no_request_sent")
        for name, expected in [
            ("VIP_AGENT_MODEL", "gpt-6-luna"),
            ("VIP_AGENT_SERVICE_TIER", "flex"),
            ("VIP_AGENT_REASONING_EFFORT", "low"),
        ]:
            if os.getenv(name) != expected:
                raise AgentError("explicit_baseline_configuration_required")
        if (
            os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
            != "https://api.openai.com/v1"
        ):
            raise AgentError("official_openai_endpoint_required")
        settings = AgentSettings(
            enabled=False,
            provider="openai",
            max_steps=16,
            max_tool_calls=32,
            max_specialists=3,
            max_telemetry_calls=1,
            max_provider_retries=1,
            max_grounding_retries=1,
            max_concurrent_runs=1,
            max_output_tokens=4096,
            model_timeout=60,
            run_timeout=180,
        )
        limit = Decimal(os.getenv("VIP_7D_MAX_SPEND_USD", "2.00"))
        suite, digest = load_suite(ROOT / "evals/phase7d/suite-v1.json")
        rates = Rates()
        if (datetime.now(UTC).date() - date.fromisoformat(rates.verified_on)).days > 7:
            raise AgentError("official_pricing_reverification_required")
        config = identity(settings, digest, suite)
        budget = Ledger(
            checkpoint, config, limit, rates, confirmation=args.confirmation_suite
        )
        print(
            json.dumps(
                {
                    "model": settings.model,
                    "service_tier": settings.service_tier,
                    "reasoning_effort": settings.reasoning_effort,
                    "unique_cases": 80,
                    "max_runs": 120,
                    "max_provider_calls_per_case": 18,
                    "max_calls": 2163,
                    "max_spend_usd": str(limit),
                    "repository_sha": config["repository_sha"],
                    "round": budget.state["round"],
                }
            ),
            flush=True,
        )
        asyncio.run(smoke(settings, budget))
        if args.mode == "eval":
            asyncio.run(evaluate(settings, budget, suite, args.output))
        atomic_json(args.output / "report.json", summarize(budget.state))


if __name__ == "__main__":
    try:
        main()
    except AgentError as error:
        raise SystemExit(error.category) from None
