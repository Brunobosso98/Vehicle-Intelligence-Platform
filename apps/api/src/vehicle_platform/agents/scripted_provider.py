"""Deterministic provider adapter; the production orchestrator and grounding are unchanged."""

import re
from collections.abc import Callable
from typing import Any
from uuid import UUID

from vehicle_platform.agents.provider import AgentError, ModelInput, ModelTurn, ToolRequest
from vehicle_platform.agents.schemas import Binding, Claim, Classification, Draft, Usage


class ScriptedProvider:
    def __init__(
        self, turns: list[ModelTurn | AgentError | Callable[[ModelInput], ModelTurn]]
    ) -> None:
        self.turns = iter(turns)

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


class DeterministicProvider:
    """Small reproducible local provider with natural-language scenarios, never the default."""

    def __init__(self) -> None:
        self.index = 0

    async def turn(self, request: ModelInput) -> ModelTurn:
        self.index += 1
        question = request.question.casefold()
        context = request.context
        vehicle = str(context["vehicle_id"])
        sessions = context["sessions"]
        calls: list[tuple[str, dict[str, Any]]] = []
        executed = {m.get("name") for m in request.messages if m.get("type") == "function_call"}
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
            )
        )
        unsafe = bool(re.search(r"\b(flash|ecu|shell|sql|ignore)\b", question))
        comparison = any(
            word in question for word in ("configura", "intercooler", "peça", "antes", "depois")
        )
        events = any(word in question for word in ("boost drop", "estranho", "evento"))
        repeated = any(word in question for word in ("puxada", "pull", "consecut", "iat"))
        if sessions and not unsafe:
            if comparison and "compare_configurations" not in executed:
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
                    or any(word in question for word in ("timing", "pid", "sinal indispon"))
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
