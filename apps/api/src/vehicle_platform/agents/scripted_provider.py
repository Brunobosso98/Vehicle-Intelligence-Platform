"""Deterministic provider adapter; the production orchestrator and grounding are unchanged."""

import re
from collections.abc import Callable
from typing import Any
from uuid import UUID

from vehicle_platform.agents.investigation.domain import (
    GapType,
    HypothesisCategory,
    Resolution,
    SignalRole,
)
from vehicle_platform.agents.investigation.proposal import (
    InvestigationInput,
    InvestigationProposal,
    ProposedGap,
    ProposedHypothesis,
)
from vehicle_platform.agents.provider import AgentError, ModelInput, ModelTurn, ToolRequest
from vehicle_platform.agents.schemas import Binding, Claim, Classification, Draft, Usage


class ScriptedProvider:
    def __init__(
        self,
        turns: list[ModelTurn | AgentError | Callable[[ModelInput], ModelTurn]],
        proposal: InvestigationProposal | None = None,
    ) -> None:
        self.turns = iter(turns)
        self.proposal = proposal

    async def turn(self, request: ModelInput) -> ModelTurn:
        try:
            selected = next(self.turns)
        except StopIteration:
            raise AgentError("script_exhausted") from None
        if isinstance(selected, AgentError):
            raise selected
        return selected(request) if callable(selected) else selected

    async def close(self) -> None:
        return None

    async def propose(self, request: InvestigationInput) -> InvestigationProposal:
        if self.proposal is None:
            raise AgentError("script_exhausted")
        return self.proposal


class DeterministicProvider:
    """Small reproducible local provider with natural-language scenarios, never the default."""

    def __init__(self) -> None:
        self.index = 0

    async def propose(self, request: InvestigationInput) -> InvestigationProposal:
        question = request.question.casefold()
        missing = set(request.missing_evidence)
        if missing == {"technical_documentation"} or any(
            word in question for word in ("manual", "factory specification", "especificação bmw")
        ):
            return InvestigationProposal(
                hypotheses=[],
                gaps=[ProposedGap(category=GapType.TECHNICAL_DOCUMENTATION)],
            )
        if "data_quality" in missing or any(
            word in question for word in ("dropout", "timestamp", "amostragem", "qualidade")
        ):
            return InvestigationProposal(
                hypotheses=[ProposedHypothesis(category=HypothesisCategory.DATA_QUALITY)],
                gaps=[
                    ProposedGap(
                        category=GapType.DATA_QUALITY,
                        hypothesis_indexes=[0],
                        signal_roles=[SignalRole.DATA_QUALITY, SignalRole.ENGINE_SPEED],
                    )
                ],
            )
        if any(word in question for word in ("intercooler", "modifica", "before", "after")):
            return InvestigationProposal(
                hypotheses=[
                    ProposedHypothesis(category=HypothesisCategory.CONFIGURATION_ASSOCIATION)
                ],
                gaps=[
                    ProposedGap(category=GapType.COMPARABLE_HISTORY, hypothesis_indexes=[0]),
                    ProposedGap(
                        category=GapType.SIGNAL_OR_MEASUREMENT,
                        hypothesis_indexes=[0],
                        signal_roles=[SignalRole.INTAKE_TEMPERATURE, SignalRole.ENGINE_SPEED],
                    ),
                ],
            )
        if any(word in question for word in ("fuel", "combust", "hpfp", "pressão")):
            return InvestigationProposal(
                hypotheses=[ProposedHypothesis(category=HypothesisCategory.FUELING)],
                gaps=[
                    ProposedGap(
                        category=GapType.SIGNAL_OR_MEASUREMENT,
                        hypothesis_indexes=[0],
                        signal_roles=[SignalRole.HIGH_FUEL_PRESSURE, SignalRole.ENGINE_SPEED],
                        resolution=Resolution.HIGH,
                    )
                ],
            )
        if any(word in question for word in ("pull", "puxada", "iat", "slower", "lento")):
            return InvestigationProposal(
                hypotheses=[
                    ProposedHypothesis(category=HypothesisCategory.THERMAL),
                    ProposedHypothesis(category=HypothesisCategory.FUELING),
                    ProposedHypothesis(category=HypothesisCategory.THROTTLE_TORQUE_INTERVENTION),
                ],
                gaps=[
                    ProposedGap(
                        category=GapType.SIGNAL_OR_MEASUREMENT,
                        hypothesis_indexes=[0, 1, 2],
                        signal_roles=[
                            SignalRole.INTAKE_TEMPERATURE,
                            SignalRole.HIGH_FUEL_PRESSURE,
                            SignalRole.THROTTLE,
                        ],
                        resolution=Resolution.HIGH,
                    ),
                    ProposedGap(
                        category=GapType.SIGNAL_OR_MEASUREMENT,
                        hypothesis_indexes=[0, 2],
                        required=False,
                        signal_roles=[SignalRole.TIMING],
                    ),
                ],
            )
        return InvestigationProposal(
            hypotheses=[ProposedHypothesis(category=HypothesisCategory.PERFORMANCE_VARIATION)],
            gaps=[
                ProposedGap(category=GapType.COMPARABLE_HISTORY, hypothesis_indexes=[0]),
                ProposedGap(
                    category=GapType.SIGNAL_OR_MEASUREMENT,
                    hypothesis_indexes=[0],
                    signal_roles=[SignalRole.ENGINE_SPEED, SignalRole.VEHICLE_SPEED],
                ),
            ],
        )

    async def turn(self, request: ModelInput) -> ModelTurn:
        self.index += 1
        question = request.question.casefold()
        context = request.context
        vehicle = str(context["vehicle_id"])
        sessions = context["sessions"]
        calls: list[tuple[str, dict[str, Any]]] = []
        executed = {m.get("name") for m in request.messages if m.get("type") == "function_call"}
        investigation_follow_up = any(
            isinstance(message.get("content"), str)
            and message["content"].startswith("Investigation follow-up context")
            for message in request.messages
        )
        insufficient = any(
            word in question
            for word in (
                "caus",
                "caused",
                "exata",
                "diagn",
                "timing",
                "pid",
                "manual",
                "sinal indispon",
                "why",
                "por que",
                "porque",
            )
        )
        unsafe = bool(re.search(r"\b(flash|ecu|shell|sql|ignore)\b", question))
        comparison = any(
            word in question for word in ("configura", "intercooler", "peça", "antes", "depois")
        )
        events = any(word in question for word in ("boost drop", "estranho", "evento"))
        repeated = any(word in question for word in ("puxada", "pull", "consecut", "iat"))
        if sessions and not unsafe:
            if investigation_follow_up and "list_session_events" not in executed:
                calls = [("list_session_events", {"session_id": sessions[0]["id"], "limit": 20})]
            elif comparison and "compare_configurations" not in executed:
                records = [e for e in request.evidence if e["source_tool"] == "list_session_pulls"]
                represented = {e.get("session_id") for e in records}
                missing = [s for s in sessions[:6] if s["id"] not in represented]
                if missing:
                    calls = [
                        ("list_session_pulls", {"session_id": s["id"], "limit": 3})
                        for s in missing[:4]
                    ]
                else:
                    groups: dict[str, list[str]] = {}
                    for record in records:
                        config = record.get("configuration_id")
                        if config:
                            groups.setdefault(config, []).append(record["entity_id"])
                    populated = [ids[:9] for ids in groups.values() if len(ids) >= 2]
                    if len(populated) >= 2:
                        calls = [
                            (
                                "compare_configurations",
                                {"before_pull_ids": populated[-1], "after_pull_ids": populated[0]},
                            )
                        ]
            elif events and "list_session_events" not in executed:
                calls = [("list_session_events", {"session_id": sessions[0]["id"], "limit": 10})]
            elif repeated and "get_repeated_pull_analysis" not in executed:
                pulls = [e for e in request.evidence if e["source_tool"] == "list_session_pulls"]
                if "list_session_pulls" not in executed:
                    calls = [("list_session_pulls", {"session_id": sessions[0]["id"], "limit": 4})]
                elif len(pulls) >= 2:
                    calls = [
                        (
                            "get_repeated_pull_analysis",
                            {"pull_ids": [p["entity_id"] for p in pulls[:3]]},
                        )
                    ]
            elif (
                not (comparison or events or repeated)
                and "get_session_summary" not in executed
                and "última sessão" not in question
            ):
                calls = [("get_session_summary", {"session_id": sessions[0]["id"]})]
        if calls:
            return ModelTurn(
                tool_calls=[
                    ToolRequest(
                        call_id=f"scripted-{self.index}-{i}",
                        name=name,
                        arguments=args | {"vehicle_id": vehicle},
                    )
                    for i, (name, args) in enumerate(calls)
                ],
                usage=Usage(input_tokens=0, output_tokens=0, total_tokens=0, cached_input_tokens=0),
            )
        claims: list[Claim] = []
        preferred = (
            "compare_configurations"
            if comparison
            else "list_session_events"
            if events
            else "get_repeated_pull_analysis"
            if repeated
            else "list_sessions"
        )
        sources = [e for e in request.evidence if e["source_tool"] == preferred]
        quality_insufficient = any(e["warnings"] or e["truncated"] for e in sources)
        insufficient = insufficient or quality_insufficient
        for source in sources[:3]:
            candidates = source["facts"]
            if preferred == "list_session_events":
                selected = [f for f in candidates if f["path"] == "/event_type"]
            elif preferred == "list_sessions":
                selected = [
                    f
                    for f in candidates
                    if f["path"] in {"/id", "/started_at", "/configuration_id"}
                ]
            else:
                selected = [
                    f
                    for f in candidates
                    if type(f["value"]) in {int, float}
                    and any(
                        w in f["path"].lower() for w in ("iat", "temperature", "delta", "duration")
                    )
                ][:4]
                if not selected:
                    selected = [f for f in candidates if type(f["value"]) in {int, float}][:2]
                if comparison:
                    deltas = [
                        f
                        for f in candidates
                        if f["path"].startswith("/result/metric_deltas/")
                        and f["path"].endswith("/absolute")
                        and type(f["value"]) in {int, float}
                    ]
                    if deltas:
                        selected = sorted(deltas, key=lambda f: (f["value"] == 0, f["path"]))[:4]
            if selected:
                identifiers = [UUID(source["id"])]
                classification = Classification.OBSERVATION
                template = "recorded_fact"
                if comparison:
                    identifiers += [
                        UUID(e["id"])
                        for e in request.evidence
                        if e["source_tool"] == "list_vehicle_configurations"
                    ][:4]
                    valid_comparison = (
                        not source["warnings"]
                        and not source["truncated"]
                        and request.correction != "unsupported_association"
                        and any(
                            f["path"] == "/result/sufficiency" and f["value"] == "sufficient"
                            for f in source["facts"]
                        )
                    )
                    if valid_comparison:
                        classification, template = (
                            Classification.ASSOCIATION,
                            "temporal_association",
                        )
                    else:
                        insufficient = True
                claims.append(
                    Claim.model_validate(
                        {
                            "classification": classification,
                            "template": template,
                            "bindings": [
                                Binding(evidence_id=UUID(source["id"]), **f) for f in selected
                            ],
                            "evidence_ids": identifiers,
                        }
                    )
                )
        if insufficient or unsafe or not claims:
            claims.append(
                Claim(
                    classification=Classification.INSUFFICIENT_EVIDENCE,
                    template="unsafe_operation_refused" if unsafe else "insufficient_evidence",
                    bindings=[],
                    evidence_ids=[],
                )
            )
        return ModelTurn(
            draft=Draft(
                confidence="low" if insufficient or unsafe else "moderate",
                claims=claims,
                missing_evidence=[
                    "technical_documentation"
                    if "manual" in question
                    else "signal_or_measurement"
                    if quality_insufficient
                    or any(
                        word in question
                        for word in (
                            "timing",
                            "pid",
                            "sinal indispon",
                            "why",
                            "por que",
                            "porque",
                        )
                    )
                    else "comparable_history"
                    if comparison and not sources
                    else "mechanical_cause"
                ]
                if not unsafe and (insufficient or not sources)
                else [],
            ),
            usage=Usage(input_tokens=0, output_tokens=0, total_tokens=0, cached_input_tokens=0),
        )

    async def close(self) -> None:
        return None
