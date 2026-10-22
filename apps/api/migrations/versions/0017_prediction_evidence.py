"""Persist immutable Phase 9E evidence bundles and source-verification audits."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0017"
down_revision = "0016"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "prediction_evidence_bundles",
        sa.Column("id", postgresql.UUID(), primary_key=True),
        sa.Column(
            "receipt_id",
            postgresql.UUID(),
            sa.ForeignKey("prediction_receipts.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("schema_version", sa.String(80), nullable=False),
        sa.Column("projection_version", sa.String(80), nullable=False),
        sa.Column("verifier_policy_version", sa.String(80), nullable=False),
        sa.Column("logical_fingerprint", sa.String(64), nullable=False, unique=True),
        sa.Column("content_checksum", sa.String(64), nullable=False),
        sa.Column("provenance_manifest_checksum", sa.String(64), nullable=False),
        sa.Column("result_type", sa.String(24), nullable=False),
        sa.Column("horizon", sa.String(32), nullable=False),
        sa.Column("source_role", sa.String(32), nullable=False),
        sa.Column("effective_cutoff", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completeness", sa.String(16), nullable=False),
        sa.Column("integrity", sa.String(48), nullable=False),
        sa.Column("bundle_body", postgresql.JSONB(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.UniqueConstraint(
            "receipt_id", "schema_version", name="uq_prediction_evidence_receipt_schema"
        ),
        sa.CheckConstraint(
            "length(logical_fingerprint)=64", name="ck_prediction_evidence_fingerprint"
        ),
        sa.CheckConstraint(
            "length(content_checksum)=64 AND length(provenance_manifest_checksum)=64",
            name="ck_prediction_evidence_checksums",
        ),
        sa.CheckConstraint(
            "result_type IN ('next_pull','anomaly')", name="ck_prediction_evidence_kind"
        ),
        sa.CheckConstraint(
            "(result_type='next_pull' AND horizon='NEXT_PULL') OR (result_type='anomaly' AND horizon='AFTER_PULL_OFFLINE')",
            name="ck_prediction_evidence_horizon",
        ),
        sa.CheckConstraint(
            "source_role IN ('synthetic','real_vehicle','imported','imported_fixture')",
            name="ck_prediction_evidence_role",
        ),
        sa.CheckConstraint(
            "completeness IN ('COMPLETE','PARTIAL','ABSTAINED')",
            name="ck_prediction_evidence_completeness",
        ),
        sa.CheckConstraint(
            "integrity IN ('VERIFIED','VERIFIED_SNAPSHOT_ARTIFACT_UNAVAILABLE','FAILED_SOURCE_MISMATCH','NOT_VERIFIABLE','UNSUPPORTED_SCHEMA')",
            name="ck_prediction_evidence_integrity",
        ),
        sa.CheckConstraint(
            "jsonb_typeof(bundle_body)='object' AND octet_length(bundle_body::text)<=65536",
            name="ck_prediction_evidence_body_bound",
        ),
    )
    op.create_index(
        "ix_prediction_evidence_receipt_created",
        "prediction_evidence_bundles",
        ["receipt_id", "created_at"],
    )

    op.create_table(
        "prediction_evidence_sources",
        sa.Column(
            "evidence_id",
            postgresql.UUID(),
            sa.ForeignKey("prediction_evidence_bundles.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("source_kind", sa.String(32), nullable=False),
        sa.Column("source_entity_id", postgresql.UUID(), nullable=False),
        sa.Column("source_checksum", sa.String(64), nullable=False),
        sa.Column("source_schema_checksum", sa.String(64)),
        sa.PrimaryKeyConstraint("evidence_id", "source_kind"),
        sa.CheckConstraint(
            "source_kind IN ('prediction_receipt','serving_binding','approval_event','feature_set','feature_version','model_version','detector_version','anomaly_run','anomaly_finding','reference_dataset')",
            name="ck_prediction_evidence_source_kind",
        ),
        sa.CheckConstraint(
            "length(source_checksum)=64 AND (source_schema_checksum IS NULL OR length(source_schema_checksum)=64)",
            name="ck_prediction_evidence_source_hash",
        ),
    )
    op.create_table(
        "prediction_evidence_nodes",
        sa.Column("evidence_id", postgresql.UUID(), nullable=False),
        sa.Column("node_id", sa.String(80), nullable=False),
        sa.Column("source_kind", sa.String(32), nullable=False),
        sa.Column("source_entity_id", postgresql.UUID(), nullable=False),
        sa.Column("node_type", sa.String(32), nullable=False),
        sa.Column("trust_role", sa.String(32), nullable=False),
        sa.Column("projection_class", sa.String(32), nullable=False),
        sa.Column("valid_from", sa.DateTime(timezone=True)),
        sa.Column("valid_through", sa.DateTime(timezone=True)),
        sa.PrimaryKeyConstraint("evidence_id", "node_id"),
        sa.ForeignKeyConstraint(
            ["evidence_id", "source_kind"],
            ["prediction_evidence_sources.evidence_id", "prediction_evidence_sources.source_kind"],
            ondelete="RESTRICT",
        ),
        sa.CheckConstraint(
            "node_type IN ('PREDICTION_RECEIPT','SERVING_BINDING','APPROVAL_EVENT','FEATURE_SET','FEATURE_VERSION','MODEL_VERSION','DETECTOR_VERSION','ANOMALY_RUN','ANOMALY_FINDING','REFERENCE_DATASET')",
            name="ck_prediction_evidence_node_type",
        ),
        sa.CheckConstraint(
            "trust_role IN ('IMMUTABLE_SOURCE','VERSIONED_SOURCE','DERIVED_SNAPSHOT')",
            name="ck_prediction_evidence_node_trust",
        ),
        sa.CheckConstraint(
            "projection_class IN ('OPERATOR_RESULT','INTERNAL_LINEAGE','INTERNAL_SOURCE')",
            name="ck_prediction_evidence_node_projection",
        ),
        sa.CheckConstraint(
            "valid_from IS NULL OR valid_through IS NULL OR valid_from<=valid_through",
            name="ck_prediction_evidence_node_times",
        ),
    )
    op.create_table(
        "prediction_evidence_edges",
        sa.Column("evidence_id", postgresql.UUID(), nullable=False),
        sa.Column("edge_id", sa.String(80), nullable=False),
        sa.Column("source_node_id", sa.String(80), nullable=False),
        sa.Column("target_node_id", sa.String(80), nullable=False),
        sa.Column("relation", sa.String(32), nullable=False),
        sa.PrimaryKeyConstraint("evidence_id", "edge_id"),
        sa.ForeignKeyConstraint(
            ["evidence_id", "source_node_id"],
            ["prediction_evidence_nodes.evidence_id", "prediction_evidence_nodes.node_id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["evidence_id", "target_node_id"],
            ["prediction_evidence_nodes.evidence_id", "prediction_evidence_nodes.node_id"],
            ondelete="RESTRICT",
        ),
        sa.CheckConstraint(
            "source_node_id<>target_node_id", name="ck_prediction_evidence_edge_not_self"
        ),
        sa.CheckConstraint(
            "relation IN ('DERIVED_FROM','SCORED_WITH','SELECTED_BY','OBSERVED_IN','SUPPORTED_BY','COMPARED_AGAINST','MEASURED_AT','LIMITED_BY')",
            name="ck_prediction_evidence_edge_relation",
        ),
    )
    op.create_table(
        "prediction_evidence_facts",
        sa.Column("evidence_id", postgresql.UUID(), nullable=False),
        sa.Column("fact_id", sa.String(80), nullable=False),
        sa.Column("source_node_id", sa.String(80), nullable=False),
        sa.Column("fact_type", sa.String(32), nullable=False),
        sa.Column("fact_key", sa.String(160), nullable=False),
        sa.Column("fact_value", postgresql.JSONB()),
        sa.Column("fact_unit", sa.String(48)),
        sa.Column("cutoff", sa.DateTime(timezone=True), nullable=False),
        sa.Column("cutoff_eligible", sa.Boolean(), nullable=False),
        sa.Column("quality", sa.String(24), nullable=False),
        sa.Column("fact_body", postgresql.JSONB(), nullable=False),
        sa.PrimaryKeyConstraint("evidence_id", "fact_id"),
        sa.ForeignKeyConstraint(
            ["evidence_id", "source_node_id"],
            ["prediction_evidence_nodes.evidence_id", "prediction_evidence_nodes.node_id"],
            ondelete="RESTRICT",
        ),
        sa.CheckConstraint(
            "fact_type IN ('SOURCE_MEASUREMENT','COMPUTED_FEATURE','MODEL_OUTPUT','STATISTICAL_REFERENCE','CONTEXT_DESCRIPTOR','QUALITY_INDICATOR','INTERPRETATION_LIMIT')",
            name="ck_prediction_evidence_fact_type",
        ),
        sa.CheckConstraint(
            "quality IN ('VALID','LIMITED','MISSING','INVALID','NOT_CHECKABLE')",
            name="ck_prediction_evidence_fact_quality",
        ),
        sa.CheckConstraint(
            "cutoff_eligible AND octet_length(fact_body::text)<=4096",
            name="ck_prediction_evidence_fact_bound",
        ),
    )
    op.create_table(
        "prediction_evidence_gaps",
        sa.Column(
            "evidence_id",
            postgresql.UUID(),
            sa.ForeignKey("prediction_evidence_bundles.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column("gap_code", sa.String(48), nullable=False),
        sa.Column("source_node_id", sa.String(80)),
        sa.Column("reason_code", sa.String(80)),
        sa.PrimaryKeyConstraint("evidence_id", "ordinal"),
        sa.ForeignKeyConstraint(
            ["evidence_id", "source_node_id"],
            ["prediction_evidence_nodes.evidence_id", "prediction_evidence_nodes.node_id"],
            ondelete="RESTRICT",
        ),
        sa.CheckConstraint("ordinal BETWEEN 0 AND 15", name="ck_prediction_evidence_gap_ordinal"),
        sa.CheckConstraint(
            "gap_code IN ('NO_FEATURE_SET','INPUT_ABSTAINED','SIGNAL_UNAVAILABLE','FEATURE_NOT_YET_OBSERVED','LOW_QUALITY','REFERENCE_INSUFFICIENT','CONTEXT_INCOMPATIBLE','UNKNOWN_CONFIG','MODEL_ARTIFACT_UNAVAILABLE','PROVENANCE_MISMATCH','EVIDENCE_SOURCE_MISSING','SOURCE_SCHEMA_MISMATCH','CUTOFF_MISMATCH','UNSUPPORTED_SOURCE','AMBIGUOUS_ASSOCIATION','INCOMPLETE_PROJECTION','UNVERIFIED_SOURCE')",
            name="ck_prediction_evidence_gap_code",
        ),
    )
    op.create_table(
        "prediction_evidence_verification_audits",
        sa.Column(
            "id", postgresql.UUID(), primary_key=True, server_default=sa.text("gen_random_uuid()")
        ),
        sa.Column(
            "evidence_id",
            postgresql.UUID(),
            sa.ForeignKey("prediction_evidence_bundles.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("integrity", sa.String(48), nullable=False),
        sa.Column("reason_codes", postgresql.ARRAY(sa.String(80)), nullable=False),
        sa.Column("source_count", sa.Integer(), nullable=False),
        sa.Column(
            "checked_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.CheckConstraint(
            "integrity IN ('VERIFIED','VERIFIED_SNAPSHOT_ARTIFACT_UNAVAILABLE','FAILED_SOURCE_MISMATCH','NOT_VERIFIABLE','UNSUPPORTED_SCHEMA')",
            name="ck_prediction_evidence_audit_integrity",
        ),
        sa.CheckConstraint(
            "source_count BETWEEN 0 AND 32 AND cardinality(reason_codes)<=16",
            name="ck_prediction_evidence_audit_bounds",
        ),
    )
    op.create_index(
        "ix_prediction_evidence_audits_evidence_checked",
        "prediction_evidence_verification_audits",
        ["evidence_id", "checked_at"],
    )

    op.execute(
        "CREATE FUNCTION reject_immutable_prediction_evidence_mutation() RETURNS trigger "
        "LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'Phase 9E evidence records are immutable'; END; $$"
    )
    for table in (
        "prediction_evidence_bundles",
        "prediction_evidence_sources",
        "prediction_evidence_nodes",
        "prediction_evidence_edges",
        "prediction_evidence_facts",
        "prediction_evidence_gaps",
        "prediction_evidence_verification_audits",
    ):
        op.execute(
            f"CREATE TRIGGER trg_{table}_immutable BEFORE UPDATE OR DELETE ON {table} "
            "FOR EACH ROW EXECUTE FUNCTION reject_immutable_prediction_evidence_mutation()"
        )


def downgrade() -> None:
    for table in (
        "prediction_evidence_bundles",
        "prediction_evidence_sources",
        "prediction_evidence_nodes",
        "prediction_evidence_edges",
        "prediction_evidence_facts",
        "prediction_evidence_gaps",
        "prediction_evidence_verification_audits",
    ):
        op.execute(f"DROP TRIGGER IF EXISTS trg_{table}_immutable ON {table}")
    op.drop_index(
        "ix_prediction_evidence_audits_evidence_checked",
        table_name="prediction_evidence_verification_audits",
    )
    op.drop_table("prediction_evidence_verification_audits")
    op.drop_table("prediction_evidence_gaps")
    op.drop_table("prediction_evidence_facts")
    op.drop_table("prediction_evidence_edges")
    op.drop_table("prediction_evidence_nodes")
    op.drop_table("prediction_evidence_sources")
    op.drop_index(
        "ix_prediction_evidence_receipt_created", table_name="prediction_evidence_bundles"
    )
    op.drop_table("prediction_evidence_bundles")
    op.execute("DROP FUNCTION IF EXISTS reject_immutable_prediction_evidence_mutation()")
