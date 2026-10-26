import math
from uuid import UUID

from vehicle_platform.agents.evidence import EvidenceRegistry
from vehicle_platform.agents.provider import AgentError
from vehicle_platform.agents.schemas import (
    Answer,
    Binding,
    Claim,
    Classification,
    Draft,
    Evidence,
    Fact,
    Finding,
    VehicleContext,
)
from vehicle_platform.agents.specialists.routing import prediction_anomaly_pair_requested

PREDICTION_TASKS = {
    "NEXT_PULL_THERMAL_DEGRADATION": (
        "IAT inicial da próxima puxada compatível pelo menos 3 K acima da puxada de entrada"
    ),
    "NEXT_PULL_PERFORMANCE_DEGRADATION": (
        "intervalo de 3.500–4.500 RPM pelo menos 8% mais lento por 1.000 RPM"
    ),
    "NEXT_PULL_FUEL_DEVIATION": (
        "pressão mínima de combustível da próxima puxada em até 88% da média compatível anterior"
    ),
}
ANOMALY_FAMILIES = frozenset({"thermal", "boost_air", "performance", "fuel"})
ACCEPTED_INTEGRITY = frozenset({"VERIFIED", "VERIFIED_SNAPSHOT_ARTIFACT_UNAVAILABLE"})


def _prediction_fact(source: Evidence, path: str) -> Fact:
    matches = [fact for fact in source.facts if fact.path == path]
    if len(matches) != 1:
        raise AgentError("unsupported_prediction_claim")
    return matches[0]


def _prediction_bindings(source: Evidence, paths: tuple[str, ...]) -> list[Binding]:
    return [
        Binding(
            evidence_id=source.id,
            path=path,
            value=_prediction_fact(source, path).value,
            unit=_prediction_fact(source, path).unit,
        )
        for path in paths
    ]


def _anomaly_source_measurement(source: Evidence, family: str) -> Fact | None:
    """Return a bounded, unit-bearing feature from the same 9E projection."""
    prefixes = {
        "thermal": "thermal.",
        "boost_air": "boost_air.",
        "performance": "performance.",
        "fuel": "fuel.",
    }
    prefix = prefixes.get(family)
    if prefix is None:
        return None
    candidates = [
        fact
        for fact in source.facts
        if fact.path.startswith("/prediction/features/")
        and fact.path.removeprefix("/prediction/features/").startswith(prefix)
        and fact.unit is not None
        and isinstance(fact.value, (int, float))
        and not isinstance(fact.value, bool)
        and math.isfinite(fact.value)
    ]
    return min(candidates, key=lambda fact: fact.path) if candidates else None


def prediction_answer(
    registry: EvidenceRegistry,
    context: VehicleContext,
    intent: str,
    *,
    error: str | None = None,
    forced_gap: str | None = None,
    question: str = "",
) -> Answer:
    """Render an explicit prediction request without provider-authored prose."""
    sources = [item for item in registry.ordered() if item.source_tool == "get_prediction_evidence"]
    compare_pair = prediction_anomaly_pair_requested(question)
    if compare_pair and error is None and forced_gap is None:
        next_pull = [
            item
            for item in sources
            if _prediction_fact(item, "/prediction/horizon").value == "NEXT_PULL"
        ]
        offline = [
            item
            for item in sources
            if _prediction_fact(item, "/prediction/horizon").value == "AFTER_PULL_OFFLINE"
        ]
        pair = [next_pull[0], offline[0]] if len(next_pull) == len(offline) == 1 else []
        if pair:
            claim = Claim(
                classification=Classification.DESCRIPTIVE_ASSOCIATION,
                template="statistical_association",
                bindings=[],
                evidence_ids=[item.id for item in pair if item is not None],
            )
            try:
                return validate(
                    Draft(confidence="moderate", claims=[claim], missing_evidence=[]),
                    registry,
                    context,
                )
            except AgentError:
                forced_gap = "shared_source_lineage_not_verified"
        else:
            forced_gap = "prediction_anomaly_pair_unavailable"
    expected_horizon = "NEXT_PULL" if intent == "prediction" else "AFTER_PULL_OFFLINE"
    selected = [
        item
        for item in sources
        if _prediction_fact(item, "/prediction/horizon").value == expected_horizon
    ]
    blocked = error is not None or forced_gap is not None or not selected
    real_vehicle = any(
        token in question.casefold()
        for token in ("my real car", "my actual car", "meu carro real", "veículo real")
    )
    if real_vehicle and any(
        _prediction_fact(item, "/prediction/source_role").value != "real_vehicle"
        for item in selected
    ):
        blocked = True
        forced_gap = "source_role_not_real_vehicle"
    eligible: list[Evidence] = []
    for source in selected:
        integrity = _prediction_fact(source, "/prediction/integrity").value
        completeness = _prediction_fact(source, "/prediction/completeness").value
        quality = _prediction_fact(source, "/prediction/quality_class").value
        status = _prediction_fact(source, "/prediction/status").value
        score = _prediction_fact(source, "/prediction/score").value
        threshold = _prediction_fact(source, "/prediction/threshold").value
        if (
            integrity not in ACCEPTED_INTEGRITY
            or completeness != "COMPLETE"
            or quality != "high"
            or status != "READY_SCORE"
            or type(score) not in {int, float}
            or type(threshold) not in {int, float}
        ):
            blocked = True
        else:
            eligible.append(source)
    if forced_gap or blocked or not eligible:
        cited = selected[:4]
        reason = forced_gap or error or "prediction_evidence_incomplete_or_abstained"
        claim = Claim(
            classification=Classification.DATA_GAP,
            template="prediction_insufficient",
            bindings=[],
            evidence_ids=[item.id for item in cited],
        )
        answer = validate(
            Draft(
                confidence="low",
                claims=[claim],
                missing_evidence=["signal_or_measurement"],
            ),
            registry,
            context,
        )
        answer.limitations = list(
            dict.fromkeys(
                [
                    f"prediction_data_gap:{reason[:80]}",
                    "Uma nova coleta exige aprovação explícita; nenhuma aquisição foi iniciada.",
                    *answer.limitations,
                ]
            )
        )[:32]
        return answer

    claims: list[Claim] = []
    source_roles: set[str] = set()
    for source in eligible:
        source_role = _prediction_fact(source, "/prediction/source_role").value
        if not isinstance(source_role, str):
            return prediction_answer(
                registry, context, intent, forced_gap="unsupported_source_role", question=question
            )
        source_roles.add(source_role)
        if intent == "prediction":
            task = _prediction_fact(source, "/prediction/task").value
            decision = _prediction_fact(source, "/prediction/decision").value
            if task not in PREDICTION_TASKS or type(decision) is not bool:
                return prediction_answer(
                    registry,
                    context,
                    intent,
                    forced_gap="unsupported_task_or_decision",
                    question=question,
                )
            prediction_paths = (
                "/prediction/horizon",
                "/prediction/task",
                "/prediction/score",
                "/prediction/threshold",
                "/prediction/decision",
                "/prediction/model_version",
                "/prediction/source_role",
                "/prediction/effective_cutoff",
            )
            claims.append(
                Claim(
                    classification=Classification.MODEL_CLASSIFICATION,
                    template="prediction_result",
                    bindings=_prediction_bindings(source, prediction_paths),
                    evidence_ids=[source.id],
                )
            )
        else:
            family = _prediction_fact(source, "/prediction/family").value
            decision = _prediction_fact(source, "/prediction/decision").value
            if (
                not isinstance(family, str)
                or family not in ANOMALY_FAMILIES
                or decision not in {"ANOMALOUS", "INLIER"}
            ):
                return prediction_answer(
                    registry,
                    context,
                    intent,
                    forced_gap="unsupported_family_or_decision",
                    question=question,
                )
            anomaly_paths: tuple[str, ...] = (
                "/prediction/horizon",
                "/prediction/family",
                "/prediction/score",
                "/prediction/threshold",
                "/prediction/detector_version",
                "/prediction/detector_method",
                "/prediction/effective_cutoff",
            )
            source_measurement = _anomaly_source_measurement(source, family)
            if decision == "ANOMALOUS":
                if source_measurement is None:
                    raise AgentError("unsupported_prediction_claim")
                anomaly_paths = (*anomaly_paths, source_measurement.path)
            claims.append(
                Claim(
                    classification=(
                        Classification.STATISTICAL_OUTLIER
                        if decision == "ANOMALOUS"
                        else Classification.MODEL_CLASSIFICATION
                    ),
                    template="anomaly_result",
                    bindings=_prediction_bindings(source, anomaly_paths),
                    evidence_ids=[source.id],
                )
            )
    answer = validate(
        Draft(confidence="low", claims=claims, missing_evidence=[]), registry, context
    )
    answer.limitations = list(
        dict.fromkeys(
            [
                *(f"source_role:{role}" for role in sorted(source_roles)),
                *(
                    ["O artefato histórico não está disponível para reprodução atual."]
                    if any(
                        _prediction_fact(source, "/prediction/integrity").value
                        == "VERIFIED_SNAPSHOT_ARTIFACT_UNAVAILABLE"
                        for source in eligible
                    )
                    else []
                ),
                *answer.limitations,
            ]
        )
    )[:32]
    return answer


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
        elif claim.template == "prediction_insufficient":
            if claim.classification != Classification.DATA_GAP or claim.bindings:
                raise AgentError("unsupported_classification")
            if any(source.source_tool != "get_prediction_evidence" for source in cited):
                raise AgentError("unsupported_prediction_claim")
            status_values = [
                _prediction_fact(source, "/prediction/status").value for source in cited
            ]
            reason_values = [
                _prediction_fact(source, "/prediction/reason_code").value for source in cited
            ]
            reasons = [
                str(value)
                for value in [*status_values, *reason_values]
                if isinstance(value, str)
                and value.isascii()
                and value.replace("_", "").replace("-", "").isalnum()
            ][:4]
            statement = (
                "Não há resultado preditivo elegível para esta afirmação. "
                + ("Estado registrado: " + ", ".join(reasons) + ". " if reasons else "")
                + "Os dados disponíveis não estabelecem uma falha mecânica."
            )
        elif claim.template == "prediction_result":
            if (
                claim.classification != Classification.MODEL_CLASSIFICATION
                or len(cited) != 1
                or cited[0].source_tool != "get_prediction_evidence"
            ):
                raise AgentError("unsupported_classification")
            source = cited[0]
            expected_paths = {
                "/prediction/horizon",
                "/prediction/task",
                "/prediction/score",
                "/prediction/threshold",
                "/prediction/decision",
                "/prediction/model_version",
                "/prediction/source_role",
                "/prediction/effective_cutoff",
            }
            if {binding.path for binding in claim.bindings} != expected_paths:
                raise AgentError("unsupported_prediction_claim")
            values = {path: _prediction_fact(source, path).value for path in expected_paths}
            task_value = values["/prediction/task"]
            score_value = values["/prediction/score"]
            threshold_value = values["/prediction/threshold"]
            if (
                values["/prediction/horizon"] != "NEXT_PULL"
                or not isinstance(task_value, str)
                or task_value not in PREDICTION_TASKS
                or type(values["/prediction/decision"]) is not bool
                or _prediction_fact(source, "/prediction/integrity").value not in ACCEPTED_INTEGRITY
                or _prediction_fact(source, "/prediction/completeness").value != "COMPLETE"
                or _prediction_fact(source, "/prediction/quality_class").value != "high"
                or _prediction_fact(source, "/prediction/status").value != "READY_SCORE"
                or _prediction_fact(source, "/prediction/score_is_probability").value is not False
            ):
                raise AgentError("unsupported_prediction_claim")
            if (
                not isinstance(score_value, (int, float))
                or isinstance(score_value, bool)
                or not isinstance(threshold_value, (int, float))
                or isinstance(threshold_value, bool)
            ):
                raise AgentError("unsupported_prediction_claim")
            if not 0 <= float(score_value) <= 1 or not 0 <= float(threshold_value) <= 1:
                raise AgentError("unsupported_prediction_claim")
            label = PREDICTION_TASKS[task_value]
            outcome = "positiva" if values["/prediction/decision"] else "negativa"
            statement = (
                f"O modelo registrado classificou como {outcome} o rótulo de engenharia "
                f"'{label}' para a próxima puxada compatível (horizonte NEXT_PULL). "
                f"Score de validação de engenharia: {values['/prediction/score']}; "
                f"limiar congelado: {values['/prediction/threshold']}; "
                f"versão do modelo: {values['/prediction/model_version']}; "
                f"papel da fonte: {values['/prediction/source_role']}; "
                f"corte de entrada: {values['/prediction/effective_cutoff']}. "
                "O score não é probabilidade calibrada de falha nem telemetria observada "
                "da próxima puxada."
            )
        elif claim.template == "anomaly_result":
            if len(cited) != 1 or cited[0].source_tool != "get_prediction_evidence":
                raise AgentError("unsupported_classification")
            source = cited[0]
            family = _prediction_fact(source, "/prediction/family").value
            decision = _prediction_fact(source, "/prediction/decision").value
            expected_classification = (
                Classification.STATISTICAL_OUTLIER
                if decision == "ANOMALOUS"
                else Classification.MODEL_CLASSIFICATION
            )
            expected_paths = {
                "/prediction/horizon",
                "/prediction/family",
                "/prediction/score",
                "/prediction/threshold",
                "/prediction/detector_version",
                "/prediction/detector_method",
                "/prediction/effective_cutoff",
            }
            if not isinstance(family, str):
                raise AgentError("unsupported_prediction_claim")
            source_measurement = _anomaly_source_measurement(source, family)
            if decision == "ANOMALOUS" and source_measurement is None:
                raise AgentError("unsupported_prediction_claim")
            if source_measurement is not None and decision == "ANOMALOUS":
                expected_paths.add(source_measurement.path)
            if (
                claim.classification != expected_classification
                or {binding.path for binding in claim.bindings} != expected_paths
                or family not in ANOMALY_FAMILIES
                or decision not in {"ANOMALOUS", "INLIER"}
                or _prediction_fact(source, "/prediction/horizon").value != "AFTER_PULL_OFFLINE"
                or _prediction_fact(source, "/prediction/status").value != "READY_SCORE"
                or _prediction_fact(source, "/prediction/integrity").value not in ACCEPTED_INTEGRITY
                or _prediction_fact(source, "/prediction/completeness").value != "COMPLETE"
                or _prediction_fact(source, "/prediction/quality_class").value != "high"
                or _prediction_fact(source, "/prediction/score_is_probability").value is not False
            ):
                raise AgentError("unsupported_prediction_claim")
            score = _prediction_fact(source, "/prediction/score").value
            threshold = _prediction_fact(source, "/prediction/threshold").value
            method = _prediction_fact(source, "/prediction/detector_method").value
            if (
                type(score) not in {int, float}
                or type(threshold) not in {int, float}
                or not isinstance(method, str)
            ):
                raise AgentError("unsupported_prediction_claim")
            reference_rows = _prediction_fact(source, "/prediction/reference_row_count").value
            reference_sessions = _prediction_fact(
                source, "/prediction/reference_session_count"
            ).value
            reference = (
                f" A referência congelada continha {reference_rows} linhas e "
                f"{reference_sessions} sessões."
                if type(reference_rows) is int and type(reference_sessions) is int
                else " O tamanho da referência não está disponível nesta projeção."
            )
            label = (
                "foi classificada como relativamente incomum"
                if decision == "ANOMALOUS"
                else "não foi classificada como incomum por este detector"
            )
            source_detail = (
                " Característica registrada na fonte 9E: "
                + render_binding(
                    source_measurement.path,
                    source_measurement.value,
                    source_measurement.unit,
                )
                + "."
                if source_measurement is not None
                else ""
            )
            statement = (
                f"A puxada observada {label} pela família {family} no horizonte "
                "AFTER_PULL_OFFLINE. "
                f"Score específico do detector: {score}; limiar: {threshold}; "
                f"método: {method}; versão: "
                f"{_prediction_fact(source, '/prediction/detector_version').value}; "
                f"papel da fonte: {_prediction_fact(source, '/prediction/source_role').value}; "
                f"corte: {_prediction_fact(source, '/prediction/effective_cutoff').value}."
                f"{reference}{source_detail} O score é relativo a esta referência e não é "
                "probabilidade, "
                "severidade de falha ou diagnóstico mecânico."
            )
        elif claim.template == "statistical_association":
            if (
                claim.classification != Classification.DESCRIPTIVE_ASSOCIATION
                or claim.bindings
                or len(cited) != 2
                or any(source.source_tool != "get_prediction_evidence" for source in cited)
            ):
                raise AgentError("unsupported_classification")
            links = {link.run_evidence_id: link for link in registry.prediction_links}
            left, right = (links.get(source.id) for source in cited)
            horizons = {_prediction_fact(source, "/prediction/horizon").value for source in cited}
            if (
                left is None
                or right is None
                or left.source_feature_set_id is None
                or left.source_feature_set_id != right.source_feature_set_id
                or left.source_pull_id != right.source_pull_id
                or left.source_evidence_id == right.source_evidence_id
                or left.receipt_id == right.receipt_id
                or left.source_role != right.source_role
                or horizons != {"NEXT_PULL", "AFTER_PULL_OFFLINE"}
                or any(
                    _prediction_fact(source, "/prediction/integrity").value
                    not in ACCEPTED_INTEGRITY
                    or _prediction_fact(source, "/prediction/completeness").value != "COMPLETE"
                    or _prediction_fact(source, "/prediction/quality_class").value != "high"
                    for source in cited
                )
            ):
                raise AgentError("unsupported_prediction_association")
            statement = (
                "A classificação NEXT_PULL e a avaliação AFTER_PULL_OFFLINE usam a mesma "
                "FeatureSet e puxada de origem. São saídas distintas e relacionadas pelo "
                "snapshot compartilhado; não constituem confirmação independente, medida de "
                "causalidade nem confiança combinada. "
                f"Papel da fonte: {left.source_role}; cortes: "
                f"{left.effective_cutoff.isoformat()} e {right.effective_cutoff.isoformat()}."
            )
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
    predictive_evidence_cited = any(
        source.source_tool == "get_prediction_evidence"
        for finding in findings
        for source in (registry.items[identifier] for identifier in finding.evidence_ids)
    )
    warnings = list(dict.fromkeys(warnings))[:32]
    return Answer(
        answer="\n".join(f.statement for f in findings),
        confidence="low"
        if insufficient or warnings or predictive_evidence_cited
        else draft.confidence,
        findings=findings,
        evidence=registry.ordered(),
        context=context,
        uncertainties=[
            "Causalidade e diagnóstico mecânico não demonstrados pelos dados disponíveis."
        ],
        limitations=warnings,
        missing_evidence=list(draft.missing_evidence),
    )
