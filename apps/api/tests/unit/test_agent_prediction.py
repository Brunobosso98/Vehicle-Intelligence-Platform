import json
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import pytest
from pydantic import SecretStr, ValidationError
from test_agents import execution, fixture, telemetry  # noqa: F401
from test_knowledge import retrieval_fixture

from vehicle_platform.agents.config import AgentSettings
from vehicle_platform.agents.evidence import EvidenceRegistry
from vehicle_platform.agents.grounding import prediction_answer, validate
from vehicle_platform.agents.orchestration import Orchestrator
from vehicle_platform.agents.provider import AgentError
from vehicle_platform.agents.schemas import (
    Ask,
    Binding,
    Claim,
    Classification,
    Draft,
    VehicleContext,
)
from vehicle_platform.agents.specialists.contracts import Specialist
from vehicle_platform.agents.specialists.routing import hints_for, prediction_request_intent
from vehicle_platform.agents.specialists.validation import validate_prediction_scope
from vehicle_platform.mcp.schemas import Envelope, PredictionEvidenceMCPProjection

NOW = datetime(2026, 10, 22, tzinfo=UTC)


def projection(
    *,
    vehicle_id=None,
    evidence_id=None,
    result_type="next_pull",
    horizon="NEXT_PULL",
    task="NEXT_PULL_THERMAL_DEGRADATION",
    family=None,
    status="READY_SCORE",
    decision=True,
    score=0.72,
    threshold=0.5,
    completeness="COMPLETE",
    integrity="VERIFIED",
    quality_class="high",
    artifact_availability="VERIFIED",
    session_id=None,
):
    vehicle = vehicle_id or uuid4()
    source_evidence = evidence_id or uuid4()
    pull_id, configuration_id = uuid4(), uuid4()
    return PredictionEvidenceMCPProjection.model_validate_json(
        json.dumps(
            {
                "schema_version": "prediction-agent-summary-v1",
                "evidence_id": str(source_evidence),
                "receipt_id": str(uuid4()),
                "source_vehicle_id": str(vehicle),
                "source_session_id": str(session_id or uuid4()),
                "source_pull_id": str(pull_id),
                "source_configuration_id": str(configuration_id),
                "source_feature_set_id": str(uuid4()),
                "result_type": result_type,
                "horizon": horizon,
                "task": task,
                "family": family,
                "source_role": "synthetic",
                "requested_cutoff": NOW.isoformat(),
                "effective_cutoff": NOW.isoformat(),
                "status": status,
                "reason_code": "INSUFFICIENT_SIGNAL" if score is None else None,
                "model_version": "model-v1" if result_type == "next_pull" else None,
                "model_algorithm": "random_forest" if result_type == "next_pull" else None,
                "detector_version": "detector-v1" if result_type == "anomaly" else None,
                "detector_algorithm_version": "detector-alg-v1"
                if result_type == "anomaly"
                else None,
                "detector_method": "robust_mad" if result_type == "anomaly" else None,
                "decision": decision,
                "score": score,
                "threshold": threshold,
                "score_is_probability": False,
                "completeness": completeness,
                "integrity": integrity,
                "verification_reasons": [],
                "quality_class": quality_class,
                "coverage": 1.0,
                "feature_coverage": 1.0,
                "observed_feature_count": 1,
                "expected_feature_count": 1,
                "source_type": "synthetic",
                "missing_reason_counts": {},
                "available_signals": ["engine.intake_air_temperature"],
                "invalid_observation_count": 0,
                "duplicate_timestamp_count": 0,
                "pull_completeness": 1.0,
                "artifact_availability": artifact_availability,
                "reference_row_count": 30 if result_type == "anomaly" else None,
                "reference_session_count": 6 if result_type == "anomaly" else None,
                "facts": [
                    {
                        "key": "thermal.pre_pull_iat_k",
                        "fact_type": "COMPUTED_FEATURE",
                        "value": 300.0,
                        "unit": "K",
                        "quality": "VALID",
                        "cutoff": NOW.isoformat(),
                        "observed_at": NOW.isoformat(),
                        "available_at": NOW.isoformat(),
                    }
                ],
                "gaps": [],
                "omitted_count": 0,
            }
        )
    )


def add_prediction(registry, projection_value):
    return registry.add(
        "get_prediction_evidence",
        uuid4(),
        Envelope(
            data=projection_value.model_dump(mode="json"),
            context={
                "vehicle_id": registry.vehicle_id,
                "session_id": projection_value.source_session_id,
                "pull_id": projection_value.source_pull_id,
            },
            provenance={"source": "immutable-phase9e-evidence"},
            returned=1,
        ),
    )[0]


def test_explicit_prediction_routing_is_deterministic_and_domain_scoped():
    assert prediction_request_intent("Qual foi a previsão registrada?").value == "prediction"
    assert prediction_request_intent("Was an anomaly detected?").value == "anomaly"
    assert prediction_request_intent("How does the anomaly detector work?") is None
    assert prediction_request_intent("Summarize my vehicle") is None
    hints = hints_for("Qual foi a previsão registrada?", [])
    assert hints.intent.value == "prediction"
    assert hints.candidates == ()
    assert hints.required == ()
    assert hints_for("Explain the thermal prediction", []).required == (Specialist.THERMAL,)
    assert prediction_request_intent("Train a stronger model and predict my failure chance") is None
    assert prediction_request_intent("Can I keep accelerating safely?") is None


def test_settings_keep_predictive_access_separate_and_controlled():
    base = {
        "environment": "test",
        "prediction_service_enabled": True,
        "prediction_evidence_enabled": True,
        "prediction_capability_token": SecretStr("c" * 48),
        "prediction_mcp_token": SecretStr("p" * 48),
        "mcp_token": SecretStr("m" * 48),
        "prediction_vehicle_ids": [uuid4()],
    }
    assert AgentSettings(**base).prediction_evidence_enabled
    for updates in (
        {"environment": "production"},
        {"prediction_vehicle_ids": []},
        {"prediction_mcp_token": SecretStr("m" * 48)},
        {"prediction_capability_token": SecretStr("p" * 48)},
    ):
        with pytest.raises(ValidationError):
            AgentSettings(**(base | updates))


def test_projection_keeps_source_lineage_private_and_bounds_facts():
    vehicle = uuid4()
    projected = projection(vehicle_id=vehicle)
    registry = EvidenceRegistry(
        uuid4(), vehicle, 20, selected_prediction_ids=(projected.evidence_id,)
    )
    evidence = add_prediction(registry, projected)
    public = evidence.model_dump_json()
    assert evidence.source_tool == "get_prediction_evidence"
    assert evidence.configuration_id is evidence.session_id is evidence.pull_id is None
    assert str(projected.evidence_id) not in public
    assert str(projected.receipt_id) not in public
    assert str(projected.source_feature_set_id) not in public
    values = {fact.path: (fact.value, fact.unit) for fact in evidence.facts}
    assert values["/prediction/score"] == (0.72, "engineering_validation_score")
    assert values["/prediction/features/thermal.pre_pull_iat_k"] == (300.0, "K")
    assert values["/prediction/feature_quality/thermal.pre_pull_iat_k"][0] == "VALID"


def test_projection_rejects_non_finite_source_scores():
    raw = json.loads(projection().model_dump_json())
    raw["score"] = float("nan")
    with pytest.raises(ValidationError, match="non-finite"):
        PredictionEvidenceMCPProjection.model_validate_json(json.dumps(raw))


def test_unavailable_snapshot_is_limited_to_historical_recorded_output():
    vehicle = uuid4()
    projected = projection(
        vehicle_id=vehicle,
        integrity="VERIFIED_SNAPSHOT_ARTIFACT_UNAVAILABLE",
        artifact_availability="UNAVAILABLE",
    )
    registry = EvidenceRegistry(
        uuid4(), vehicle, 20, selected_prediction_ids=(projected.evidence_id,)
    )
    add_prediction(registry, projected)
    answer = prediction_answer(
        registry,
        VehicleContext(vehicle_id=vehicle, as_of=NOW),
        "prediction",
        question="Qual foi a previsão registrada?",
    )
    assert answer.findings[0].template == "prediction_result"
    assert any("artefato histórico" in item for item in answer.limitations)


def test_projection_rejects_foreign_source_vehicle_and_unselected_evidence():
    vehicle = uuid4()
    foreign = projection(vehicle_id=uuid4())
    registry = EvidenceRegistry(
        uuid4(), vehicle, 20, selected_prediction_ids=(foreign.evidence_id,)
    )
    with pytest.raises(AgentError, match="incompatible_context"):
        add_prediction(registry, foreign)
    unselected = projection(vehicle_id=vehicle)
    registry = EvidenceRegistry(uuid4(), vehicle, 20, selected_prediction_ids=(uuid4(),))
    with pytest.raises(AgentError, match="incompatible_context"):
        add_prediction(registry, unselected)


@pytest.mark.parametrize("scope", ["session", "pull"])
def test_projection_rejects_mismatched_selected_session_or_pull(scope):
    vehicle = uuid4()
    projected = projection(vehicle_id=vehicle)
    registry = EvidenceRegistry(
        uuid4(),
        vehicle,
        20,
        selected_session_id=uuid4() if scope == "session" else None,
        selected_pull_id=uuid4() if scope == "pull" else None,
        selected_prediction_ids=(projected.evidence_id,),
    )
    with pytest.raises(AgentError, match="incompatible_context"):
        add_prediction(registry, projected)


def test_prediction_result_is_application_rendered_and_low_confidence():
    vehicle = uuid4()
    projected = projection(vehicle_id=vehicle)
    registry = EvidenceRegistry(
        uuid4(), vehicle, 20, selected_prediction_ids=(projected.evidence_id,)
    )
    add_prediction(registry, projected)
    answer = prediction_answer(
        registry,
        VehicleContext(vehicle_id=vehicle, as_of=NOW),
        "prediction",
        question="Qual foi a previsão registrada?",
    )
    assert answer.confidence == "low"
    assert "NEXT_PULL" in answer.answer
    assert "3 K" in answer.answer
    assert "não é probabilidade calibrada de falha" in answer.answer
    assert answer.findings[0].classification is Classification.MODEL_CLASSIFICATION
    assert answer.findings[0].template == "prediction_result"


def test_anomaly_renderer_preserves_family_reference_and_nonprobability_semantics():
    vehicle = uuid4()
    projected = projection(
        vehicle_id=vehicle,
        result_type="anomaly",
        horizon="AFTER_PULL_OFFLINE",
        task=None,
        family="thermal",
        decision="ANOMALOUS",
        score=4.2,
        threshold=3.5,
    )
    registry = EvidenceRegistry(
        uuid4(), vehicle, 20, selected_prediction_ids=(projected.evidence_id,)
    )
    add_prediction(registry, projected)
    answer = prediction_answer(
        registry,
        VehicleContext(vehicle_id=vehicle, as_of=NOW),
        "anomaly",
        question="Existiu anomalia térmica?",
    )
    assert answer.findings[0].classification is Classification.STATISTICAL_OUTLIER
    assert "AFTER_PULL_OFFLINE" in answer.answer
    assert "relativamente incomum" in answer.answer
    assert "30 linhas e 6 sessões" in answer.answer
    assert "não é probabilidade" in answer.answer


@pytest.mark.parametrize(
    ("status", "completeness", "quality", "decision", "score"),
    [
        ("READY_SCORE", "PARTIAL", "degraded", True, 0.72),
        ("ABSTAINED_INSUFFICIENT_SIGNAL", "ABSTAINED", "insufficient", None, None),
    ],
)
def test_abstention_and_partial_evidence_render_only_a_data_gap(
    status, completeness, quality, decision, score
):
    vehicle = uuid4()
    projected = projection(
        vehicle_id=vehicle,
        status=status,
        decision=decision,
        score=score,
        threshold=0.5 if score is not None else None,
        completeness=completeness,
        quality_class=quality,
    )
    registry = EvidenceRegistry(
        uuid4(), vehicle, 20, selected_prediction_ids=(projected.evidence_id,)
    )
    add_prediction(registry, projected)
    answer = prediction_answer(
        registry,
        VehicleContext(vehicle_id=vehicle, as_of=NOW),
        "prediction",
        question="Qual foi a previsão registrada?",
    )
    assert answer.findings[0].classification is Classification.DATA_GAP
    assert answer.findings[0].template == "prediction_insufficient"
    assert status in answer.answer
    assert "0.72" not in answer.answer
    assert "aprovação explícita" in " ".join(answer.limitations)


def test_missing_prediction_evidence_renders_only_a_data_gap():
    vehicle = uuid4()
    registry = EvidenceRegistry(uuid4(), vehicle, 20)
    answer = prediction_answer(
        registry,
        VehicleContext(vehicle_id=vehicle, as_of=NOW),
        "prediction",
        question="Qual foi a previsão registrada?",
    )
    assert answer.findings[0].classification is Classification.DATA_GAP
    assert answer.findings[0].template == "prediction_insufficient"
    assert "não há resultado preditivo elegível" in answer.answer.casefold()


def test_real_vehicle_request_rejects_synthetic_source_role():
    vehicle = uuid4()
    projected = projection(vehicle_id=vehicle)
    registry = EvidenceRegistry(
        uuid4(), vehicle, 20, selected_prediction_ids=(projected.evidence_id,)
    )
    add_prediction(registry, projected)
    answer = prediction_answer(
        registry,
        VehicleContext(vehicle_id=vehicle, as_of=NOW),
        "prediction",
        question="What was the prediction for my real car?",
    )
    assert answer.findings[0].classification is Classification.DATA_GAP
    assert any("source_role_not_real_vehicle" in limit for limit in answer.limitations)


def test_provider_cannot_bind_prediction_result_to_wrong_horizon_or_score():
    vehicle = uuid4()
    projected = projection(vehicle_id=vehicle)
    registry = EvidenceRegistry(
        uuid4(), vehicle, 20, selected_prediction_ids=(projected.evidence_id,)
    )
    evidence = add_prediction(registry, projected)
    context = VehicleContext(vehicle_id=vehicle, as_of=NOW)
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
    facts = {fact.path: fact for fact in evidence.facts}
    bindings = [
        Binding(
            evidence_id=evidence.id,
            path=path,
            value="AFTER_PULL_OFFLINE" if path == "/prediction/horizon" else facts[path].value,
            unit=facts[path].unit,
        )
        for path in paths
    ]
    draft = Draft(
        confidence="high",
        claims=[
            Claim(
                classification=Classification.MODEL_CLASSIFICATION,
                template="prediction_result",
                bindings=bindings,
                evidence_ids=[evidence.id],
            )
        ],
        missing_evidence=[],
    )
    with pytest.raises(AgentError, match="unsupported_claim"):
        validate(draft, registry, context)


def test_domain_specialist_cannot_relabel_prediction_as_measurement():
    vehicle = uuid4()
    projected = projection(vehicle_id=vehicle)
    registry = EvidenceRegistry(
        uuid4(), vehicle, 20, selected_prediction_ids=(projected.evidence_id,)
    )
    evidence = add_prediction(registry, projected)
    claim = Claim(
        classification=Classification.OBSERVATION,
        template="recorded_fact",
        bindings=[
            Binding(
                evidence_id=evidence.id,
                path="/prediction/score",
                value=0.72,
                unit="engineering_validation_score",
            )
        ],
        evidence_ids=[evidence.id],
    )
    with pytest.raises(AgentError, match="specialist_prediction_scope_violation"):
        validate_prediction_scope(Specialist.THERMAL, claim, registry)


async def test_prediction_and_applicable_documentation_keep_separate_citations(
    fixture,  # noqa: F811
    telemetry,  # noqa: F811
):
    from vehicle_platform.knowledge.domain import match, scope_hash

    state = execution(fixture)
    session_id = UUID(str(state.context.sessions[0]["id"]))
    question = (
        "Compare the previous fuel prediction with the expected N55 high pressure "
        "fuel conditions in the documentation."
    )
    projected = projection(
        vehicle_id=state.run.vehicle_id,
        task="NEXT_PULL_FUEL_DEVIATION",
        session_id=session_id,
    )
    state.registry = EvidenceRegistry(
        state.run.id,
        state.run.vehicle_id,
        80,
        selected_session_id=session_id,
        selected_prediction_ids=(projected.evidence_id,),
    )
    prediction_evidence = add_prediction(state.registry, projected)
    state.ask = Ask(
        question=question,
        session_id=session_id,
        include_prediction_evidence=True,
        prediction_evidence_ids=[projected.evidence_id],
    )
    state.final = prediction_answer(state.registry, state.context, "prediction", question=question)
    retrieval = retrieval_fixture()

    async def search(intent, scope):
        result = retrieval.model_copy(deep=True)
        result.scope = scope
        result.intent = intent
        for evidence in result.evidence:
            evidence.vehicle_id = scope.vehicle_id
            evidence.scope_hash = scope_hash(scope)
            evidence.applicability = match(evidence.document.applicability, scope)
        return result

    knowledge = SimpleNamespace(search=AsyncMock(side_effect=search))
    engine = Orchestrator(AgentSettings(), MagicMock(), MagicMock(), telemetry, knowledge=knowledge)
    engine.call = AsyncMock(return_value={"data": {}})
    await engine.knowledge_node({"execution": state})
    assert knowledge.search.await_count == 1
    assert state.knowledge_tools is not None
    assert state.knowledge_tools.results[0].scope.vehicle_id == state.run.vehicle_id
    engine.graph = SimpleNamespace(ainvoke=AsyncMock())

    answer = await engine.execute(state)

    assert answer.findings[0].evidence_ids == [prediction_evidence.id]
    assert answer.findings[0].classification is Classification.MODEL_CLASSIFICATION
    assert answer.knowledge.request_type == "HYBRID_COMPARISON"
    assert len(answer.knowledge.claims) == 1
    documentary_claim = answer.knowledge.claims[0]
    assert documentary_claim.evidence_id != prediction_evidence.id
    documentary_sources = {item.id: item for item in answer.knowledge.retrieval.evidence}
    assert documentary_claim.evidence_id in documentary_sources
    assert documentary_sources[documentary_claim.evidence_id].source.trust.value == (
        "TIER_1_AUTHORITATIVE"
    )
    assert str(projected.score) in answer.answer
    assert "synthetic N55 pressure regulator" in answer.answer
    assert "independent diagnostic proof" not in answer.answer.casefold()
