from vehicle_platform.agent_evaluation.cli import DEFAULT_SUITE
from vehicle_platform.agent_evaluation.contracts import (
    AttemptStatus,
    CaseAttempt,
    Severity,
)
from vehicle_platform.agent_evaluation.corpus import load_corpus
from vehicle_platform.agent_evaluation.receipts import create_receipt, verify_receipt
from vehicle_platform.agent_evaluation.thresholds import load_threshold_policy, score_thresholds


def test_threshold_policy_is_pinned_and_full_denominators_are_required() -> None:
    policy, digest = load_threshold_policy()
    _document, cases, _suite_digest = load_corpus(DEFAULT_SUITE)

    scored = score_thresholds(cases, (), independently_graded={}, policy=policy)

    assert policy.policy_version == "phase11-thresholds-v1"
    assert len(digest) == 64
    assert scored["policy_sha256"] == digest
    assert all(outcome["status"] == "UNDEFINED" for outcome in scored["metrics"].values())
    assert scored["metrics"]["benign_usefulness"]["denominator"] > 0
    assert scored["metrics"]["expected_route_accuracy"]["denominator"] > 0
    assert scored["metrics"]["grounded_fact_accuracy"]["denominator"] > 0


def test_thresholds_pass_only_when_independent_all_case_metrics_pass() -> None:
    policy, _digest = load_threshold_policy()
    _document, all_cases, _suite_digest = load_corpus(DEFAULT_SUITE)
    benign = next(
        case for case in all_cases if case.family.value == "benign" and case.expected_facts
    )
    critical_attack = next(
        case
        for case in all_cases
        if case.severity is Severity.CRITICAL and case.attack_family and case.forbidden_tools
    )
    cases = (benign, critical_attack)
    attempts = tuple(
        CaseAttempt(
            case_id=case.case_id,
            status=AttemptStatus.PASS,
            run_id=f"run-{index}",
            answer_status="completed",
            observed_route=case.expected_route,
        )
        for index, case in enumerate(cases)
    )
    graded = {case.case_id: AttemptStatus.PASS for case in cases}

    scored = score_thresholds(cases, attempts, independently_graded=graded, policy=policy)

    assert all(outcome["status"] == "PASS" for outcome in scored["metrics"].values())


def test_critical_compromise_breaks_pre_registered_zero_tolerance() -> None:
    policy, _digest = load_threshold_policy()
    _document, all_cases, _suite_digest = load_corpus(DEFAULT_SUITE)
    benign = next(
        case for case in all_cases if case.family.value == "benign" and case.expected_facts
    )
    critical_attack = next(
        case
        for case in all_cases
        if case.severity is Severity.CRITICAL and case.attack_family and case.forbidden_tools
    )
    cases = (benign, critical_attack)
    forbidden_tool = critical_attack.forbidden_tools[0]
    attempts = (
        CaseAttempt(
            case_id=benign.case_id,
            status=AttemptStatus.PASS,
            run_id="run-benign",
            answer_status="completed",
            observed_route=benign.expected_route,
        ),
        CaseAttempt(
            case_id=critical_attack.case_id,
            status=AttemptStatus.PASS,
            run_id="run-critical",
            answer_status="completed",
            observed_tools=(forbidden_tool,),
            successful_tools=(forbidden_tool,),
            observed_route=critical_attack.expected_route,
        ),
    )
    graded = {case.case_id: AttemptStatus.PASS for case in cases}

    scored = score_thresholds(cases, attempts, independently_graded=graded, policy=policy)

    compromise = scored["metrics"]["critical_compromise_acceptance"]
    assert compromise["successful_compromises"] == 1
    assert compromise["status"] == "FAIL"


def test_receipt_checker_rejects_missing_threshold_binding_and_incomplete_metrics() -> None:
    policy, digest = load_threshold_policy()
    _document, all_cases, suite_digest = load_corpus(DEFAULT_SUITE)
    case = next(
        item for item in all_cases if item.severity is Severity.CRITICAL and item.attack_family
    )
    attempt = CaseAttempt(case_id=case.case_id, status=AttemptStatus.NOT_RUN)
    receipt = create_receipt(
        {
            "schema_version": "1.0",
            "suite_version": "phase11-threshold-unit",
            "suite_sha256": suite_digest,
            "repository_sha": "a" * 40,
            "source_fixture_sha256": "b" * 64,
            "scenario_generator_version": "1.0",
            "random_seed": 0,
            "dependency_manifest_sha256": "c" * 64,
            "prompt_manifest_sha256": "d" * 64,
            "tool_catalog_sha256": "e" * 64,
            "schema_revision": "0020",
            "environment": "test",
            "provider": "deterministic",
            "model": "scripted-v1",
            "attempts": [attempt.model_dump(mode="json")],
        }
    ).model_dump(mode="json")

    valid, reasons = verify_receipt(
        receipt,
        (case,),
        expected_sha="a" * 40,
        suite_sha=suite_digest,
        suite_version="phase11-threshold-unit",
        expected_threshold_policy=policy,
        expected_threshold_policy_sha256=digest,
    )

    assert not valid
    assert "threshold_policy_version_mismatch" in reasons
    assert "threshold_policy_sha256_mismatch" in reasons
    assert any(reason.startswith("scoring_threshold_not_pass:") for reason in reasons)
