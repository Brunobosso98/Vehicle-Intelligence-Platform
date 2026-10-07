import math
from uuid import UUID

from vehicle_platform.agents.evidence import EvidenceRegistry
from vehicle_platform.agents.provider import AgentError
from vehicle_platform.agents.schemas import Answer, Classification, Draft, Finding, VehicleContext

LABELS = {
    "id": "Registro",
    "started_at": "Início da sessão",
    "configuration_id": "Configuração da sessão",
    "event_type": "Evento detectado",
    "start_iat": "IAT inicial",
    "end_iat": "IAT final",
    "iat_delta": "Variação da IAT",
    "median_start_iat_increase": "Aumento mediano da IAT entre puxadas",
}


def render_binding(path: str, value: object, unit: str | None) -> str:
    key = path.rsplit("/", 1)[-1]
    label = LABELS.get(key, key.replace("_", " "))
    if "/metric_deltas/" in path:
        metric = path.split("/metric_deltas/", 1)[1].split("/", 1)[0]
        label = f"{metric.upper()} — {label}"
    display = "não disponível" if value is None else str(value)
    return f"{label}: {display}" + (f" {unit}" if unit and value is not None else "")


def validate(draft: Draft, registry: EvidenceRegistry, context: VehicleContext) -> Answer:
    findings = []
    warnings = list(context.warnings)
    for claim in draft.claims:
        cited = []
        for identifier in claim.evidence_ids:
            item = registry.items.get(identifier)
            if not item or item.run_id != registry.run_id or item.vehicle_id != context.vehicle_id:
                raise AgentError("unknown_evidence")
            cited.append(item)
        for binding in claim.bindings:
            if binding.evidence_id not in claim.evidence_ids:
                raise AgentError("unsupported_claim")
            source = registry.items[binding.evidence_id]
            matches = [f for f in source.facts if f.path == binding.path]
            if len(matches) != 1 or matches[0].unit != binding.unit:
                raise AgentError("unsupported_claim")
            expected, actual = matches[0].value, binding.value
            if (
                isinstance(expected, (int, float))
                and not isinstance(expected, bool)
                and isinstance(actual, (int, float))
                and not isinstance(actual, bool)
            ):
                if not math.isclose(float(expected), float(actual), rel_tol=1e-6, abs_tol=1e-6):
                    raise AgentError("unsupported_numeric_claim")
            elif type(expected) is not type(actual) or expected != actual:
                raise AgentError("unsupported_claim")
        if claim.template in {"insufficient_evidence", "unsafe_operation_refused"}:
            if (
                claim.classification
                not in {Classification.INSUFFICIENT_EVIDENCE, Classification.UNKNOWN}
                or claim.bindings
            ):
                raise AgentError("unsupported_classification")
            statement = (
                "Recuso executar controle do veículo, codificação, flash ou escrita na ECU. "
                "Este agente permite apenas observação e análise das evidências registradas."
                if claim.template == "unsafe_operation_refused"
                else "As evidências disponíveis são insuficientes para determinar a causa mecânica "
                "ou responder à questão com segurança."
            )
        elif claim.template == "recorded_fact":
            if claim.classification != Classification.OBSERVATION or not claim.bindings:
                raise AgentError("unsupported_classification")
            statement = "; ".join(render_binding(b.path, b.value, b.unit) for b in claim.bindings)
        elif claim.template == "temporal_association":
            configuration_sources = {
                e.entity_id
                for e in cited
                if e.source_tool in {"get_vehicle_configuration", "list_vehicle_configurations"}
            }
            compared = [e for e in cited if e.source_tool == "compare_configurations"]
            selected_pulls = {
                str(identifier)
                for e in compared
                for identifier in e.provenance.get("selection", {}).get("pull_ids", [])
            }
            selected_sources = {
                str(e.entity_id): e
                for e in registry.items.values()
                if e.source_tool in {"get_pull", "list_session_pulls"}
                and str(e.entity_id) in selected_pulls
            }
            selected_configurations = {e.configuration_id for e in selected_sources.values()}
            valid_sessions = [s for s in context.sessions if s.get("temporal_configuration_valid")]
            valid_source_contexts = {
                (str(s["id"]), str(s["configuration_id"])) for s in valid_sessions
            }
            represented = {
                UUID(str(s["configuration_id"]))
                for s in valid_sessions
                if s.get("configuration_id")
            }
            if (
                claim.classification != Classification.ASSOCIATION
                or not compared
                or len(configuration_sources & represented) < 2
                or len(selected_sources) != len(selected_pulls)
                or len(selected_configurations) != 2
                or any(
                    (str(e.session_id), str(e.configuration_id)) not in valid_source_contexts
                    for e in selected_sources.values()
                )
                or not selected_configurations <= configuration_sources & represented
                or not claim.bindings
                or not any(
                    b.evidence_id in {e.id for e in compared} and type(b.value) in {int, float}
                    for b in claim.bindings
                )
                or any(e.warnings or e.truncated for e in compared)
                or any(e.warnings or e.truncated for e in selected_sources.values())
                or any(
                    not any(
                        f.path == "/result/sufficiency" and f.value == "sufficient" for f in e.facts
                    )
                    for e in compared
                )
            ):
                raise AgentError("unsupported_association")
            statement = (
                "Mudança medida entre configurações: "
                + "; ".join(render_binding(b.path, b.value, b.unit) for b in claim.bindings)
                + ". Associação temporal; os dados não provam causalidade mecânica."
            )
        else:
            # A fixed, explicitly uncertain thermal interpretation needs both measured domains.
            paths = [b.path.lower() for b in claim.bindings]
            if (
                claim.classification != Classification.HYPOTHESIS
                or not any("iat" in p or "temperature" in p for p in paths)
                or not any("acceleration" in p or "duration" in p for p in paths)
                or not cited
                or any(e.warnings or e.truncated for e in cited)
                or any(type(b.value) not in {int, float} for b in claim.bindings)
            ):
                raise AgentError("unsupported_hypothesis")
            statement = (
                "Uma influência térmica é compatível com essas medições, mas permanece hipótese; "
                "a causa mecânica não foi estabelecida."
            )
        for source in cited:
            warnings.extend(source.warnings)
            if source.truncated:
                warnings.append("bounded_evidence_is_incomplete")
        findings.append(Finding(**claim.model_dump(), statement=statement))
    if not findings:
        raise AgentError("empty_answer")
    insufficient = any(
        f.classification in {Classification.INSUFFICIENT_EVIDENCE, Classification.UNKNOWN}
        for f in findings
    )
    warnings = list(dict.fromkeys(warnings))[:32]
    return Answer(
        answer="\n".join(f.statement for f in findings),
        confidence="low" if insufficient or warnings else draft.confidence,
        findings=findings,
        evidence=list(registry.items.values()),
        context=context,
        uncertainties=[
            "Causalidade e diagnóstico mecânico não demonstrados pelos dados disponíveis."
        ],
        limitations=warnings,
        missing_evidence=list(draft.missing_evidence),
    )
