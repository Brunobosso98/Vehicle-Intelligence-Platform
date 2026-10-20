"""Fault injection at the provider seam; production HTTP routes, graph, MCP and DB remain real."""

import asyncio
from uuid import UUID

import httpx
from pydantic import SecretStr
from vehicle_platform.agents.config import AgentSettings
from vehicle_platform.agents.mcp_client import connect
from vehicle_platform.agents.provider import AgentError, ModelTurn, ToolRequest
from vehicle_platform.agents.schemas import Binding, Claim, Draft, Specialist, Usage
from vehicle_platform.agents.scripted_provider import DeterministicProvider
from vehicle_platform.core.config import Settings
from vehicle_platform.main import create_app

ZERO = Usage(input_tokens=0, output_tokens=0, total_tokens=0, cached_input_tokens=0)


class FaultProvider(DeterministicProvider):
    def __init__(self, mode, fixture):
        super().__init__()
        self.mode, self.fixture = mode, fixture
        self.entered = set()
        self.ready, self.release = asyncio.Event(), asyncio.Event()

    async def specialist_turn(self, request):
        scope = request.specialist
        role = scope.specialist
        if self.mode in {"parallel", "cancel"} and role is not Specialist.DATA_QUALITY:
            self.entered.add(role)
            if len(self.entered) == 2:
                self.ready.set()
            await self.release.wait()
        if self.mode == "quality_failure" and role is Specialist.DATA_QUALITY:
            raise AgentError("provider_unavailable")
        if role is Specialist.THERMAL:
            if self.mode == "timeout":
                raise TimeoutError
            if self.mode == "failure":
                raise AgentError("provider_unavailable")
            if self.mode == "escalation":
                return ModelTurn(
                    tool_calls=[
                        ToolRequest(
                            call_id="attempt",
                            name="get_vehicle",
                            arguments={"vehicle_id": str(scope.vehicle_id)},
                        )
                    ],
                    usage=ZERO,
                )
            if self.mode == "cross_vehicle":
                return ModelTurn(
                    tool_calls=[
                        ToolRequest(
                            call_id="attempt",
                            name="get_session_summary",
                            arguments={
                                "vehicle_id": self.fixture["other_vehicle"],
                                "session_id": str(scope.session_ids[0]),
                            },
                        )
                    ],
                    usage=ZERO,
                )
            if self.mode == "foreign_evidence":
                foreign = self.fixture["foreign_evidence"]
                return ModelTurn(
                    draft=Draft(
                        confidence="high",
                        missing_evidence=[],
                        claims=[
                            Claim(
                                classification="OBSERVATION",
                                template="recorded_fact",
                                evidence_ids=[foreign],
                                bindings=[
                                    Binding(
                                        evidence_id=foreign,
                                        path="/id",
                                        value=str(scope.vehicle_id),
                                    )
                                ],
                            )
                        ],
                    ),
                    usage=ZERO,
                )
            if self.mode == "oversized_turn":
                return ModelTurn(
                    tool_calls=[
                        ToolRequest(
                            call_id=f"attempt-{i}",
                            name="get_session_summary",
                            arguments={
                                "vehicle_id": str(scope.vehicle_id),
                                "session_id": str(scope.session_ids[0]),
                            },
                        )
                        for i in range(5)
                    ],
                    usage=ZERO,
                )
        if (
            self.mode == "reuse"
            and role is not Specialist.DATA_QUALITY
            and not request.messages
        ):
            return ModelTurn(
                tool_calls=[
                    ToolRequest(
                        call_id="reuse",
                        name="get_session_summary",
                        arguments={
                            "vehicle_id": str(scope.vehicle_id),
                            "session_id": str(scope.session_ids[0]),
                        },
                    )
                ],
                usage=ZERO,
            )
        return await super().specialist_turn(request)


async def fault_scenarios(url, stack, fixture, score, counters, execution_score):
    app = create_app(Settings(database_url=url, environment="test"))
    service = app.state.agent_service
    settings = AgentSettings(
        enabled=True,
        provider="deterministic",
        mcp_token=SecretStr(stack["token"]),
        mcp_url=stack["mcp"].ready.removesuffix("/ready") + "/mcp",
    )
    service.settings = settings
    service.client_factory = lambda: connect(settings)
    reports = []
    async with (
        app.router.lifespan_context(app),
        httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://fault-api",
            timeout=100,
        ) as api,
    ):
        base = f"/api/v1/vehicles/{fixture['vehicle']}/agent-runs"
        # Capture a real other-vehicle evidence ID; it must not enter the subsequent run.
        service.provider_factory = DeterministicProvider
        foreign = (
            await api.post(
                f"/api/v1/vehicles/{fixture['other_vehicle']}/agent-runs",
                json={"question": "What was my last session?"},
            )
        ).json()
        await service.tasks[UUID(foreign["id"])]
        foreign = (
            await api.get(
                f"/api/v1/vehicles/{fixture['other_vehicle']}/agent-runs/{foreign['id']}"
            )
        ).json()
        fixture = fixture | {"foreign_evidence": UUID(foreign["evidence"][0]["id"])}
        for mode, expected in (
            ("escalation", "specialist_tool_policy_violation"),
            ("cross_vehicle", "tool_policy_violation"),
            ("foreign_evidence", "unknown_evidence"),
            ("timeout", "specialist_timeout"),
            ("failure", "provider_unavailable"),
            ("quality_failure", "provider_unavailable"),
            ("oversized_turn", "invalid_specialist_result"),
            ("reuse", None),
            ("parallel", None),
            ("cancel", "cancelled"),
        ):
            provider = FaultProvider(mode, fixture)
            service.provider_factory = lambda provider=provider: provider
            created = await api.post(
                base,
                json={
                    "question": "Why did performance degrade after repeated pulls?",
                    "session_id": fixture["recordings"]["thermal"],
                },
            )
            assert created.status_code == 202, created.text
            identifier = created.json()["id"]
            task = service.tasks[UUID(identifier)]
            if mode in {"parallel", "cancel"}:
                # Allow slow full-stack scheduling while staying below the
                # specialist timeout, so both provider calls can reach the gate.
                async with asyncio.timeout(20):
                    await provider.ready.wait()
                assert provider.entered == {Specialist.PERFORMANCE, Specialist.THERMAL}
                if mode == "cancel":
                    response = await api.post(f"{base}/{identifier}/cancel")
                    assert response.status_code == 200, response.text
                else:
                    provider.release.set()
            await task
            run = (await api.get(f"{base}/{identifier}")).json()
            assert run["status"] == (
                "cancelled" if mode == "cancel" else "completed"
            ), (mode, run)
            results = run["supervisor"]["specialists"]
            target = "data_quality" if mode == "quality_failure" else "thermal"
            result = next(r for r in results if r["specialist"] == target)
            assert result["error_category"] == expected, (mode, result)
            if expected:
                assert not result["findings"]
            if mode == "quality_failure":
                assert (
                    len([r for r in results if r["status"] != "skipped"]) == 1
                    and run["supervisor"]["sufficiency"] == "UNRELIABLE_DATA"
                )
                assert all(
                    r["model_turn_count"] == r["tool_call_count"] == 0
                    for r in results
                    if r["status"] == "skipped"
                )
            elif mode != "cancel":
                assert (
                    next(r for r in results if r["specialist"] == "performance")[
                        "status"
                    ]
                    == "completed"
                )
            if mode == "reuse":
                assert run["supervisor"]["cache_hits"] >= 2
            audit = (await api.get(f"{base}/{identifier}/audit")).json()
            assert (
                sum(c["tool_name"] == "get_vehicle" for c in audit["tool_calls"]) == 1
            )
            assert len(audit["tool_calls"]) <= settings.max_tool_calls
            assert all(
                e["vehicle_id"] == fixture["vehicle"] and e["run_id"] == identifier
                for e in run["evidence"]
            )
            events = (await api.get(f"{base}/{identifier}/events")).json()
            assert [e["sequence"] for e in events] == list(range(1, len(events) + 1)), (
                mode,
                [(e["sequence"], e["type"]) for e in events],
            )
            execution_score(run, audit, events, counters)
            assert (
                sum(
                    e["type"] in {"run_completed", "run_cancelled", "run_failed"}
                    for e in events
                )
                == 1
            )
            replay = await api.get(f"{base}/{identifier}/stream?after=1")
            assert "event: run_started" not in replay.text
            if mode != "cancel":
                score(run, counters)
            reports.append(
                {
                    "name": mode,
                    "passed": True,
                    "error_category": expected,
                    "mcp_calls": len(audit["tool_calls"]),
                }
            )
        service.provider_factory = DeterministicProvider
        recovered = (
            await api.post(
                base,
                json={
                    "question": "Is heat soak increasing?",
                    "session_id": fixture["recordings"]["thermal"],
                },
            )
        ).json()
        await service.tasks[UUID(recovered["id"])]
        final = (await api.get(f"{base}/{recovered['id']}")).json()
        assert final["status"] == "completed" and all(
            r["status"] == "completed" for r in final["supervisor"]["specialists"]
        )
        reports.append({"name": "recovery_after_faults", "passed": True})
    return reports
