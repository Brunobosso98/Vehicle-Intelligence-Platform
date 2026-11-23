from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

SOURCE_TABLES = frozenset(
    {
        "vehicles",
        "vehicle_configurations",
        "modifications",
        "driving_sessions",
        "telemetry_samples",
        "pulls",
        "session_segments",
        "detected_events",
        "analytics_runs",
        "dataset_capability_reports",
        "feature_sets",
        "prediction_receipts",
        "prediction_evidence_bundles",
        "knowledge_documents",
        "knowledge_chunks",
        "mlops_candidates",
    }
)

SPECIALIST_NAMES = frozenset({"data_quality", "performance", "thermal", "fuel_air_boost"})


class EvalModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, hide_input_in_errors=True)


class CaseFamily(StrEnum):
    BENIGN = "benign"
    CRITICAL = "critical"
    RED_TEAM = "red_team"
    METAMORPHIC = "metamorphic"
    FAULT_INJECTION = "fault_injection"
    PROVIDER_COMPATIBILITY = "provider_compatibility"


class Severity(StrEnum):
    CRITICAL = "critical"
    SAFETY = "safety"
    MAJOR = "major"
    MINOR = "minor"


class ExpectedBehavior(StrEnum):
    ANSWER = "answer"
    ABSTAIN = "abstain"
    REFUSE = "refuse"
    DENY = "deny"
    CANCEL = "cancel"


class AttemptStatus(StrEnum):
    PASS = "PASS"  # noqa: S105 - this is an evaluation status, not a secret
    ASSERTION_FAIL = "ASSERTION_FAIL"
    UNSAFE_ACTION_BLOCKED = "UNSAFE_ACTION_BLOCKED"
    INFRA_FAILURE = "INFRA_FAILURE"
    PROVIDER_FAILURE = "PROVIDER_FAILURE"
    TIMED_OUT = "TIMED_OUT"
    NOT_RUN = "NOT_RUN"
    INSUFFICIENT_ORACLE = "INSUFFICIENT_ORACLE"
    SKIPPED_BUDGET = "SKIPPED_BUDGET"
    INCOMPLETE = "INCOMPLETE"


class OracleFact(EvalModel):
    path: str = Field(min_length=1, max_length=300)
    value: str | int | float | bool | None
    unit: str | None = Field(default=None, max_length=80)
    source_table: str = Field(min_length=1, max_length=80)

    @field_validator("source_table")
    @classmethod
    def source_table_is_allowlisted(cls, table: str) -> str:
        if table not in SOURCE_TABLES:
            raise ValueError("oracle source table is not allowlisted")
        return table


class OracleSpec(EvalModel):
    expected_behavior: ExpectedBehavior
    facts: tuple[OracleFact, ...] = Field(default=(), max_length=24)
    allowed_tools: tuple[str, ...] = Field(default=(), max_length=32)
    forbidden_tools: tuple[str, ...] = Field(default=(), max_length=32)
    forbidden_claims: tuple[str, ...] = Field(default=(), max_length=24)


class ThreatScenario(EvalModel):
    attack_family: str = Field(min_length=1, max_length=80)
    surface: str = Field(min_length=1, max_length=80)
    mutation: str = Field(min_length=1, max_length=80)
    mutation_version: int = Field(ge=1)
    seed: int = Field(ge=0, le=2**32 - 1)
    original_source_sha256: str | None = Field(default=None, pattern=r"^[a-f0-9]{64}$")


class AgentEvalProtocol(EvalModel):
    schema_version: str = Field(pattern=r"^1\.0$")
    protocol_version: str = Field(min_length=1, max_length=40)
    suite_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    deterministic_provider_required: bool = True
    paid_provider_calls_allowed: bool = False
    max_case_timeout_seconds: int = Field(default=90, ge=1, le=900)
    max_parallel_cases: int = Field(default=1, ge=1, le=16)


class RunDefinition(EvalModel):
    repository_sha: str = Field(pattern=r"^[a-f0-9]{40}$")
    suite_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    fixture_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    seed: int = Field(ge=0, le=2**32 - 1)
    provider: str = Field(min_length=1, max_length=80)
    model: str = Field(min_length=1, max_length=120)
    environment: str = Field(pattern=r"^(test|development)$")


class ToolTrace(EvalModel):
    tool_name: str = Field(min_length=1, max_length=100)
    status: str = Field(pattern=r"^(running|completed|failed)$")
    argument_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    result_sha256: str | None = Field(default=None, pattern=r"^[a-f0-9]{64}$")
    duration_ms: int | None = Field(default=None, ge=0)


class ProviderUsageMeasurement(EvalModel):
    input_tokens: int | None = Field(default=None, ge=0)
    cached_input_tokens: int | None = Field(default=None, ge=0)
    output_tokens: int | None = Field(default=None, ge=0)
    total_tokens: int | None = Field(default=None, ge=0)
    estimated_cost: float | None = Field(default=None, ge=0, allow_inf_nan=False)
    pricing_version: str | None = Field(default=None, max_length=80)


class DirectProbeEvidence(EvalModel):
    probe_type: Literal[
        "mcp_capability",
        "mcp_source_role",
        "mcp_vehicle_scope",
        "mcp_revoked_capability",
        "operator_cli",
        "knowledge_retrieval",
        "vehicle_scope_fixture",
        "specialist_conflict",
        "provider_fault",
        "source_metamorph",
        "prediction_evidence",
        "investigation_approval",
        "cancellation_lifecycle",
        "provider_boundary",
        "mcp_parameter_injection",
        "api_input_boundary",
    ]
    target: str = Field(min_length=1, max_length=100)
    visible_tools: tuple[str, ...] = Field(default=(), max_length=64)
    call_rejected: bool
    output_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    output_summary: dict[str, str | int | float | bool | None] = Field(
        default_factory=dict, max_length=24
    )


class EvidenceBindingOracle(EvalModel):
    case_id: str
    source_table: str
    source_row_id: str = Field(min_length=1, max_length=80)
    vehicle_id: str = Field(min_length=1, max_length=80)
    run_id: str = Field(min_length=1, max_length=80)
    fact: OracleFact


class AttackResult(EvalModel):
    attack_family: str
    attempted: bool
    # None means that this boundary was not instrumented for this attempt.
    provider_intent_generated: bool | None = None
    tool_schema_blocked: bool | None = None
    mcp_auth_blocked: bool | None = None
    grounding_blocked: bool | None = None
    successful_compromise: bool = False
    observable: str = Field(min_length=1, max_length=160)


class GraderResult(EvalModel):
    case_id: str
    status: AttemptStatus
    reasons: tuple[str, ...] = Field(default=(), max_length=32)


class ProviderReceipt(EvalModel):
    provider: str
    model: str
    provider_version: str = Field(min_length=1, max_length=120)
    calls: int = Field(default=0, ge=0)
    input_tokens: int = Field(default=0, ge=0)
    output_tokens: int = Field(default=0, ge=0)
    cost_usd: float = Field(default=0, ge=0, le=10000)
    approval_reference: str | None = Field(default=None, max_length=100)


class EvalEvidenceManifest(EvalModel):
    repository_sha: str = Field(pattern=r"^[a-f0-9]{40}$")
    suite_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    fixture_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    dependency_manifest_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    prompt_manifest_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    tool_catalog_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    schema_revision: str = Field(min_length=1, max_length=80)
    environment: str = Field(pattern=r"^(test|development)$")


class ResourceMeasurement(EvalModel):
    platform: str = Field(pattern=r"^(linux|darwin)$")
    child_process_count: int = Field(ge=1, le=1000)
    peak_child_rss_bytes: int = Field(gt=0)
    child_cpu_user_ms: int = Field(ge=0)
    child_cpu_system_ms: int = Field(ge=0)


class AgentEvalCase(EvalModel):
    schema_version: str = Field(pattern=r"^1\.0$")
    case_id: str = Field(pattern=r"^P11-[A-Z0-9-]{3,48}$")
    version: int = Field(ge=1)
    family: CaseFamily
    severity: Severity
    language: str = Field(pattern=r"^(en|pt-BR|mixed)$")
    author: str = Field(min_length=1, max_length=100)
    intent: str = Field(min_length=1, max_length=100)
    question: str = Field(min_length=1, max_length=2000)
    expected_behavior: ExpectedBehavior
    expected_error_category: str | None = Field(
        default=None,
        pattern=(
            r"^(mcp_unavailable|dependency_unavailable|run_timeout|provider_timeout|"
            r"provider_invalid_output)$"
        ),
    )
    expected_route: str | None = Field(default=None, max_length=80)
    persistence_required: bool = True
    expected_facts: tuple[OracleFact, ...] = Field(default=(), max_length=24)
    expected_absent_signals: tuple[str, ...] = Field(default=(), max_length=24)
    allowed_tools: tuple[str, ...] = Field(default=(), max_length=32)
    required_tools: tuple[str, ...] = Field(default=(), max_length=24)
    forbidden_tools: tuple[str, ...] = Field(default=(), max_length=24)
    attack_family: str | None = Field(default=None, max_length=80)
    source_surface: str = Field(min_length=1, max_length=80)
    vehicle_fixture: str = Field(default="synthetic-a", max_length=80)
    session_fixture: str | None = Field(default=None, max_length=80)
    source_role: str = Field(default="SYNTHETIC_ONLY", max_length=40)
    construction: str = Field(min_length=1, max_length=500)
    forbidden_claims: tuple[str, ...] = Field(default=(), max_length=24)

    @model_validator(mode="after")
    def expected_fact_paths_are_valid(self) -> AgentEvalCase:
        paths = [fact.path for fact in self.expected_facts]
        if self.intent == "multi_session_temporal_lookup":
            if (
                len(self.expected_facts) != 2
                or paths != ["/id", "/id"]
                or any(fact.source_table != "driving_sessions" for fact in self.expected_facts)
                or [fact.value for fact in self.expected_facts]
                != ["fixture-latest-session", "fixture-second-latest-session"]
            ):
                raise ValueError("multi_session_temporal_oracle_invalid")
        elif len(paths) != len(set(paths)):
            raise ValueError("oracle fact paths must be unique")
        return self

    @field_validator("expected_absent_signals")
    @classmethod
    def absent_signals_are_allowlisted(cls, signals: tuple[str, ...]) -> tuple[str, ...]:
        allowed = {
            "engine.rpm",
            "vehicle.speed",
            "engine.throttle_position",
            "engine.boost_pressure",
            "engine.intake_air_temperature",
            "engine.oil_temperature",
            "engine.coolant_temperature",
            "fuel.high_pressure",
        }
        if len(signals) != len(set(signals)) or set(signals) - allowed:
            raise ValueError("expected_absent_signals_must_be_unique_and_allowlisted")
        return signals


class CaseAttempt(EvalModel):
    case_id: str
    status: AttemptStatus
    run_id: str | None = None
    selected_vehicle_id: str | None = None
    resolved_oracle_facts: tuple[OracleFact, ...] = Field(default=(), max_length=24)
    source_signal_presence: dict[str, bool] = Field(default_factory=dict, max_length=24)
    answer_status: str | None = None
    answer_text: str = Field(default="", max_length=12000)
    findings: tuple[dict[str, Any], ...] = Field(default=(), max_length=32)
    evidence: tuple[dict[str, Any], ...] = Field(default=(), max_length=120)
    observed_tools: tuple[str, ...] = Field(default=(), max_length=64)
    successful_tools: tuple[str, ...] = Field(default=(), max_length=64)
    observed_specialists: tuple[str, ...] = Field(default=(), max_length=4)
    tool_trace: tuple[ToolTrace, ...] = Field(default=(), max_length=32)
    direct_probe: DirectProbeEvidence | None = None
    attack_result: AttackResult | None = None
    tool_trace_sha256: str | None = Field(default=None, pattern=r"^[a-f0-9]{64}$")
    sse_event_types: tuple[str, ...] = Field(default=(), max_length=128)
    sse_replay_verified: bool = False
    sse_replay_event_count: int = Field(default=0, ge=0, le=400)
    sse_replay_stream_sha256: str | None = Field(default=None, pattern=r"^[a-f0-9]{64}$")
    sse_replay_repeat_sha256: str | None = Field(default=None, pattern=r"^[a-f0-9]{64}$")
    sse_replay_empty_after_terminal: bool = False
    sse_replay_tool_count_unchanged: bool = False
    model_turn_count: int | None = Field(default=None, ge=0, le=16)
    mcp_call_count: int = Field(default=0, ge=0, le=32)
    forbidden_action_count: int = Field(default=0, ge=0, le=1000)
    source_digest_before: str | None = Field(default=None, pattern=r"^[a-f0-9]{64}$")
    source_digest_after: str | None = Field(default=None, pattern=r"^[a-f0-9]{64}$")
    elapsed_ms: int | None = Field(default=None, ge=0)
    first_sse_event_ms: int | None = Field(default=None, ge=0)
    routing_ms: int | None = Field(default=None, ge=0)
    specialist_work_ms: int | None = Field(default=None, ge=0)
    tool_work_ms: int | None = Field(default=None, ge=0)
    rag_tool_work_ms: int | None = Field(default=None, ge=0)
    provider_usage: dict[str, ProviderUsageMeasurement] = Field(default_factory=dict, max_length=8)
    error_category: str | None = Field(default=None, max_length=80)
    observed_route: str | None = Field(default=None, max_length=80)
    reasons: tuple[str, ...] = Field(default=(), max_length=32)

    @field_validator("observed_specialists")
    @classmethod
    def observed_specialists_are_allowlisted(cls, specialists: tuple[str, ...]) -> tuple[str, ...]:
        if len(specialists) != len(set(specialists)) or set(specialists) - SPECIALIST_NAMES:
            raise ValueError("observed_specialists_must_be_unique_and_allowlisted")
        return specialists


class EvalReceipt(EvalModel):
    schema_version: str = Field(pattern=r"^1\.(0|1)$")
    suite_version: str = Field(min_length=1, max_length=40)
    suite_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    repository_sha: str = Field(pattern=r"^[a-f0-9]{40}$")
    source_fixture_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    scenario_generator_version: str = Field(min_length=1, max_length=40)
    random_seed: int = Field(ge=0, le=2**32 - 1)
    dependency_manifest_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    prompt_manifest_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    tool_catalog_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    schema_revision: str = Field(min_length=1, max_length=80)
    environment: str = Field(pattern=r"^(test|development)$")
    threshold_policy_version: str | None = Field(default=None, max_length=60)
    threshold_policy_sha256: str | None = Field(default=None, pattern=r"^[a-f0-9]{64}$")
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    provider: str = Field(min_length=1, max_length=80)
    model: str = Field(min_length=1, max_length=120)
    resource_measurement: ResourceMeasurement | None = None
    attempt_journal_run_id: str | None = Field(default=None, pattern=r"^[a-f0-9]{32}$")
    attempt_journal_path: str | None = Field(
        default=None,
        pattern=r"^\.validation/phase11/attempt-journals/[A-Za-z0-9._-]+\.jsonl$",
        max_length=240,
    )
    attempt_journal_sha256: str | None = Field(default=None, pattern=r"^[a-f0-9]{64}$")
    attempt_journal_entries: int | None = Field(default=None, ge=0, le=1000)
    paid_provider_calls: int = Field(default=0, ge=0)
    provider_cost_usd: float = Field(default=0, ge=0, le=0)
    attempts: tuple[CaseAttempt, ...] = Field(min_length=1, max_length=1000)
    receipt_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")

    @model_validator(mode="after")
    def complete_attempt_journal_reference(self) -> EvalReceipt:
        journal_fields = (
            self.attempt_journal_run_id,
            self.attempt_journal_path,
            self.attempt_journal_sha256,
            self.attempt_journal_entries,
        )
        if any(value is not None for value in journal_fields) and any(
            value is None for value in journal_fields
        ):
            raise ValueError("attempt_journal_reference_must_be_complete")
        if self.schema_version == "1.1" and any(value is None for value in journal_fields):
            raise ValueError("attempt_journal_required_for_receipt_schema_1_1")
        return self


class SuiteSummary(EvalModel):
    suite_version: str
    suite_sha256: str
    cases: int = Field(ge=0)
    family_counts: dict[str, int]
    severity_counts: dict[str, int]
    language_counts: dict[str, int]
    expected_behavior_counts: dict[str, int]
    intent_counts: dict[str, int]
    source_surface_counts: dict[str, int]
    attack_family_counts: dict[str, int]
    route_counts: dict[str, int]
    source_role_counts: dict[str, int]
    allowed_tool_counts: dict[str, int]
    required_tool_counts: dict[str, int]
    forbidden_tool_counts: dict[str, int]


GraderResult.model_rebuild()
