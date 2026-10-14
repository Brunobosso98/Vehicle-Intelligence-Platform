"""Hybrid routing: typed model intent constrained by question and actual evidence families."""

import re
from dataclasses import dataclass

from vehicle_platform.agents.provider import AgentError
from vehicle_platform.agents.schemas import Evidence, VehicleContext
from vehicle_platform.agents.specialists.contracts import (
    Intent,
    RoutingDecision,
    RoutingProposal,
    Specialist,
)

DOMAIN_ORDER = (Specialist.PERFORMANCE, Specialist.THERMAL, Specialist.FUEL_AIR_BOOST)
QUALITY_EVENTS = frozenset({"telemetry_gap", "sensor_dropout", "signal_stuck"})
FUEL_EVENTS = frozenset({"boost_drop", "boost_overshoot", "fuel_pressure_drop"})
THERMAL_EVENTS = frozenset({"iat_rise", "intake_temperature_high", "oil_temperature_high"})


@dataclass(frozen=True)
class RoutingHints:
    intent: Intent | None
    candidates: tuple[Specialist, ...]
    required: tuple[Specialist, ...]
    hints: tuple[str, ...]
    unreliable: bool


def event_types(evidence: list[Evidence]) -> set[str]:
    return {
        str(fact.value)
        for item in evidence
        if item.source_tool in {"list_session_events", "get_event", "list_pull_events"}
        for fact in item.facts
        if fact.path == "/event_type"
    }


def hints_for(question: str, evidence: list[Evidence]) -> RoutingHints:
    q = question.casefold()
    events = event_types(evidence)
    unreliable = bool(events & QUALITY_EVENTS) or any(
        item.source_tool in {"get_session_capabilities", "get_session_summary"}
        and (item.truncated or "source_incomplete" in item.warnings)
        for item in evidence
    )
    hints: list[str] = []
    intent: Intent | None = None
    selected: set[Specialist] = set()
    forced_consensus = (
        re.search(r"\b(repeat|rerun|rerunning|iterate|loop|keep|repita|repetir)\b", q)
        and re.search(r"\b(until|até)\b.*\b(agree|consensus|concordem|consenso)\b", q)
        and re.search(r"\b(agents?|specialists?|agentes?|especialistas?)\b", q)
    )
    reliability_query = re.search(
        r"\b(trust|reliable|reliability|confiar|confiável)\b", q
    ) and re.search(r"\b(data|signals?|sensors?|samples?|telemetry|dados|sinais)\b", q)
    missing_samples = re.search(r"\b(missing|lost|dropped|ausentes|perdidos)\b", q) and re.search(
        r"\b(samples?|packets?|amostras?|pacotes?)\b", q
    )
    abrupt_zero = (
        re.search(r"\b(signals?|sensors?|channels?|sinais|sensores?)\b", q)
        and re.search(r"\b(suddenly|abruptly|unexpectedly|repentinamente)\b", q)
        and re.search(r"\bzero\b", q)
    )
    source_capability_query = re.search(r"\b(source|logger|adapter|device|fonte)\b", q) and (
        re.search(r"\b(capabilities|capability|available|availability)\b", q)
        or re.search(
            r"\b(can|could|does|will)\b.{0,100}\b(source|logger|adapter|device)\b"
            r".{0,100}\b(log|record|capture|support|provide)\b",
            q,
        )
    )
    foreign_vehicle = bool(
        re.search(r"\b(use|read|query|compare|usar|consulte)\b", q)
        and re.search(r"\b(another|other|different|outro)\s+vehicle\b", q)
    )
    telemetry_gaps = bool(re.search(r"\b(telemetry|sampling|sample)\s+gaps?\b", q))
    collection_request = bool(
        re.search(r"\b(collect|collecting|capture|capturing|coletar|coletando)\b", q)
        and re.search(r"\b(automatically|approval|asking|keep|until|automaticamente|até)\b", q)
    )
    if (
        forced_consensus
        or foreign_vehicle
        or re.search(r"\b(flash|coding|write ecu|control brakes|shell|sql)\b", q)
    ):
        intent = Intent.UNSAFE
    elif collection_request:
        # Planning capture is read-only; execution and approval remain unavailable.
        intent = Intent.FACTUAL
    elif any(word in q for word in ("manual", "factory specification", "documentação técnica")):
        intent = Intent.TECHNICAL_DOCUMENTATION
    elif re.search(r"\b(how many|quantos|quantas|number of|count of)\b", q) and not any(
        word in q
        for word in (
            "why",
            "por que",
            "porque",
            "cause",
            "causa",
            "explain",
            "compare",
            "slower",
            "faster",
            "degrad",
            "consistent",
            "affect",
            "trust",
            "reliable",
        )
    ):
        intent = Intent.FACTUAL
    elif (
        any(word in q for word in ("dropout", "data quality", "qualidade", "timestamp anomaly"))
        or re.search(r"\b(signal|sensor)\b.*\bstuck\b", q)
        or (reliability_query or missing_samples or abrupt_zero or telemetry_gaps)
    ):
        intent = Intent.DATA_QUALITY
    elif source_capability_query:
        intent = Intent.FACTUAL
    elif q.startswith(("teve ", "what events", "which events", "show events")):
        intent = Intent.FACTUAL
    else:
        why = any(word in q for word in ("why", "por que", "porque", "cause", "causa"))
        repeated = any(word in q for word in ("repeated", "consecut", "repetid"))
        performance = any(
            word in q
            for word in ("slower", "lento", "performance", "desempenho", "acelera", "acceler")
        )
        thermal = any(
            word in q
            for word in ("heat soak", "iat", "thermal", "térmic", "temperat", "hotter", "coolant")
        )
        performance = (
            performance
            or "torque intervention" in q
            or ("consisten" in q and bool(re.search(r"\b(car|vehicle|pulls?|puxadas?)\b", q)))
        )
        fuel = any(
            word in q for word in ("boost", "fuel", "hpfp", "lambda", "combust", "throttle", "afr")
        )
        pull_noun = r"(?:pulls?|puxadas?)"
        performance_comparison = r"(?:better|worse|faster|slower|quicker|pior(?:es)?|melhor(?:es)?)"
        comparative_pull = bool(
            re.search(rf"\b{pull_noun}\b(?:\W+\w+){{0,3}}\W+{performance_comparison}\b", q)
            or re.search(rf"\b{performance_comparison}\b(?:\W+\w+){{0,2}}\W+{pull_noun}\b", q)
        )
        performance = performance or (
            (any(word in q for word in ("pulls", "puxadas")) or comparative_pull)
            and not thermal
            and not fuel
        )
        comparison = any(word in q for word in ("before", "after", "antes", "depois")) and any(
            word in q for word in ("configur", "modific", "intercooler")
        )
        lookup = bool(re.search(r"\b(how many|quantos|quantas|number of|count of)\b", q))
        interpretation = why or any(
            word in q for word in ("compare", "slower", "faster", "degrad", "consistent", "affect")
        )
        metadata_comparison = (
            "configur" in q
            and any(word in q for word in ("same", "igual", "mesma"))
            and not (performance or thermal or fuel or interpretation)
        )
        overview = bool(re.search(r"^what.*\bknow\b.*\b(car|vehicle)\b", q)) and not (
            performance or thermal or fuel or interpretation
        )
        hypothesis_review = bool(
            re.search(r"\b(hypothesis|hypotheses|hipótese|hipóteses)\b", q)
            and re.search(r"\b(evidence|evidências)\b", q)
            and re.search(r"\b(against|competing|contra|concorrentes)\b", q)
        )
        if (lookup and not interpretation) or metadata_comparison or overview:
            intent = Intent.FACTUAL
        elif hypothesis_review:
            intent = Intent.MULTI_MECHANISM
            selected.add(Specialist.PERFORMANCE)
            if events & THERMAL_EVENTS:
                selected.add(Specialist.THERMAL)
            if events & FUEL_EVENTS:
                selected.add(Specialist.FUEL_AIR_BOOST)
        elif comparison:
            intent = Intent.CONFIGURATION
            selected.update(
                [Specialist.FUEL_AIR_BOOST]
                if fuel
                else [Specialist.THERMAL]
                if thermal
                else [Specialist.PERFORMANCE]
            )
        elif (
            performance
            and (thermal or fuel)
            and any(
                word in q
                for word in (
                    " and ",
                    " but ",
                    "without",
                    " as ",
                    "versus",
                    "distinguish",
                    "while",
                    "same time",
                    "correlat",
                    "association",
                    "relationship",
                    "compare",
                    "affect",
                    " e ",
                    " mas ",
                    "sem ",
                    "distinguir",
                )
            )
        ) or (
            thermal and fuel and any(word in q for word in ("explanation", "hypothes", "explica"))
        ):
            # Relating measured outcomes or competing mechanisms needs each named domain.
            intent = Intent.MULTI_MECHANISM
            selected.add(Specialist.PERFORMANCE)
            if thermal or (performance and why):
                selected.add(Specialist.THERMAL)
            if fuel:
                selected.add(Specialist.FUEL_AIR_BOOST)
        elif (
            why
            and (thermal or fuel)
            and not any(word in q for word in ("why", "por que", "porque"))
        ):
            # A question about a named mechanism proving causation belongs to that
            # mechanism; a slower outcome alone does not require another analyzer.
            intent = Intent.THERMAL if thermal and not fuel else Intent.FUEL_AIR_BOOST
            if thermal:
                selected.add(Specialist.THERMAL)
            if fuel:
                selected.add(Specialist.FUEL_AIR_BOOST)
        elif performance and why:
            intent = Intent.REPEATED_DEGRADATION if repeated else Intent.MULTI_MECHANISM
            selected.update({Specialist.PERFORMANCE, Specialist.THERMAL})
            if fuel or events & FUEL_EVENTS:
                selected.add(Specialist.FUEL_AIR_BOOST)
                intent = Intent.MULTI_MECHANISM
        elif fuel:
            intent = Intent.FUEL_AIR_BOOST
            selected.add(Specialist.FUEL_AIR_BOOST)
        elif performance:
            intent = Intent.PERFORMANCE
            selected.add(Specialist.PERFORMANCE)
        elif thermal:
            intent = Intent.THERMAL
            selected.add(Specialist.THERMAL)
        elif any(word in q for word in ("last session", "última sessão", "installed", "instalada")):
            intent = Intent.FACTUAL
    if intent:
        hints.append(f"question_intent:{intent.value}")
    if events & FUEL_EVENTS:
        hints.append("recorded_fuel_air_boost_events")
    if events & THERMAL_EVENTS:
        hints.append("recorded_thermal_events")
    if unreliable:
        hints.append("recorded_quality_warning")
    required = tuple(item for item in DOMAIN_ORDER if item in selected)
    # An unrecognized question needs typed model interpretation, within the finite registry.
    candidates = required if intent is not None else DOMAIN_ORDER
    return RoutingHints(intent, candidates, required, tuple(hints), unreliable)


def decide(
    hints: RoutingHints, proposal: RoutingProposal, context: VehicleContext, cap: int = 3
) -> RoutingDecision:
    if not 0 <= cap <= 3 or len(set(proposal.specialists)) != len(proposal.specialists):
        raise AgentError("invalid_supervisor_routing")
    if any(s is Specialist.DATA_QUALITY or s not in hints.candidates for s in proposal.specialists):
        raise AgentError("invalid_supervisor_routing")
    intent = hints.intent or proposal.intent
    selected_set = set(hints.required) | set(proposal.specialists)
    if intent in {
        Intent.FACTUAL,
        Intent.TECHNICAL_DOCUMENTATION,
        Intent.UNSAFE,
        Intent.DATA_QUALITY,
    }:
        selected_set.clear()
    selected = [s for s in DOMAIN_ORDER if s in selected_set]
    if len(selected) > cap:
        raise AgentError("specialist_budget_exhausted")
    gate = bool(selected or intent is Intent.DATA_QUALITY or hints.unreliable)
    # Factual/documentation paths do not interpret telemetry, even if old telemetry is poor.
    if intent in {Intent.FACTUAL, Intent.TECHNICAL_DOCUMENTATION, Intent.UNSAFE}:
        gate = False
    if not context.sessions and selected:
        gate = True  # A quality gate must explicitly report absent telemetry.
    all_considered = list(Specialist)
    return RoutingDecision(
        intent=intent,
        considered=all_considered,
        selected=selected,
        skipped=[
            s
            for s in all_considered
            if s not in selected and not (gate and s is Specialist.DATA_QUALITY)
        ],
        data_quality_gate=gate,
        hints=list(hints.hints),
        reason="Scoped intent and recorded evidence determine the minimum specialist set.",
    )
