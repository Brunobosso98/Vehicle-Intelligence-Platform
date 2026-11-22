from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

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


class DirectProbeEvidence(EvalModel):
    probe_type: Literal[
        "mcp_capability",
        "mcp_revoked_capability",
        "operator_cli",
        "knowledge_retrieval",
    ]
    target: str = Field(min_length=1, max_length=100)
    visible_tools: tuple[str, ...] = Field(default=(), max_length=64)
    call_rejected: bool
    output_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    output_summary: dict[str, str | int | float | bool | None] = Field(
        default_factory=dict, max_length=16
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
    tool_schema_blocked: bool = False
    mcp_auth_blocked: bool = False
    grounding_blocked: bool = False
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
        pattern=r"^(mcp_unavailable|dependency_unavailable|run_timeout|provider_invalid_output)$",
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

    @field_validator("expected_facts")
    @classmethod
    def unique_fact_paths(cls, facts: tuple[OracleFact, ...]) -> tuple[OracleFact, ...]:
        paths = [fact.path for fact in facts]
        if len(paths) != len(set(paths)):
            raise ValueError("oracle fact paths must be unique")
        return facts

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
    tool_trace: tuple[ToolTrace, ...] = Field(default=(), max_length=32)
    direct_probe: DirectProbeEvidence | None = None
    tool_trace_sha256: str | None = Field(default=None, pattern=r"^[a-f0-9]{64}$")
    sse_event_types: tuple[str, ...] = Field(default=(), max_length=128)
    model_turn_count: int | None = Field(default=None, ge=0, le=16)
    mcp_call_count: int = Field(default=0, ge=0, le=32)
    forbidden_action_count: int = Field(default=0, ge=0, le=1000)
    source_digest_before: str | None = Field(default=None, pattern=r"^[a-f0-9]{64}$")
    source_digest_after: str | None = Field(default=None, pattern=r"^[a-f0-9]{64}$")
    elapsed_ms: int | None = Field(default=None, ge=0)
    error_category: str | None = Field(default=None, max_length=80)
    reasons: tuple[str, ...] = Field(default=(), max_length=32)


class EvalReceipt(EvalModel):
    schema_version: str = Field(pattern=r"^1\.0$")
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
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    provider: str = Field(min_length=1, max_length=80)
    model: str = Field(min_length=1, max_length=120)
    paid_provider_calls: int = Field(default=0, ge=0)
    provider_cost_usd: float = Field(default=0, ge=0, le=0)
    attempts: tuple[CaseAttempt, ...] = Field(min_length=1, max_length=1000)
    receipt_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")


class SuiteSummary(EvalModel):
    suite_version: str
    suite_sha256: str
    cases: int = Field(ge=0)
    family_counts: dict[str, int]
    severity_counts: dict[str, int]
    language_counts: dict[str, int]
    expected_behavior_counts: dict[str, int]


GraderResult.model_rebuild()
