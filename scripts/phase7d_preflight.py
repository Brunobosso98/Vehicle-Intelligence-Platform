"""Free prompt-size sampling through the production graph, before any bulk paid run."""

import json
from collections import Counter, defaultdict
from dataclasses import asdict
from decimal import Decimal
from math import ceil
from statistics import median

from openai.lib._pydantic import to_strict_json_schema
from phase7d_fixtures import vehicle_for
from vehicle_platform.agents.investigation.proposal import InvestigationInput
from vehicle_platform.agents.investigation.service import investigable
from vehicle_platform.agents.openai_provider import draft_schema, turn_data
from vehicle_platform.agents.prompts import INVESTIGATION_POLICY, SYSTEM_POLICY
from vehicle_platform.agents.provider import AgentError
from vehicle_platform.agents.schemas import AgentRun, RoutingProposal
from vehicle_platform.agents.scripted_provider import DeterministicProvider
from vehicle_platform.agents.specialists.policy import (
    SUPERVISOR_POLICY,
    specialist_policy,
)


class CaptureProvider(DeterministicProvider):
    def __init__(self, samples, case_id=None):
        super().__init__()
        self.samples = samples
        self.case_id = case_id

    def sample(self, role, request, response, policy, schema):
        # Match the adapter's public payload and schema. Byte counts are safe upper
        # estimates for inputs; output forecasts include the real smoke's reasoning use.
        encoded = json.dumps(asdict(request), default=str) + policy + json.dumps(schema)
        public = response.model_dump_json() if response is not None else "{}"
        self.samples.append(
            {
                "role": role,
                "case_id": self.case_id,
                "input_bytes": len(encoded.encode()) + 2048,
                "output_bytes": len(public.encode()),
            }
        )

    async def turn(self, request):
        result = await super().turn(request)
        role = (
            request.specialist.specialist.value
            if request.specialist
            else "synthesis"
            if request.supervisor
            else "agent"
        )
        policy = SYSTEM_POLICY + (
            specialist_policy(request.specialist.specialist)
            if request.specialist
            else SUPERVISOR_POLICY
            if request.supervisor
            else ""
        )
        # Match the compact wire payload; scoped context/question duplicates are
        # omitted by the real adapter while all recorded evidence remains present.
        public_request = {
            "question": request.question,
            "tools": request.tools,
            "data": turn_data(request),
            "messages": request.messages,
        }
        encoded = (
            json.dumps(public_request, separators=(",", ":"))
            + policy
            + json.dumps(draft_schema(request))
        )
        routing = (request.supervisor or {}).get("routing") or {}
        self.samples.append(
            {
                "role": role,
                "case_id": self.case_id,
                "input_bytes": len(encoded.encode()) + 2048,
                "output_bytes": len(result.draft.model_dump_json().encode())
                if result.draft is not None
                else 2,
                "domain_free": request.specialist is None
                and bool(routing)
                and not routing["selected"]
                and not routing["data_quality_gate"],
            }
        )
        return result

    async def route(self, request):
        result = await super().route(request)
        self.sample(
            "supervisor",
            request,
            result,
            SUPERVISOR_POLICY,
            RoutingProposal.model_json_schema(),
        )
        return result

    async def propose(self, request):
        result = await super().propose(request)
        self.sample(
            "investigation",
            request,
            result,
            INVESTIGATION_POLICY,
            to_strict_json_schema(type(result)),
        )
        return result


def observed_role_turns(budget, suite):
    """Calibrate typical turns only from an entirely attempted prior full schedule."""
    unattempted = {
        "NOT_RUN_EXTERNAL_BLOCKER",
        "SKIPPED_BUDGET_LIMIT",
        "INTERRUPTED",
        "HARNESS_FAILURE",
    }
    rounds = sorted(
        {int(key.split(":")[0]) for key in budget.state["results"]}, reverse=True
    )
    for round_id in rounds:
        keys = {
            f"{round_id}:{case.case_id}:{repeat}" for case, repeat in suite.schedule()
        }
        if not all(
            key in budget.state["results"]
            and budget.state["results"][key]["status"] not in unattempted
            for key in keys
        ):
            continue
        counts = defaultdict(Counter)
        for call in budget.state["calls"].values():
            if call["case_key"] in keys:
                counts[call["role"]][call["case_key"]] += 1
        return {
            role: max(1, ceil(median(cases.values()))) for role, cases in counts.items()
        }, round_id
    return {}, None


def sampled_input_size(samples, role, domain_free, case_id=None):
    if case_id is not None:
        matched = [
            s["input_bytes"]
            for s in samples
            if s.get("case_id") == case_id and s["role"] == role
        ]
        if not matched and role == "agent":
            matched = [
                s["input_bytes"]
                for s in samples
                if s.get("case_id") == case_id and s["role"] == "synthesis"
            ]
        if matched:
            return max(matched)
    candidates = [s["input_bytes"] for s in samples if s["role"] == role]
    if domain_free and role in {"agent", "synthesis"}:
        scoped = [
            s["input_bytes"]
            for s in samples
            if s.get("domain_free") and s["role"] in {"agent", "synthesis"}
        ]
        if scoped:
            return max(scoped)
    return max(candidates, default=max(s["input_bytes"] for s in samples))


async def project(
    api,
    app,
    fixture,
    suite,
    budget,
    settings,
    case_ids=None,
    operator_budget_progress=False,
    case_slots=None,
):
    samples = []
    app.state.agent_service.settings = settings.model_copy(
        update={
            "provider": "deterministic",
            "enabled": True,
            "mcp_url": app.state.agent_service.settings.mcp_url,
            "mcp_token": app.state.agent_service.settings.mcp_token,
            "investigation_token": app.state.agent_service.settings.investigation_token,
        }
    )
    for case in suite.cases:
        if case_ids is not None and case.case_id not in case_ids:
            continue
        app.state.agent_service.provider_factory = lambda case_id=case.case_id: (
            CaptureProvider(samples, case_id)
        )
        vehicle = vehicle_for(fixture, case)
        path = f"/api/v1/vehicles/{vehicle}/agent-runs"
        response = await api.post(
            path,
            json={
                "question": case.question,
                "session_id": fixture["recordings"].get(case.fixture),
            },
        )
        response.raise_for_status()
        run_id = response.json()["id"]
        (await api.get(f"{path}/{run_id}/stream")).raise_for_status()
        run = (await api.get(f"{path}/{run_id}")).json()
        if run["status"] != "completed":
            raise AgentError("deterministic_fixture_preflight_failed")
        typed_run = AgentRun.model_validate(run)
        if investigable(typed_run) and typed_run.result is not None:
            # Match the production proposal input with a deterministic provider only.
            # No OpenAI client or receipt is constructed for this free size sample.
            await CaptureProvider(samples, case.case_id).propose(
                InvestigationInput(
                    question=typed_run.user_question,
                    context=typed_run.result.context.model_dump(mode="json"),
                    evidence=[e.model_dump(mode="json") for e in typed_run.evidence],
                    missing_evidence=typed_run.result.missing_evidence,
                    supervisor=typed_run.supervisor.model_dump(mode="json")
                    if typed_run.supervisor
                    else None,
                )
            )
    if not samples:
        raise AgentError("fixture_prompt_sizes_unavailable")
    smoke_calls = [
        call for call in budget.state["calls"].values() if call["case_key"] == "smoke"
    ]
    observed_output = max(
        (call["usage"]["output_tokens"] for call in smoke_calls), default=512
    )
    token_fraction = max(
        Decimal("0.34"),
        max(
            (
                Decimal(call["usage"]["input_tokens"])
                / max(1, call["input_bound"] - 2048)
                for call in smoke_calls
            ),
            default=Decimal("0.34"),
        ),
    )
    typical_output = max(
        1024,
        observed_output,
        max(sample["output_bytes"] // 3 + 128 for sample in samples),
    )
    estimated = Decimal(0)
    role_turns, calibration_round = observed_role_turns(budget, suite)
    for case, repeat in suite.schedule():
        if case_ids is not None and case.case_id not in case_ids:
            continue
        if case_slots is not None and f"{case.case_id}:{repeat}" not in case_slots:
            continue
        roles = set(case.required_specialists) | set(case.allowed_optional_specialists)
        topology = ["supervisor", "synthesis", "agent"] + [
            role for role in roles for _ in range(role_turns.get(role, 2))
        ]
        if case.expect_phase7b:
            topology.append("investigation")
        for role in topology:
            size = sampled_input_size(
                samples, role, domain_free=not roles, case_id=case.case_id
            )
            # Use observed controlled fixture bytes, no caching discount, and public
            # output sizes plus smoke reasoning. Per-call reservations remain stricter.
            estimated += Decimal(
                budget.rates.cost(
                    min(272000, int(Decimal(size) * token_fraction)),
                    0,
                    min(settings.max_output_tokens, typical_output),
                )["total"]
            )
    budget.state["projection"] = {
        "method": "controlled_fixture_bytes_and_observed_smoke_usage",
        "samples": samples,
        "sampled_case_ids": sorted({s["case_id"] for s in samples}),
        "parent_prompt_scope": "Domain-free parent calls use actual domain-free samples; domain and unseen roles retain the largest matching/fallback sample",
        "observed_or_conservative_tokens_per_byte": str(token_fraction),
        "estimated_output_tokens": typical_output,
        "estimated_suite_cost_usd": str(estimated),
        "scheduled_case_ids": sorted(case_ids) if case_ids is not None else None,
        "scheduled_case_slots": sorted(case_slots) if case_slots is not None else None,
        "calibration_round": calibration_round,
        "observed_median_role_turns": role_turns,
        "contingency": "One extra agent turn per case; per-call hard reservations still enforce the accumulated ceiling",
        "operator_budget_progress": operator_budget_progress,
        "projected_full_schedule_fits": budget.spend() + estimated <= budget.limit,
    }
    budget.save()
    if budget.spend() + estimated > budget.limit and not operator_budget_progress:
        raise AgentError("projected_cost_exceeds_budget")
    return estimated
