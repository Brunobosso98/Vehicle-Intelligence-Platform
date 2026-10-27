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


def prediction_anomaly_pair_requested(question: str) -> bool:
    """Recognize an explicit request to compare recorded predictions and anomalies."""
    q = question.casefold()
    return any(word in q for word in ("prediction", "previsão", "predição")) and any(
        word in q
        for word in (
            "anomaly",
            "anomalies",
            "anomalia",
            "anomalias",
            "outlier",
            "outliers",
            "desvio estatístico",
            "desvios estatísticos",
        )
    )


def prediction_request_intent(question: str) -> Intent | None:
    """Return only explicit requests about an already recorded prediction or anomaly."""
    q = question.casefold()
    methodology = re.search(
        r"\b(methodology|method|algorithm|calibrat|how does .* work|como funciona|"
        r"significado do score|meaning of (the )?score|how is .* detected)\b",
        q,
    )
    if methodology:
        return None
    if re.search(r"\b(anomal(?:y|ies)|outlier|anomalia|anomalias|desvio estatístico)\b", q):
        if re.search(
            r"\b(was|were|is|are|has|have|any|there|teve|tem|existiu|existe|houve|registrad|"
            r"detectad|observad|found|seen|present|outlier|compare|comparar)\b",
            q,
        ):
            return Intent.ANOMALY
    recorded_prediction = (
        re.search(
            r"\b(prediction|previsão|predição)\b.{0,60}\b(recorded|registered|existing|previous|last|result|score|registrada|registrado|anterior|resultado|pontuação)\b",
            q,
        )
        or re.search(
            r"\b(last|previous|existing|registered|recent|última|último|anterior|registrad[oa])\b"
            r".{0,40}\b(prediction|previsão|predição)\b",
            q,
        )
        or re.search(
            r"\b(what|qual|quais)\b.{0,40}\b(prediction|previsão|predição)\b.{0,30}\b(was|is|foi|está|registrad|previst)\b",
            q,
        )
        or re.search(
            r"\b(what did (the )?model predict|o que (o )?modelo previu|qual foi a previsão|"
            r"qual previsão foi registrada)\b",
            q,
        )
    )
    next_pull_expectation = re.search(
        r"\b(next compatible pull|next pull|próxima puxada|próximo pull)\b.{0,60}"
        r"\b(expect|predict|classif|expectativa|previst|classifica)\b",
        q,
    )
    return Intent.PREDICTION if recorded_prediction or next_pull_expectation else None


def risk_sensitive_question(question: str) -> bool:
    """Identify safety clearance, component-failure and repair-choice requests."""
    q = question.casefold()
    patterns = (
        r"\b(can i|may i|should i|is it safe to|keep accelerating|continue accelerating|"
        r"continue driving|safe to drive)\b",
        r"\b(will|could|is .* going to)\b.{0,60}\b(fail|break|blow|explode)\b",
        r"\b(what part|which part|what component)\b.{0,60}\b(replace|change|install)\b",
        r"\b(probability|chance|likelihood)\b.{0,60}\b(fail|failure|break|component)\b",
        r"\b(posso|devo)\b.{0,50}\b(continuar|acelerar|dirigir|rodar)\b",
        r"\b(turbo|motor|peça|componente)\b.{0,60}\b(vai quebrar|vai falhar|quebrou|falhou)\b",
        r"\b(qual|que)\b.{0,50}\b(peça|componente)\b.{0,50}\b(trocar|substituir)\b",
        r"\b(probabilidade|chance|risco)\b.{0,60}\b(falha|quebrar|componente)\b",
    )
    return any(re.search(pattern, q) for pattern in patterns)


def prediction_specialists(question: str, evidence: list[Evidence]) -> tuple[Specialist, ...]:
    q = question.casefold()
    interpretive = re.search(
        r"\b(explain|interpret|analy[sz]e|why|compare|mean|impact|explanation|explique|"
        r"interprete|analise|por que|significa|impacto)\b",
        q,
    )
    if interpretive is None:
        return ()
    selected: set[Specialist] = set()
    if any(word in q for word in ("thermal", "temperature", "heat", "iat", "térmic", "temperat")):
        selected.add(Specialist.THERMAL)
    if any(word in q for word in ("fuel", "hpfp", "boost", "lambda", "combust", "combustível")):
        selected.add(Specialist.FUEL_AIR_BOOST)
    if any(
        word in q for word in ("performance", "torque", "acceleration", "desempenho", "acelera")
    ):
        selected.add(Specialist.PERFORMANCE)
    if not selected:
        for item in evidence:
            if item.source_tool != "get_prediction_evidence":
                continue
            task = next((f.value for f in item.facts if f.path == "/prediction/task"), None)
            family = next((f.value for f in item.facts if f.path == "/prediction/family"), None)
            if (isinstance(task, str) and "THERMAL" in task) or family == "thermal":
                selected.add(Specialist.THERMAL)
            elif (isinstance(task, str) and "FUEL" in task) or family in {"fuel", "boost_air"}:
                selected.add(Specialist.FUEL_AIR_BOOST)
            elif (isinstance(task, str) and "PERFORMANCE" in task) or family == "performance":
                selected.add(Specialist.PERFORMANCE)
    return tuple(item for item in DOMAIN_ORDER if item in selected)


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
    explicit_prediction = prediction_request_intent(question)
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
    channel_alternatives = bool(
        re.search(r"\b(what|which|quais)\b", q)
        and re.search(r"\b(signals?|channels?|sinais|canais)\b", q)
        and re.search(r"\b(collect|capture|record|log|coletar|registrar)\b", q)
        and re.search(r"\b(unavailable|instead|alternatives?|indisponível|alternativas?)\b", q)
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
    elif explicit_prediction is not None:
        intent = explicit_prediction
        selected.update(prediction_specialists(question, evidence))
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
    elif source_capability_query or channel_alternatives:
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
    if collection_request and intent is Intent.FACTUAL:
        hints.append("capture_requires_approval")
    if events & FUEL_EVENTS:
        hints.append("recorded_fuel_air_boost_events")
    if events & THERMAL_EVENTS:
        hints.append("recorded_thermal_events")
    if unreliable:
        hints.append("recorded_quality_warning")
    required = tuple(item for item in DOMAIN_ORDER if item in selected)
    # An unrecognized question needs typed model interpretation, within the finite registry.
    # A prediction request is classified from bounded source facts, so no second
    # provider call is needed just to decide whether the evidence can be read.
    candidates = (
        ()
        if intent in {Intent.PREDICTION, Intent.ANOMALY}
        else (required if intent is not None else DOMAIN_ORDER)
    )
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
