from typing import Any

from vehicle_platform.agent_evaluation.contracts import (
    AgentEvalCase,
    AttemptStatus,
    CaseAttempt,
    EvalReceipt,
    ToolTrace,
)
from vehicle_platform.agent_evaluation.corpus import canonical_json, sha256_bytes
from vehicle_platform.agent_evaluation.grader import grade


def receipt_digest(payload: dict[str, Any]) -> str:
    unsigned = {key: value for key, value in payload.items() if key != "receipt_sha256"}
    return sha256_bytes(canonical_json(unsigned))


def create_receipt(payload: dict[str, Any]) -> EvalReceipt:
    unsigned = {key: value for key, value in payload.items() if key != "receipt_sha256"}
    unsigned.setdefault("receipt_sha256", "0" * 64)
    normalized = EvalReceipt.model_validate(unsigned).model_dump(mode="json")
    normalized["receipt_sha256"] = receipt_digest(normalized)
    return EvalReceipt.model_validate(normalized)


def verify_receipt(
    raw: dict[str, Any],
    cases: tuple[AgentEvalCase, ...],
    *,
    expected_sha: str,
    suite_sha: str,
    suite_version: str | None = None,
    oracle_facts: dict[str, tuple[Any, ...]] | None = None,
    expected_source_sha: str | None = None,
    persisted_runs: dict[str, dict[str, Any]] | None = None,
    expected_dependency_manifest_sha256: str | None = None,
    expected_prompt_manifest_sha256: str | None = None,
    expected_tool_catalog_sha256: str | None = None,
    expected_schema_revision: str | None = None,
    expected_environment: str | None = None,
    expected_provider: str | None = None,
    expected_model: str | None = None,
) -> tuple[bool, tuple[str, ...]]:
    reasons: list[str] = []
    try:
        receipt = EvalReceipt.model_validate(raw)
    except Exception:
        return False, ("receipt_schema_invalid",)
    if receipt.repository_sha != expected_sha:
        reasons.append("repository_sha_mismatch")
    if receipt.suite_sha256 != suite_sha:
        reasons.append("suite_sha256_mismatch")
    if suite_version is not None and receipt.suite_version != suite_version:
        reasons.append("suite_version_mismatch")
    if expected_source_sha is not None and receipt.source_fixture_sha256 != expected_source_sha:
        reasons.append("source_fixture_digest_mismatch")
    manifest_expectations = (
        ("dependency_manifest_sha256", expected_dependency_manifest_sha256),
        ("prompt_manifest_sha256", expected_prompt_manifest_sha256),
        ("tool_catalog_sha256", expected_tool_catalog_sha256),
        ("schema_revision", expected_schema_revision),
        ("environment", expected_environment),
        ("provider", expected_provider),
        ("model", expected_model),
    )
    for field, expected_value in manifest_expectations:
        if expected_value is not None and getattr(receipt, field) != expected_value:
            reasons.append(f"{field}_mismatch")
    if receipt.receipt_sha256 != receipt_digest(raw):
        reasons.append("receipt_digest_mismatch")
    expected = {case.case_id: case for case in cases}
    attempts: dict[str, CaseAttempt] = {}
    for attempt in receipt.attempts:
        if attempt.case_id not in expected:
            reasons.append("unknown_case_attempt")
            continue
        if attempt.case_id in attempts:
            reasons.append("duplicate_case_attempt")
            continue
        attempts[attempt.case_id] = attempt
        status, _ = grade(
            expected[attempt.case_id],
            attempt,
            selected_vehicle_id=attempt.selected_vehicle_id,
            expected_facts=(oracle_facts or {}).get(attempt.case_id),
        )
        if oracle_facts is not None and expected[attempt.case_id].expected_facts:
            independently_resolved = oracle_facts.get(attempt.case_id)
            if attempt.status != AttemptStatus.NOT_RUN and independently_resolved is None:
                reasons.append("independent_oracle_facts_missing")
            elif (
                independently_resolved is not None
                and attempt.resolved_oracle_facts != independently_resolved
            ):
                reasons.append("resolved_oracle_fact_mismatch")
        if status != attempt.status:
            reasons.append("claimed_status_disagrees_with_independent_grade")
        if status != AttemptStatus.PASS:
            reasons.append("case_not_pass")
        if persisted_runs is not None:
            persisted = persisted_runs.get(attempt.case_id)
            if attempt.run_id is None:
                if expected[attempt.case_id].persistence_required:
                    reasons.append("persisted_agent_run_id_missing")
                elif persisted is not None:
                    reasons.append("unexpected_persisted_agent_run")
                elif attempt.status != AttemptStatus.NOT_RUN:
                    reasons.append("independent_non_agent_evidence_missing")
            elif persisted is None:
                reasons.append("persisted_agent_run_not_found")
            else:
                snapshot = persisted.get("snapshot")
                if not isinstance(snapshot, dict):
                    reasons.append("persisted_agent_run_snapshot_invalid")
                else:
                    if str(snapshot.get("id")) != attempt.run_id:
                        reasons.append("persisted_agent_run_id_mismatch")
                    if persisted.get("vehicle_id") != attempt.selected_vehicle_id:
                        reasons.append("persisted_agent_vehicle_mismatch")
                    if persisted.get("status") != attempt.answer_status:
                        reasons.append("persisted_agent_status_mismatch")
                    if (
                        expected_provider is not None
                        and snapshot.get("provider") != expected_provider
                    ):
                        reasons.append("persisted_agent_provider_mismatch")
                    if expected_model is not None and snapshot.get("model") != expected_model:
                        reasons.append("persisted_agent_model_mismatch")
                    result = snapshot.get("result")
                    persisted_answer = result.get("answer") if isinstance(result, dict) else ""
                    if (persisted_answer or "") != attempt.answer_text:
                        reasons.append("persisted_agent_answer_mismatch")
                    persisted_findings = (
                        result.get("findings", []) if isinstance(result, dict) else []
                    )
                    persisted_evidence = (
                        result.get("evidence", []) if isinstance(result, dict) else []
                    )
                    if canonical_json(persisted_findings) != canonical_json(list(attempt.findings)):
                        reasons.append("persisted_agent_findings_mismatch")
                    if canonical_json(persisted_evidence) != canonical_json(list(attempt.evidence)):
                        reasons.append("persisted_agent_evidence_mismatch")
                    calls = persisted.get("tool_calls", [])
                    if not isinstance(calls, list) or len(calls) != attempt.mcp_call_count:
                        reasons.append("persisted_agent_tool_count_mismatch")
                    else:
                        try:
                            observed = tuple(
                                ToolTrace(
                                    tool_name=str(call.get("tool_name", "")),
                                    status=str(call.get("status", "")),
                                    argument_sha256=str(call.get("argument_hash", "")),
                                    duration_ms=(
                                        int(float(call["duration_seconds"]) * 1000)
                                        if call.get("duration_seconds") is not None
                                        else None
                                    ),
                                )
                                for call in calls
                                if isinstance(call, dict)
                            )
                        except (TypeError, ValueError):
                            observed = ()
                        if len(observed) != len(calls) or observed != attempt.tool_trace:
                            reasons.append("persisted_agent_tool_trace_mismatch")
                    events = persisted.get("events", [])
                    event_types = (
                        tuple(
                            str(event.get("type", ""))
                            for event in events
                            if isinstance(event, dict)
                        )
                        if isinstance(events, list)
                        else ()
                    )
                    if event_types != attempt.sse_event_types:
                        reasons.append("persisted_agent_event_stream_mismatch")
    if set(attempts) != set(expected):
        reasons.append("case_coverage_incomplete")
    for attempt in receipt.attempts:
        if attempt.source_digest_before != receipt.source_fixture_sha256:
            reasons.append("attempt_source_digest_mismatch")
        if attempt.source_digest_after != receipt.source_fixture_sha256:
            reasons.append("attempt_source_mutated_or_unmeasured")
        if attempt.tool_trace_sha256 is not None:
            trace_digest = sha256_bytes(
                canonical_json([trace.model_dump(mode="json") for trace in attempt.tool_trace])
            )
            if trace_digest != attempt.tool_trace_sha256:
                reasons.append("tool_trace_digest_mismatch")
    if receipt.paid_provider_calls != 0 or receipt.provider_cost_usd != 0:
        reasons.append("paid_provider_use_forbidden_in_deterministic_receipt")
    return not reasons, tuple(dict.fromkeys(reasons))
