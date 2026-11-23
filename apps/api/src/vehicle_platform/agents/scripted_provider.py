"""Deterministic provider adapter; the production orchestrator and grounding are unchanged."""

import asyncio
import re
from collections.abc import Callable
from dataclasses import replace
from typing import Any, Literal
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
from vehicle_platform.agents.provider import (
    AgentError,
    ModelInput,
    ModelTurn,
    RoutingInput,
    ToolRequest,
)
from vehicle_platform.agents.schemas import (
    Binding,
    Claim,
    Classification,
    Draft,
    Evidence,
    Intent,
    RoutingProposal,
    Specialist,
    Usage,
)
from vehicle_platform.agents.specialists.routing import hints_for


class ScriptedProvider:
    def __init__(
        self,
        turns: list[ModelTurn | AgentError | Callable[[ModelInput], ModelTurn]],
        proposal: InvestigationProposal | None = None,
        routing: RoutingProposal | None = None,
    ) -> None:
        self.turns = iter(turns)
        self.proposal = proposal
        self.routing = routing

    async def route(self, request: RoutingInput) -> RoutingProposal:
        return self.routing or await DeterministicProvider().route(request)

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

    async def route(self, request: RoutingInput) -> RoutingProposal:
        hints = hints_for(
            request.question, [Evidence.model_validate(item) for item in request.evidence]
        )
        return RoutingProposal(
            intent=hints.intent or Intent.FACTUAL,
            specialists=list(hints.required),
            usage=Usage(input_tokens=0, output_tokens=0, total_tokens=0, cached_input_tokens=0),
        )

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
            domain_requested = any(
                word in question
                for word in (
                    "intercooler",
                    "modifica",
                    "configuration",
                    "configura",
                    "boost",
                    "fuel",
                    "combust",
                    "hpfp",
                    "pressão",
                    "lambda",
                    "pull",
                    "puxada",
                    "iat",
                    "slower",
                    "lento",
                )
            )
            if not domain_requested:
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
            proposal = self.domain_investigation(question)
            quality_index = len(proposal.hypotheses)
            proposal.hypotheses.append(ProposedHypothesis(category=HypothesisCategory.DATA_QUALITY))
            proposal.gaps.insert(
                0,
                ProposedGap(
                    category=GapType.DATA_QUALITY,
                    hypothesis_indexes=[quality_index],
                    signal_roles=[SignalRole.DATA_QUALITY, SignalRole.ENGINE_SPEED],
                ),
            )
            return proposal
        return self.domain_investigation(question)

    @staticmethod
    def domain_investigation(question: str) -> InvestigationProposal:
        if any(
            word in question for word in ("intercooler", "modifica", "configuration", "configura")
        ):
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
        if "boost" in question:
            return InvestigationProposal(
                hypotheses=[ProposedHypothesis(category=HypothesisCategory.AIRFLOW_BOOST)],
                gaps=[
                    ProposedGap(
                        category=GapType.SIGNAL_OR_MEASUREMENT,
                        hypothesis_indexes=[0],
                        signal_roles=[
                            SignalRole.BOOST,
                            SignalRole.THROTTLE,
                            SignalRole.ENGINE_SPEED,
                        ],
                        resolution=Resolution.HIGH,
                    )
                ],
            )
        if any(word in question for word in ("fuel", "combust", "hpfp", "pressão", "lambda")):
            return InvestigationProposal(
                hypotheses=[ProposedHypothesis(category=HypothesisCategory.FUELING)],
                gaps=[
                    ProposedGap(
                        category=GapType.SIGNAL_OR_MEASUREMENT,
                        hypothesis_indexes=[0],
                        signal_roles=[
                            SignalRole.LAMBDA
                            if "lambda" in question
                            else SignalRole.HIGH_FUEL_PRESSURE,
                            SignalRole.ENGINE_SPEED,
                        ],
                        resolution=Resolution.HIGH,
                    )
                ],
            )
        if any(word in question for word in ("pull", "puxada", "iat", "slower", "lento")):
            return DeterministicProvider.repeated_investigation()
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

    @staticmethod
    def repeated_investigation() -> InvestigationProposal:
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

    async def turn(self, request: ModelInput) -> ModelTurn:
        if request.specialist:
            return await self.specialist_turn(request)
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
        unsupported_source_request = (
            (
                ("another run" in question or "from another run" in question)
                and any(word in question for word in ("cite", "citation", "current"))
            )
            or (
                any(word in question for word in ("future pull", "puxada futura"))
                and any(word in question for word in ("cutoff", "original"))
            )
            or (
                any(
                    word in question for word in ("convert", "conversion", "converter", "conversão")
                )
                and any(word in question for word in ("without", "sem evidência", "sem evidencia"))
            )
        )
        insufficient = insufficient or unsupported_source_request
        benign_quoted_instruction = bool(
            re.search(
                r"\b(explain|describe|interpret|explique|descreva|interprete)\b"
                r".{0,80}\b(quoted|quote|phrase|frase citada|citação)\b",
                question,
            )
        )
        unsafe = bool(re.search(r"\b(flash|ecu|shell|sql)\b", question)) or (
            bool(re.search(r"\bignore\b", question)) and not benign_quoted_instruction
        )
        comparison = any(
            word in question for word in ("configura", "intercooler", "peça", "antes", "depois")
        )
        vehicle_profile_lookup = any(
            phrase in question
            for phrase in (
                "vehicle nickname",
                "nickname recorded",
                "nickname is recorded",
                "nickname está registrado",
            )
        )
        if (
            request.knowledge
            and any(
                word in question for word in ("boost", "hpfp", "rail pressure", "fuel pressure")
            )
            and not any(
                word in question
                for word in (
                    "before",
                    "after",
                    "antes",
                    "depois",
                    "upgrade",
                    "modifi",
                    "intercooler",
                )
            )
        ):
            # A calibration's configuration is not itself a before/after hardware comparison.
            comparison = False
        events = any(word in question for word in ("boost drop", "estranho", "evento"))
        repeated = any(word in question for word in ("puxada", "pull", "consecut", "iat"))
        if (
            vehicle_profile_lookup
            and not unsafe
            and not unsupported_source_request
            and "get_vehicle" not in executed
        ):
            calls = [("get_vehicle", {})]
        elif sessions and not unsafe and not unsupported_source_request:
            if investigation_follow_up and "list_session_events" not in executed:
                calls = [("list_session_events", {"session_id": sessions[0]["id"], "limit": 20})]
            elif comparison and "compare_configurations" not in executed:
                records = [e for e in request.evidence if e["source_tool"] == "list_session_pulls"]
                represented = {e.get("session_id") for e in records}
                # Bound capture reads while preserving both sides of the temporal boundary.
                # Taking only the six newest sessions can silently omit the earlier configuration.
                by_config: dict[str, list[dict[str, Any]]] = {}
                for session in sessions:
                    if session.get("configuration_id") and session.get(
                        "temporal_configuration_valid"
                    ):
                        by_config.setdefault(str(session["configuration_id"]), []).append(session)
                comparison_sessions = [
                    session for group in list(by_config.values())[:2] for session in group[:3]
                ]
                missing = [s for s in comparison_sessions if s["id"] not in represented]
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
                            configuration_pull_ids = groups.setdefault(config, [])
                            if record["entity_id"] not in configuration_pull_ids:
                                configuration_pull_ids.append(record["entity_id"])
                    timeline = {
                        c["id"]: c["effective_at"] for c in request.context["configurations"]
                    }
                    populated = [
                        groups[key][:9]
                        for key in sorted(groups, key=lambda key: timeline.get(key, ""))
                        if len(groups[key]) >= 2
                    ]
                    if len(populated) >= 2:
                        calls = [
                            (
                                "compare_configurations",
                                {"before_pull_ids": populated[0], "after_pull_ids": populated[-1]},
                            )
                        ]
            elif events and "list_session_events" not in executed:
                calls = [("list_session_events", {"session_id": sessions[0]["id"], "limit": 10})]
            elif repeated and "get_repeated_pull_analysis" not in executed:
                pulls = list(
                    {
                        e["entity_id"]: e
                        for e in request.evidence
                        if e["source_tool"] == "list_session_pulls"
                        and e.get("session_id") == request.context["sessions"][0]["id"]
                        and e.get("entity_id")
                    }.values()
                )
                if not pulls and "list_session_pulls" not in executed:
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
                and not vehicle_profile_lookup
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
            else "get_vehicle"
            if vehicle_profile_lookup
            else "list_sessions"
        )
        if (
            request.knowledge
            and not comparison
            and not unsafe
            and request.supervisor
            and request.supervisor.get("sufficiency") != "UNRELIABLE_DATA"
            and any(
                word in question
                for word in (
                    "hpfp",
                    "fuel pressure",
                    "rail pressure",
                    "pressão de combustível",
                    "pressao de combustivel",
                    "boost",
                )
            )
        ):
            preferred = "get_telemetry_window"
        requested_fuel_pressure = any(
            phrase in question
            for phrase in (
                "hpfp",
                "fuel pressure",
                "rail pressure",
                "pressão de combustível",
                "pressao de combustivel",
            )
        )
        sources = [e for e in request.evidence if e["source_tool"] == preferred]
        quality_insufficient = any(e["warnings"] or e["truncated"] for e in sources)
        insufficient = insufficient or quality_insufficient
        for source in sources[:3]:
            candidates = source["facts"]
            if preferred == "get_telemetry_window":
                selected = []
                signals = set()
                by_path = {fact["path"]: fact for fact in candidates}
                if requested_fuel_pressure and not any(
                    fact.get("path", "").endswith("/signal")
                    and fact.get("value") == "fuel.high_pressure"
                    for fact in candidates
                ):
                    insufficient = True
                    continue
                for fact in candidates:
                    if not fact["path"].endswith("/signal") or fact["value"] in signals:
                        continue
                    value = by_path.get(fact["path"].removesuffix("/signal") + "/value")
                    if value and value.get("unit") and type(value["value"]) in {int, float}:
                        signals.add(fact["value"])
                        selected.extend([fact, value])
                    if len(signals) == 4:
                        break
            elif preferred == "list_session_events":
                selected = [f for f in candidates if f["path"] == "/event_type"]
            elif preferred == "list_sessions":
                selected = [
                    f
                    for f in candidates
                    if f["path"] in {"/id", "/started_at", "/configuration_id"}
                ]
            elif preferred == "get_vehicle":
                selected = [f for f in candidates if f["path"] == "/nickname"]
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
        if request.supervisor and not request.supervisor.get("conflicts"):
            for source in sources:
                if (
                    source["source_tool"] != "get_repeated_pull_analysis"
                    or source["warnings"]
                    or source["truncated"]
                ):
                    continue
                numeric = [f for f in source["facts"] if type(f["value"]) in {int, float}]
                temperatures = [f for f in numeric if f["path"].endswith("/end_iat")]
                acceleration = [
                    f for f in numeric if f["path"].endswith("/normalized_acceleration")
                ]
                if (
                    len(temperatures) >= 2
                    and len(acceleration) >= 2
                    and temperatures[-1]["value"] > temperatures[0]["value"]
                    and acceleration[-1]["value"] < acceleration[0]["value"]
                ):
                    identifier = UUID(source["id"])
                    claims.append(
                        Claim(
                            classification=Classification.HYPOTHESIS,
                            template="thermal_hypothesis",
                            evidence_ids=[identifier],
                            bindings=[
                                Binding(evidence_id=identifier, **f)
                                for f in (
                                    temperatures[0],
                                    temperatures[-1],
                                    acceleration[0],
                                    acceleration[-1],
                                )
                            ],
                        )
                    )
                    break
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

    async def specialist_turn(self, request: ModelInput) -> ModelTurn:
        scope = request.specialist
        if scope is None:
            raise AgentError("invalid_specialist_request")
        specialist = scope.specialist
        executed = {m.get("name") for m in request.messages if m.get("type") == "function_call"}
        prediction_sources = [
            source
            for source in request.evidence
            if source["source_tool"] == "get_prediction_evidence"
        ]
        for source in prediction_sources:
            values = {fact["path"]: fact["value"] for fact in source["facts"]}
            task, family = values.get("/prediction/task"), values.get("/prediction/family")
            relevant = {
                Specialist.THERMAL: (isinstance(task, str) and "THERMAL" in task)
                or family == "thermal",
                Specialist.PERFORMANCE: (isinstance(task, str) and "PERFORMANCE" in task)
                or family == "performance",
                Specialist.FUEL_AIR_BOOST: (isinstance(task, str) and "FUEL" in task)
                or family in {"fuel", "boost_air"},
                Specialist.DATA_QUALITY: False,
            }[specialist]
            if not relevant:
                continue
            horizon = values.get("/prediction/horizon")
            template: Literal["prediction_result", "anomaly_result"]
            if horizon == "NEXT_PULL":
                template = "prediction_result"
                classification = Classification.MODEL_CLASSIFICATION
                paths = (
                    "/prediction/horizon",
                    "/prediction/task",
                    "/prediction/score",
                    "/prediction/threshold",
                    "/prediction/decision",
                    "/prediction/model_version",
                    "/prediction/source_role",
                    "/prediction/effective_cutoff",
                )
            elif horizon == "AFTER_PULL_OFFLINE":
                template = "anomaly_result"
                classification = (
                    Classification.STATISTICAL_OUTLIER
                    if values.get("/prediction/decision") == "ANOMALOUS"
                    else Classification.MODEL_CLASSIFICATION
                )
                paths = (
                    "/prediction/horizon",
                    "/prediction/family",
                    "/prediction/status",
                    "/prediction/score",
                    "/prediction/threshold",
                    "/prediction/detector_version",
                    "/prediction/detector_method",
                    "/prediction/effective_cutoff",
                )
            else:
                continue
            facts = {fact["path"]: fact for fact in source["facts"]}
            if not all(path in facts for path in paths):
                continue
            return ModelTurn(
                draft=Draft(
                    confidence="low",
                    claims=[
                        Claim(
                            classification=classification,
                            template=template,
                            evidence_ids=[UUID(source["id"])],
                            bindings=[
                                Binding(
                                    evidence_id=UUID(source["id"]),
                                    path=path,
                                    value=facts[path]["value"],
                                    unit=facts[path].get("unit"),
                                )
                                for path in paths
                            ],
                        )
                    ],
                    missing_evidence=[],
                ),
                usage=Usage(input_tokens=0, output_tokens=0, total_tokens=0, cached_input_tokens=0),
            )
        if specialist is Specialist.PERFORMANCE:
            q = request.question.casefold()
            if any(word in q for word in ("configur", "intercooler", "modific")):
                return await self.turn(replace(request, specialist=None))
            if request.context["sessions"] and any(word in q for word in ("pull", "puxada")):
                pulls = list(
                    {
                        e["entity_id"]: e
                        for e in request.evidence
                        if e["source_tool"] == "list_session_pulls"
                        and e.get("session_id") == request.context["sessions"][0]["id"]
                        and e.get("entity_id")
                    }.values()
                )
                tool: tuple[str, dict[str, Any]] | None = None
                if not pulls and "list_session_pulls" not in executed:
                    tool = (
                        "list_session_pulls",
                        {"session_id": request.context["sessions"][0]["id"], "limit": 4},
                    )
                elif len(pulls) >= 2 and "get_repeated_pull_analysis" not in executed:
                    tool = (
                        "get_repeated_pull_analysis",
                        {"pull_ids": [p["entity_id"] for p in pulls[:3]]},
                    )
                if tool:
                    return ModelTurn(
                        tool_calls=[
                            ToolRequest(
                                call_id=f"specialist-{specialist.value}-{len(executed)}",
                                name=tool[0],
                                arguments=tool[1] | {"vehicle_id": str(scope.vehicle_id)},
                            )
                        ],
                        usage=Usage(
                            input_tokens=0, output_tokens=0, total_tokens=0, cached_input_tokens=0
                        ),
                    )
        claims: list[Claim] = []
        sources = [
            e
            for e in request.evidence
            if e["source_tool"]
            in {
                "get_session_summary",
                "get_repeated_pull_analysis",
                "get_session_capabilities",
                "list_session_events",
            }
        ]
        for source in sources:
            selected = []
            for fact in source["facts"]:
                path = fact["path"].casefold()
                numeric = type(fact["value"]) in {int, float}
                keep = False
                if specialist is Specialist.DATA_QUALITY:
                    keep = source["source_tool"] == "get_session_capabilities" and (
                        (numeric and any(key in path for key in ("actual_hz", "missing_ratio")))
                        or (path.endswith("/signal") and isinstance(fact["value"], str))
                    )
                elif specialist is Specialist.PERFORMANCE:
                    keep = numeric and any(
                        key in path for key in ("acceleration", "duration", "repeatability")
                    )
                elif specialist is Specialist.THERMAL:
                    keep = numeric and any(key in path for key in ("iat", "temperature", "thermal"))
                    keep = keep or (
                        path == "/event_type"
                        and fact["value"]
                        in {
                            "iat_rise",
                            "intake_temperature_high",
                            "oil_temperature_high",
                            "coolant_temperature_high",
                        }
                    )
                elif specialist is Specialist.FUEL_AIR_BOOST:
                    keep = numeric and any(
                        key in path for key in ("boost", "fuel", "throttle", "lambda")
                    )
                    keep = keep or (
                        path == "/event_type"
                        and fact["value"]
                        in {
                            "boost_drop",
                            "boost_overshoot",
                            "fuel_pressure_drop",
                            "unexpected_throttle_closure",
                        }
                    )
                if keep:
                    selected.append(fact)
            if selected:
                claims.append(
                    Claim(
                        classification=Classification.OBSERVATION,
                        template="recorded_fact",
                        evidence_ids=[UUID(source["id"])],
                        bindings=[
                            Binding(evidence_id=UUID(source["id"]), **f) for f in selected[:8]
                        ],
                    )
                )
            if len(claims) >= 6:
                break
        missing = not claims
        if missing:
            claims.append(
                Claim(
                    classification=Classification.INSUFFICIENT_EVIDENCE,
                    template="insufficient_evidence",
                    evidence_ids=[],
                    bindings=[],
                )
            )
        return ModelTurn(
            draft=Draft(
                confidence="low" if missing else "moderate",
                claims=claims,
                missing_evidence=[
                    "data_quality"
                    if specialist is Specialist.DATA_QUALITY
                    else "signal_or_measurement"
                ]
                if missing
                else [],
            ),
            usage=Usage(input_tokens=0, output_tokens=0, total_tokens=0, cached_input_tokens=0),
        )


class ForgedCitationProvider:
    """Test-only provider that first cites an evidence UUID from another run."""

    def __init__(self) -> None:
        self.delegate = DeterministicProvider()
        self.injected = False

    async def route(self, request: RoutingInput) -> RoutingProposal:
        return await self.delegate.route(request)

    async def turn(self, request: ModelInput) -> ModelTurn:
        if not self.injected and request.specialist is None:
            self.injected = True
            foreign_evidence_id = UUID("00000000-0000-0000-0000-000000000001")
            return ModelTurn(
                draft=Draft(
                    confidence="high",
                    claims=[
                        Claim(
                            classification=Classification.OBSERVATION,
                            template="recorded_fact",
                            evidence_ids=[foreign_evidence_id],
                            bindings=[
                                Binding(
                                    evidence_id=foreign_evidence_id,
                                    path="/id",
                                    value="00000000-0000-0000-0000-000000000001",
                                )
                            ],
                        )
                    ],
                    missing_evidence=[],
                ),
                usage=Usage(input_tokens=0, output_tokens=0, total_tokens=0, cached_input_tokens=0),
            )
        if request.correction is not None:
            return ModelTurn(
                draft=Draft(
                    confidence="low",
                    claims=[
                        Claim(
                            classification=Classification.INSUFFICIENT_EVIDENCE,
                            template="insufficient_evidence",
                            evidence_ids=[],
                            bindings=[],
                        )
                    ],
                    missing_evidence=["signal_or_measurement"],
                ),
                usage=Usage(input_tokens=0, output_tokens=0, total_tokens=0, cached_input_tokens=0),
            )
        return await self.delegate.turn(request)

    async def specialist_turn(self, request: ModelInput) -> ModelTurn:
        return await self.delegate.specialist_turn(request)

    async def propose(self, request: InvestigationInput) -> InvestigationProposal:
        return await self.delegate.propose(request)

    async def close(self) -> None:
        await self.delegate.close()


class ConflictingUnitProvider:
    """Test-only provider that submits a source value with a forged unit once."""

    def __init__(self) -> None:
        self.delegate = DeterministicProvider()
        self.injected = False

    async def route(self, request: RoutingInput) -> RoutingProposal:
        return await self.delegate.route(request)

    async def turn(self, request: ModelInput) -> ModelTurn:
        if request.correction is not None and self.injected:
            return ModelTurn(
                draft=Draft(
                    confidence="low",
                    claims=[
                        Claim(
                            classification=Classification.INSUFFICIENT_EVIDENCE,
                            template="insufficient_evidence",
                            evidence_ids=[],
                            bindings=[],
                        )
                    ],
                    missing_evidence=["signal_or_measurement"],
                ),
                usage=Usage(input_tokens=0, output_tokens=0, total_tokens=0, cached_input_tokens=0),
            )
        if not self.injected:
            for source in request.evidence:
                for fact in source.get("facts", []):
                    unit = fact.get("unit")
                    value = fact.get("value")
                    if unit is None or type(value) not in {int, float}:
                        continue
                    self.injected = True
                    source_id = UUID(str(source["id"]))
                    forged_unit = "bar" if unit != "bar" else "K"
                    return ModelTurn(
                        draft=Draft(
                            confidence="high",
                            claims=[
                                Claim(
                                    classification=Classification.OBSERVATION,
                                    template="recorded_fact",
                                    evidence_ids=[source_id],
                                    bindings=[
                                        Binding(
                                            evidence_id=source_id,
                                            path=str(fact["path"]),
                                            value=value,
                                            unit=forged_unit,
                                        )
                                    ],
                                )
                            ],
                            missing_evidence=[],
                        ),
                        usage=Usage(
                            input_tokens=0,
                            output_tokens=0,
                            total_tokens=0,
                            cached_input_tokens=0,
                        ),
                    )
        return await self.delegate.turn(request)

    async def specialist_turn(self, request: ModelInput) -> ModelTurn:
        return await self.delegate.specialist_turn(request)

    async def propose(self, request: InvestigationInput) -> InvestigationProposal:
        return await self.delegate.propose(request)

    async def close(self) -> None:
        await self.delegate.close()


class WaitAfterToolProvider:
    """Test-only provider that blocks after its first tool request until cancelled."""

    def __init__(self) -> None:
        self.delegate = DeterministicProvider()
        self.block_after_tool = False

    async def route(self, request: RoutingInput) -> RoutingProposal:
        return await self.delegate.route(request)

    async def _wait_if_blocked(self) -> None:
        if self.block_after_tool:
            await asyncio.Event().wait()

    async def turn(self, request: ModelInput) -> ModelTurn:
        await self._wait_if_blocked()
        turn = await self.delegate.turn(request)
        self.block_after_tool = bool(turn.tool_calls)
        return turn

    async def specialist_turn(self, request: ModelInput) -> ModelTurn:
        await self._wait_if_blocked()
        turn = await self.delegate.specialist_turn(request)
        self.block_after_tool = bool(turn.tool_calls)
        return turn

    async def propose(self, request: InvestigationInput) -> InvestigationProposal:
        return await self.delegate.propose(request)

    async def close(self) -> None:
        await self.delegate.close()


class RetryOnceProvider:
    """Test provider that returns a bounded transient error sequence, then recovers."""

    def __init__(self, error_categories: tuple[str, ...] = ("provider_unavailable",)) -> None:
        allowed = {"provider_rate_limit", "provider_unavailable"}
        if not error_categories or set(error_categories) - allowed:
            raise ValueError("Unsupported transient provider error sequence")
        self.delegate = DeterministicProvider()
        self.turn_count = 0
        self.error_categories = error_categories

    async def route(self, request: RoutingInput) -> RoutingProposal:
        return await self.delegate.route(request)

    async def turn(self, request: ModelInput) -> ModelTurn:
        self.turn_count += 1
        if self.turn_count <= len(self.error_categories):
            raise AgentError(self.error_categories[self.turn_count - 1])
        return await self.delegate.turn(request)

    async def specialist_turn(self, request: ModelInput) -> ModelTurn:
        return await self.delegate.specialist_turn(request)

    async def propose(self, request: InvestigationInput) -> InvestigationProposal:
        return await self.delegate.propose(request)

    async def close(self) -> None:
        await self.delegate.close()


class ProviderTimeoutProbe:
    """Test provider that blocks until the configured model timeout cancels it."""

    def __init__(self) -> None:
        self.delegate = DeterministicProvider()

    async def route(self, request: RoutingInput) -> RoutingProposal:
        return await self.delegate.route(request)

    async def turn(self, request: ModelInput) -> ModelTurn:
        await asyncio.Event().wait()
        return await self.delegate.turn(request)

    async def specialist_turn(self, request: ModelInput) -> ModelTurn:
        await asyncio.Event().wait()
        return await self.delegate.specialist_turn(request)

    async def propose(self, request: InvestigationInput) -> InvestigationProposal:
        return await self.delegate.propose(request)

    async def close(self) -> None:
        await self.delegate.close()


class SpecialistTimeoutProbe:
    """Test provider that times out one thermal specialist and leaves siblings runnable."""

    def __init__(self) -> None:
        self.delegate = DeterministicProvider()
        self.timed_out = False

    async def route(self, request: RoutingInput) -> RoutingProposal:
        return await self.delegate.route(request)

    async def turn(self, request: ModelInput) -> ModelTurn:
        if (
            request.specialist is not None
            and request.specialist.specialist is Specialist.THERMAL
            and not self.timed_out
        ):
            self.timed_out = True
            await asyncio.Event().wait()
        return await self.delegate.turn(request)

    async def propose(self, request: InvestigationInput) -> InvestigationProposal:
        return await self.delegate.propose(request)

    async def close(self) -> None:
        await self.delegate.close()


class ProviderCanaryBoundaryProbe:
    """Test-only guard that fails if a secret canary enters any provider request."""

    def __init__(self, canary: str) -> None:
        self.canary = canary
        self.delegate = DeterministicProvider()

    def _check(self, request: object) -> None:
        if self.canary in repr(request):
            raise AgentError("provider_invalid_response")

    async def route(self, request: RoutingInput) -> RoutingProposal:
        self._check(request)
        return await self.delegate.route(request)

    async def turn(self, request: ModelInput) -> ModelTurn:
        self._check(request)
        return await self.delegate.turn(request)

    async def specialist_turn(self, request: ModelInput) -> ModelTurn:
        self._check(request)
        return await self.delegate.specialist_turn(request)

    async def propose(self, request: InvestigationInput) -> InvestigationProposal:
        self._check(request)
        return await self.delegate.propose(request)

    async def close(self) -> None:
        await self.delegate.close()
