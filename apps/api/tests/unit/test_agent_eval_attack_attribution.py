from vehicle_platform.agent_evaluation import cli
from vehicle_platform.agent_evaluation.attack_attribution import attribute_attack
from vehicle_platform.agent_evaluation.cli import DEFAULT_SUITE
from vehicle_platform.agent_evaluation.contracts import (
    AgentEvalCase,
    AttemptStatus,
    CaseAttempt,
    DirectProbeEvidence,
)
from vehicle_platform.agent_evaluation.corpus import load_corpus


def _attack_case() -> AgentEvalCase:
    _document, cases, _digest = load_corpus(DEFAULT_SUITE)
    return next(case for case in cases if case.attack_family and case.forbidden_tools)


def test_denied_forbidden_tool_is_attempted_attack_not_successful_compromise() -> None:
    case = _attack_case()
    forbidden_tool = case.forbidden_tools[0]
    attempt = CaseAttempt(
        case_id=case.case_id,
        status=AttemptStatus.PASS,
        observed_tools=(forbidden_tool,),
        successful_tools=(),
    )

    result = attribute_attack(case, attempt)

    assert result is not None
    assert result.attempted is True
    assert result.provider_intent_generated is True
    assert result.successful_compromise is False
    assert result.observable == "no_observed_compromise_signal"
    assert result.tool_schema_blocked is None
    assert result.mcp_auth_blocked is None


def test_successful_forbidden_tool_is_compromise() -> None:
    case = _attack_case()
    forbidden_tool = case.forbidden_tools[0]
    attempt = CaseAttempt(
        case_id=case.case_id,
        status=AttemptStatus.PASS,
        observed_tools=(forbidden_tool,),
        successful_tools=(forbidden_tool,),
    )

    result = attribute_attack(case, attempt)

    assert result is not None
    assert result.successful_compromise is True
    assert result.observable == "forbidden_tool_succeeded"


def test_unrun_or_budget_skipped_case_is_not_counted_as_attack_attempt() -> None:
    case = _attack_case()
    attempt = CaseAttempt(case_id=case.case_id, status=AttemptStatus.SKIPPED_BUDGET)

    result = attribute_attack(case, attempt)

    assert result is not None
    assert result.attempted is False


def test_defense_boundary_is_unknown_when_not_instrumented_and_measured_when_probed() -> None:
    case = _attack_case()
    unmeasured = attribute_attack(
        case, CaseAttempt(case_id=case.case_id, status=AttemptStatus.PASS)
    )
    probed = attribute_attack(
        case,
        CaseAttempt(
            case_id=case.case_id,
            status=AttemptStatus.PASS,
            direct_probe=DirectProbeEvidence(
                probe_type="mcp_capability",
                target="read_vehicle",
                call_rejected=True,
                output_sha256="a" * 64,
            ),
        ),
    )

    assert unmeasured is not None and unmeasured.mcp_auth_blocked is None
    assert probed is not None and probed.mcp_auth_blocked is True


def test_report_keeps_missing_attack_attribution_visible() -> None:
    _document, cases, _digest = load_corpus(DEFAULT_SUITE)
    case = next(item for item in cases if item.attack_family)
    assert case.attack_family is not None

    summary = cli._attack_attribution_summary(cases, [{"case_id": case.case_id}])

    family_cases = sum(item.attack_family == case.attack_family for item in cases)
    assert summary[case.attack_family]["unclassified"] == family_cases


def test_non_attack_case_has_no_attack_attribution() -> None:
    _document, cases, _digest = load_corpus(DEFAULT_SUITE)
    case = next(item for item in cases if item.attack_family is None)

    assert (
        attribute_attack(case, CaseAttempt(case_id=case.case_id, status=AttemptStatus.PASS)) is None
    )


def test_parameter_injection_probe_distinguishes_rejected_accepted_and_unmeasured() -> None:
    case = _attack_case()
    base = dict(
        probe_type="mcp_parameter_injection",
        target="read_vehicle",
        output_sha256="a" * 64,
    )

    rejected = attribute_attack(
        case,
        CaseAttempt(
            case_id=case.case_id,
            status=AttemptStatus.PASS,
            direct_probe=DirectProbeEvidence(
                **base, call_rejected=True, output_summary={"invalid_extra_field_rejected": True}
            ),
        ),
    )
    accepted = attribute_attack(
        case,
        CaseAttempt(
            case_id=case.case_id,
            status=AttemptStatus.PASS,
            direct_probe=DirectProbeEvidence(
                **base, call_rejected=False, output_summary={"invalid_extra_field_rejected": False}
            ),
        ),
    )
    unmeasured = attribute_attack(
        case,
        CaseAttempt(
            case_id=case.case_id,
            status=AttemptStatus.PASS,
            direct_probe=DirectProbeEvidence(
                **base,
                call_rejected=False,
                output_summary={"invalid_extra_field_rejected": "unknown"},
            ),
        ),
    )

    assert rejected is not None and rejected.tool_schema_blocked is True
    assert rejected.successful_compromise is False
    assert accepted is not None and accepted.tool_schema_blocked is False
    assert accepted.successful_compromise is True
    assert accepted.observable == "direct_boundary_probe_not_rejected"
    assert unmeasured is not None and unmeasured.tool_schema_blocked is None
    assert unmeasured.successful_compromise is False


def test_forbidden_claim_in_answer_or_evidence_is_a_compromise() -> None:
    _document, cases, _digest = load_corpus(DEFAULT_SUITE)
    case = next(item for item in cases if item.attack_family and item.forbidden_claims)
    forbidden_claim = case.forbidden_claims[0]
    attempt = CaseAttempt(
        case_id=case.case_id,
        status=AttemptStatus.PASS,
        findings=({"detail": "quoted " + forbidden_claim},),
    )

    result = attribute_attack(case, attempt)

    assert result is not None
    assert result.successful_compromise is True
    assert result.observable == "forbidden_claim_in_public_output"
