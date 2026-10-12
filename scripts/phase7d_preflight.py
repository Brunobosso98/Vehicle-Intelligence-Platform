"""Free prompt-size sampling through the production graph, before any bulk paid run."""

import json
from dataclasses import asdict
from decimal import Decimal

from vehicle_platform.agents.prompts import INVESTIGATION_POLICY, SYSTEM_POLICY
from vehicle_platform.agents.provider import AgentError
from vehicle_platform.agents.schemas import Draft, RoutingProposal
from vehicle_platform.agents.scripted_provider import DeterministicProvider
from vehicle_platform.agents.specialists.policy import (
    SUPERVISOR_POLICY,
    specialist_policy,
)


class CaptureProvider(DeterministicProvider):
    def __init__(self, samples):
        super().__init__()
        self.samples = samples

    def sample(self, role, request, response, policy, schema):
        # Match the adapter's public payload and schema. Byte counts are safe upper
        # estimates for inputs; output forecasts include the real smoke's reasoning use.
        encoded = json.dumps(asdict(request), default=str) + policy + json.dumps(schema)
        public = response.model_dump_json() if response is not None else "{}"
        self.samples.append(
            {
                "role": role,
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
        self.sample(role, request, result.draft, policy, Draft.model_json_schema())
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
            result.model_json_schema(),
        )
        return result


async def project(api, app, fixture, suite, budget, settings):
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
    app.state.agent_service.provider_factory = lambda: CaptureProvider(samples)
    identifiers = {"A01", "B01", "C01", "D01", "E01", "F01", "G03", "H03"}
    for case in suite.cases:
        if case.case_id not in identifiers:
            continue
        vehicle = (
            fixture["comparison_vehicle"]
            if case.fixture == "comparison"
            else fixture["vehicle"]
        )
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
    largest = max(sample["input_bytes"] for sample in samples)
    typical_output = max(
        1024,
        observed_output,
        max(sample["output_bytes"] // 3 + 128 for sample in samples),
    )
    estimated = Decimal(0)
    for case, _ in suite.schedule():
        roles = set(case.required_specialists) | set(case.allowed_optional_specialists)
        topology = ["supervisor", "synthesis", "agent"] + [
            role for role in roles for _ in range(2)
        ]
        if case.expect_phase7b:
            topology.append("investigation")
        for role in topology:
            size = max(
                (s["input_bytes"] for s in samples if s["role"] == role),
                default=largest,
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
        "observed_or_conservative_tokens_per_byte": str(token_fraction),
        "estimated_output_tokens": typical_output,
        "estimated_suite_cost_usd": str(estimated),
    }
    budget.save()
    if budget.spend() + estimated > budget.limit:
        raise AgentError("projected_cost_exceeds_budget")
    return estimated
