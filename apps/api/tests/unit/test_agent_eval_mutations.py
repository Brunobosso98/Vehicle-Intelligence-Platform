from datetime import UTC, datetime

import pytest

from vehicle_platform.agent_evaluation.mutations import (
    MutationName,
    MutationPreconditionError,
    ThreatFact,
    ThreatFixture,
    apply_mutation,
    low_trust_rag_mutation,
    revoked_capability_mutation,
)

NOW = datetime(2026, 11, 23, tzinfo=UTC)
CHECKSUM = "a" * 64


@pytest.mark.parametrize(
    ("mutation", "fixture"),
    [
        (
            "inject_low_trust_text",
            ThreatFixture(
                fixture_id="community-doc",
                surface="knowledge_document",
                trust_tier="TIER_4_COMMUNITY",
                source_text="Synthetic N55 community excerpt.",
            ),
        ),
        (
            "swap_document_version",
            ThreatFixture(
                fixture_id="versioned-doc",
                surface="document_version",
                document_version="v1",
                approved_document_version="v1",
                unapproved_document_version="v2",
            ),
        ),
        (
            "change_tool_result_error",
            ThreatFixture(fixture_id="tool-result", surface="tool_result"),
        ),
        (
            "rekey_vehicle_id",
            ThreatFixture(
                fixture_id="vehicle-scope",
                surface="vehicle_scope",
                vehicle_id="vehicle-a",
                expected_vehicle_id="vehicle-a",
            ),
        ),
        (
            "reorder_facts",
            ThreatFixture(
                fixture_id="telemetry-order",
                surface="telemetry",
                facts=(
                    ThreatFact(fact_id="a", observed_at=NOW, value=1000, unit="rpm"),
                    ThreatFact(fact_id="b", observed_at=NOW, value=2000, unit="rpm"),
                    ThreatFact(fact_id="c", observed_at=NOW, value=3000, unit="rpm"),
                ),
            ),
        ),
        (
            "add_future_sample",
            ThreatFixture(
                fixture_id="telemetry-cutoff",
                surface="telemetry",
                as_of=NOW,
                facts=(ThreatFact(fact_id="past", observed_at=NOW, value=1000, unit="rpm"),),
            ),
        ),
        (
            "revoke_token",
            ThreatFixture(
                fixture_id="capability",
                surface="authorization",
                token_active=True,
            ),
        ),
        (
            "delay_tool_response",
            ThreatFixture(fixture_id="transport", surface="mcp_transport"),
        ),
        (
            "tamper_source_role",
            ThreatFixture(
                fixture_id="prediction-source-role",
                surface="artifact",
                source_role="synthetic",
            ),
        ),
        (
            "corrupt_checksum",
            ThreatFixture(
                fixture_id="artifact",
                surface="artifact",
                artifact_sha256=CHECKSUM,
            ),
        ),
        (
            "distort_unit",
            ThreatFixture(
                fixture_id="numeric-fact",
                surface="numeric_fact",
                numeric_value=2.0,
                numeric_unit="bar",
            ),
        ),
    ],
)
def test_allowlisted_mutations_are_seeded_bounded_and_source_hashed(
    mutation: MutationName, fixture: ThreatFixture
) -> None:
    first = apply_mutation(fixture, mutation, seed=17)
    replay = apply_mutation(fixture, mutation, seed=17)

    assert first == replay
    assert first.scenario.seed == 17
    assert first.scenario.mutation == mutation
    assert first.scenario.mutation_version == 2
    assert first.original_fixture_sha256 == first.scenario.original_source_sha256
    assert first.mutated_fixture_sha256 != first.original_fixture_sha256
    assert first.mutated_fields
    assert fixture != first.fixture


@pytest.mark.parametrize(
    ("mutation", "fixture", "reason"),
    [
        (
            "inject_low_trust_text",
            ThreatFixture(
                fixture_id="trusted-doc",
                surface="knowledge_document",
                trust_tier="TIER_1_AUTHORITATIVE",
                source_text="Trusted synthetic document.",
            ),
            "low_trust_knowledge_text_required",
        ),
        (
            "rekey_vehicle_id",
            ThreatFixture(
                fixture_id="vehicle-scope",
                surface="vehicle_scope",
                vehicle_id="vehicle-a",
                expected_vehicle_id="vehicle-b",
            ),
            "vehicle_fixture_must_start_with_its_expected_owner",
        ),
        (
            "revoke_token",
            ThreatFixture(
                fixture_id="revoked",
                surface="authorization",
                token_active=False,
            ),
            "active_synthetic_capability_required",
        ),
        (
            "tamper_source_role",
            ThreatFixture(
                fixture_id="wrong-source-role",
                surface="artifact",
                source_role="real_vehicle",
            ),
            "synthetic_artifact_source_role_required",
        ),
        (
            "corrupt_checksum",
            ThreatFixture(fixture_id="not-artifact", surface="artifact"),
            "content_hashed_artifact_required",
        ),
    ],
)
def test_mutations_reject_missing_or_invalid_preconditions(
    mutation: MutationName, fixture: ThreatFixture, reason: str
) -> None:
    with pytest.raises(MutationPreconditionError, match=reason):
        apply_mutation(fixture, mutation, seed=0)


def test_future_sample_is_after_cutoff_and_transport_delay_is_capped() -> None:
    telemetry = ThreatFixture(
        fixture_id="cutoff",
        surface="telemetry",
        as_of=NOW,
    )
    future = apply_mutation(telemetry, "add_future_sample", seed=4)
    assert future.fixture.facts[0].observed_at > NOW

    transport = ThreatFixture(fixture_id="delay", surface="mcp_transport")
    delayed = apply_mutation(transport, "delay_tool_response", seed=2**32 - 1)
    assert delayed.fixture.delay_ms is not None
    assert 1_000 <= delayed.fixture.delay_ms <= 30_000


def test_mutation_seed_is_range_checked() -> None:
    fixture = ThreatFixture(fixture_id="delay", surface="mcp_transport")
    with pytest.raises(ValueError, match="mutation_seed_out_of_range"):
        apply_mutation(fixture, "delay_tool_response", seed=-1)


def test_low_trust_rag_mutation_is_a_frozen_reproducible_fixture() -> None:
    first = low_trust_rag_mutation()
    replay = low_trust_rag_mutation()

    assert first == replay
    assert first.scenario.mutation == "inject_low_trust_text"
    assert first.scenario.seed == 0
    assert first.fixture.surface == "knowledge_document"
    assert first.fixture.trust_tier == "TIER_4_COMMUNITY"
    assert "ignore prior instructions" in (first.fixture.source_text or "").casefold()
    assert first.original_fixture_sha256 != first.mutated_fixture_sha256


def test_revoked_capability_mutation_is_a_frozen_active_to_revoked_fixture() -> None:
    first = revoked_capability_mutation()
    replay = revoked_capability_mutation()

    assert first == replay
    assert first.scenario.mutation == "revoke_token"
    assert first.scenario.seed == 0
    assert first.fixture.surface == "authorization"
    assert first.fixture.token_active is False
    assert first.expected_defense.value == "expect_revoked_capability_denied"


def test_mutation_input_growth_stays_within_declared_fixture_limits() -> None:
    large_document = ThreatFixture(
        fixture_id="bounded-community-document",
        surface="knowledge_document",
        trust_tier="TIER_4_COMMUNITY",
        source_text="x" * 20_000,
    )
    with pytest.raises(MutationPreconditionError, match="low_trust_text_limit_exceeded"):
        apply_mutation(large_document, "inject_low_trust_text", seed=0)

    full_telemetry = ThreatFixture(
        fixture_id="bounded-telemetry",
        surface="telemetry",
        as_of=NOW,
        facts=tuple(
            ThreatFact(
                fact_id=f"sample-{index}",
                observed_at=NOW,
                value=float(index),
                unit="rpm",
            )
            for index in range(64)
        ),
    )
    with pytest.raises(MutationPreconditionError, match="telemetry_fact_limit_exceeded"):
        apply_mutation(full_telemetry, "add_future_sample", seed=0)


def test_fixture_rejects_naive_timestamps_and_duplicate_fact_ids() -> None:
    with pytest.raises(ValueError, match="threat_fixture_timestamps_must_be_timezone_aware"):
        ThreatFixture(
            fixture_id="naive-cutoff",
            surface="telemetry",
            as_of=datetime(2026, 11, 23),
        )

    fact = ThreatFact(fact_id="duplicate", observed_at=NOW, value=1, unit="rpm")
    with pytest.raises(ValueError, match="threat_fixture_fact_ids_must_be_unique"):
        ThreatFixture(
            fixture_id="duplicate-facts",
            surface="telemetry",
            facts=(fact, fact),
        )


@pytest.mark.parametrize(
    ("mutation", "fixture", "reason"),
    [
        (
            "swap_document_version",
            ThreatFixture(fixture_id="wrong-version-surface", surface="tool_result"),
            "approved_and_distinct_unapproved_versions_required",
        ),
        (
            "change_tool_result_error",
            ThreatFixture(fixture_id="wrong-error-surface", surface="telemetry"),
            "tool_result_surface_required",
        ),
        (
            "rekey_vehicle_id",
            ThreatFixture(fixture_id="missing-owner", surface="vehicle_scope"),
            "vehicle_scope_with_expected_owner_required",
        ),
        (
            "reorder_facts",
            ThreatFixture(
                fixture_id="one-fact",
                surface="telemetry",
                facts=(ThreatFact(fact_id="only", observed_at=NOW, value=1, unit="rpm"),),
            ),
            "two_or_more_telemetry_facts_required",
        ),
        (
            "add_future_sample",
            ThreatFixture(fixture_id="missing-cutoff", surface="telemetry"),
            "telemetry_cutoff_required",
        ),
        (
            "delay_tool_response",
            ThreatFixture(fixture_id="wrong-transport-surface", surface="tool_result"),
            "mcp_transport_surface_required",
        ),
        (
            "distort_unit",
            ThreatFixture(
                fixture_id="missing-numeric-value", surface="numeric_fact", numeric_unit="bar"
            ),
            "typed_numeric_fact_required",
        ),
    ],
)
def test_mutations_reject_surface_and_fixture_precondition_mismatches(
    mutation: MutationName, fixture: ThreatFixture, reason: str
) -> None:
    with pytest.raises(MutationPreconditionError, match=reason):
        apply_mutation(fixture, mutation, seed=0)


def test_mutations_resolve_seeded_identifier_collisions_deterministically() -> None:
    vehicle = ThreatFixture(
        fixture_id="collision-owner",
        surface="vehicle_scope",
        vehicle_id="synthetic-foreign-00000000",
        expected_vehicle_id="synthetic-foreign-00000000",
    )
    rekeyed = apply_mutation(vehicle, "rekey_vehicle_id", seed=0)
    assert rekeyed.fixture.vehicle_id == "synthetic-foreign-00000001"

    cutoff = ThreatFixture(
        fixture_id="collision-cutoff",
        surface="telemetry",
        as_of=NOW,
        facts=(
            ThreatFact(
                fact_id="future-00000000",
                observed_at=NOW,
                value=1,
                unit="rpm",
            ),
        ),
    )
    with pytest.raises(MutationPreconditionError, match="future_sample_id_must_be_unique"):
        apply_mutation(cutoff, "add_future_sample", seed=0)
