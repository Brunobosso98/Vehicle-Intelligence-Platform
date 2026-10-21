"""Add controlled prediction approvals, activation events and immutable receipts."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0016"
down_revision = "0015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "prediction_serving_bindings",
        sa.Column(
            "id", postgresql.UUID(), primary_key=True, server_default=sa.text("gen_random_uuid()")
        ),
        sa.Column("result_kind", sa.String(24), nullable=False),
        sa.Column("subject_key", sa.String(120), nullable=False),
        sa.Column("source_role", sa.String(32), nullable=False),
        sa.Column("environment", sa.String(20), nullable=False),
        sa.Column("scope", sa.String(120), nullable=False),
        sa.Column(
            "model_version_id",
            postgresql.UUID(),
            sa.ForeignKey("ml_model_versions.id", ondelete="RESTRICT"),
        ),
        sa.Column(
            "detector_version_id",
            postgresql.UUID(),
            sa.ForeignKey("anomaly_detector_versions.id", ondelete="RESTRICT"),
        ),
        sa.Column("artifact_checksum", sa.String(64), nullable=False),
        sa.Column("feature_set_version", sa.String(80), nullable=False),
        sa.Column("feature_set_checksum", sa.String(64), nullable=False),
        sa.Column("schema_checksum", sa.String(64), nullable=False),
        sa.Column("reason", sa.String(500), nullable=False),
        sa.Column("operator_id", sa.String(120), nullable=False),
        sa.Column("review_reference", sa.String(240), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.CheckConstraint(
            "result_kind IN ('next_pull','anomaly')", name="ck_prediction_binding_kind"
        ),
        sa.CheckConstraint(
            "(result_kind='next_pull' AND model_version_id IS NOT NULL AND detector_version_id IS NULL) "
            "OR (result_kind='anomaly' AND model_version_id IS NULL AND detector_version_id IS NOT NULL)",
            name="ck_prediction_binding_version_kind",
        ),
        sa.CheckConstraint(
            "source_role IN ('synthetic','real_vehicle','imported','imported_fixture')",
            name="ck_prediction_binding_source_role",
        ),
        sa.CheckConstraint(
            "environment IN ('development','test')", name="ck_prediction_binding_environment"
        ),
        sa.CheckConstraint("length(artifact_checksum)=64", name="ck_prediction_binding_artifact"),
        sa.CheckConstraint(
            "length(feature_set_checksum)=64", name="ck_prediction_binding_feature_checksum"
        ),
        sa.CheckConstraint("length(schema_checksum)=64", name="ck_prediction_binding_schema"),
        sa.CheckConstraint(
            "length(trim(reason)) BETWEEN 20 AND 500", name="ck_prediction_binding_reason"
        ),
        sa.CheckConstraint(
            "length(trim(operator_id)) BETWEEN 2 AND 120", name="ck_prediction_binding_operator"
        ),
        sa.CheckConstraint(
            "length(trim(review_reference)) BETWEEN 5 AND 240",
            name="ck_prediction_binding_review_reference",
        ),
    )
    op.create_index(
        "ix_prediction_bindings_scope",
        "prediction_serving_bindings",
        ["result_kind", "subject_key", "source_role", "environment", "scope"],
    )
    op.create_index(
        "ix_prediction_bindings_model_version",
        "prediction_serving_bindings",
        ["model_version_id"],
        postgresql_where=sa.text("model_version_id IS NOT NULL"),
    )
    op.create_index(
        "ix_prediction_bindings_detector_version",
        "prediction_serving_bindings",
        ["detector_version_id"],
        postgresql_where=sa.text("detector_version_id IS NOT NULL"),
    )

    op.create_table(
        "prediction_serving_events",
        sa.Column(
            "id", postgresql.UUID(), primary_key=True, server_default=sa.text("gen_random_uuid()")
        ),
        sa.Column("event_number", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column(
            "binding_id",
            postgresql.UUID(),
            sa.ForeignKey("prediction_serving_bindings.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "related_binding_id",
            postgresql.UUID(),
            sa.ForeignKey("prediction_serving_bindings.id", ondelete="RESTRICT"),
        ),
        sa.Column("slot_key", sa.String(64), nullable=False),
        sa.Column("event_type", sa.String(24), nullable=False),
        sa.Column("reason", sa.String(500), nullable=False),
        sa.Column("operator_id", sa.String(120), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.UniqueConstraint("event_number", name="uq_prediction_serving_event_number"),
        sa.CheckConstraint(
            "event_type IN ('APPROVED','ACTIVATED','REVOKED','SUPERSEDED','ROLLED_BACK')",
            name="ck_prediction_serving_event_type",
        ),
        sa.CheckConstraint("length(slot_key)=64", name="ck_prediction_serving_event_slot"),
        sa.CheckConstraint(
            "length(trim(reason)) BETWEEN 8 AND 500", name="ck_prediction_event_reason"
        ),
        sa.CheckConstraint(
            "length(trim(operator_id)) BETWEEN 2 AND 120", name="ck_prediction_event_operator"
        ),
    )
    op.create_index(
        "ix_prediction_serving_events_binding_order",
        "prediction_serving_events",
        ["binding_id", "event_number"],
    )
    op.create_index(
        "ix_prediction_serving_events_slot_order",
        "prediction_serving_events",
        ["slot_key", "event_number"],
    )

    op.create_table(
        "prediction_receipts",
        sa.Column(
            "id", postgresql.UUID(), primary_key=True, server_default=sa.text("gen_random_uuid()")
        ),
        sa.Column("request_fingerprint", sa.String(64), nullable=False, unique=True),
        sa.Column("client_key_hash", sa.String(64), unique=True),
        sa.Column("schema_version", sa.String(80), nullable=False),
        sa.Column("result_kind", sa.String(24), nullable=False),
        sa.Column("subject_key", sa.String(120), nullable=False),
        sa.Column("horizon", sa.String(32), nullable=False),
        sa.Column("status", sa.String(48), nullable=False),
        sa.Column("reason_code", sa.String(80)),
        sa.Column(
            "binding_id",
            postgresql.UUID(),
            sa.ForeignKey("prediction_serving_bindings.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "binding_event_id",
            postgresql.UUID(),
            sa.ForeignKey("prediction_serving_events.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "model_version_id",
            postgresql.UUID(),
            sa.ForeignKey("ml_model_versions.id", ondelete="RESTRICT"),
        ),
        sa.Column(
            "detector_version_id",
            postgresql.UUID(),
            sa.ForeignKey("anomaly_detector_versions.id", ondelete="RESTRICT"),
        ),
        sa.Column(
            "anomaly_run_id",
            postgresql.UUID(),
            sa.ForeignKey("anomaly_detection_runs.id", ondelete="RESTRICT"),
        ),
        sa.Column(
            "anomaly_finding_id",
            postgresql.UUID(),
            sa.ForeignKey("anomaly_findings.id", ondelete="RESTRICT"),
        ),
        sa.Column(
            "pull_id",
            postgresql.UUID(),
            sa.ForeignKey("pulls.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "feature_set_id",
            postgresql.UUID(),
            sa.ForeignKey("feature_sets.id", ondelete="RESTRICT"),
        ),
        sa.Column("feature_set_version", sa.String(80)),
        sa.Column("feature_set_checksum", sa.String(64)),
        sa.Column("feature_provenance_checksum", sa.String(64)),
        sa.Column("artifact_checksum", sa.String(64), nullable=False),
        sa.Column("requested_cutoff", sa.DateTime(timezone=True), nullable=False),
        sa.Column("effective_cutoff", sa.DateTime(timezone=True)),
        sa.Column("source_role", sa.String(32), nullable=False),
        sa.Column("engineering_validation_score", sa.Float()),
        sa.Column("anomaly_score", sa.Float()),
        sa.Column("threshold", sa.Float()),
        sa.Column("decision", sa.String(24)),
        sa.Column("coverage", sa.Float(), nullable=False),
        sa.Column("quality_summary", postgresql.JSONB(), nullable=False),
        sa.Column("response_body", postgresql.JSONB(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.CheckConstraint(
            "length(request_fingerprint)=64", name="ck_prediction_receipt_fingerprint"
        ),
        sa.CheckConstraint(
            "client_key_hash IS NULL OR length(client_key_hash)=64",
            name="ck_prediction_receipt_client_key",
        ),
        sa.CheckConstraint(
            "result_kind IN ('next_pull','anomaly')", name="ck_prediction_receipt_kind"
        ),
        sa.CheckConstraint(
            "(result_kind='next_pull' AND model_version_id IS NOT NULL AND detector_version_id IS NULL "
            "AND anomaly_run_id IS NULL AND anomaly_finding_id IS NULL AND horizon='NEXT_PULL') OR "
            "(result_kind='anomaly' AND model_version_id IS NULL AND detector_version_id IS NOT NULL "
            "AND ((anomaly_run_id IS NOT NULL AND anomaly_finding_id IS NOT NULL) OR "
            "(anomaly_run_id IS NULL AND anomaly_finding_id IS NULL AND feature_set_id IS NULL "
            "AND status='ABSTAINED_INSUFFICIENT_SIGNAL')) "
            "AND horizon='AFTER_PULL_OFFLINE')",
            name="ck_prediction_receipt_version_kind",
        ),
        sa.CheckConstraint(
            "status IN ('READY_SCORE','ABSTAINED_INSUFFICIENT_SIGNAL','ABSTAINED_LOW_QUALITY',"
            "'ABSTAINED_INSUFFICIENT_REFERENCE','ABSTAINED_INCOMPATIBLE_CONTEXT',"
            "'ABSTAINED_UNSUPPORTED_SOURCE','ABSTAINED_CUTOFF')",
            name="ck_prediction_receipt_status",
        ),
        sa.CheckConstraint(
            "source_role IN ('synthetic','real_vehicle','imported','imported_fixture')",
            name="ck_prediction_receipt_source_role",
        ),
        sa.CheckConstraint(
            "length(artifact_checksum)=64 AND (feature_set_checksum IS NULL OR length(feature_set_checksum)=64) "
            "AND (feature_provenance_checksum IS NULL OR length(feature_provenance_checksum)=64)",
            name="ck_prediction_receipt_hashes",
        ),
        sa.CheckConstraint("coverage BETWEEN 0 AND 1", name="ck_prediction_receipt_coverage"),
        sa.CheckConstraint(
            "(status='READY_SCORE' AND decision IS NOT NULL AND "
            "((result_kind='next_pull' AND engineering_validation_score IS NOT NULL AND anomaly_score IS NULL) "
            "OR (result_kind='anomaly' AND anomaly_score IS NOT NULL AND engineering_validation_score IS NULL))) "
            "OR (status<>'READY_SCORE' AND decision IS NULL AND engineering_validation_score IS NULL AND anomaly_score IS NULL)",
            name="ck_prediction_receipt_score_state",
        ),
        sa.CheckConstraint(
            "(engineering_validation_score IS NULL OR engineering_validation_score BETWEEN 0 AND 1) "
            "AND (anomaly_score IS NULL OR (anomaly_score >= 0 AND anomaly_score < 'Infinity'::float8)) "
            "AND (threshold IS NULL OR (threshold >= 0 AND threshold < 'Infinity'::float8))",
            name="ck_prediction_receipt_finite_scores",
        ),
        sa.CheckConstraint(
            "octet_length(quality_summary::text) <= 4096 AND octet_length(response_body::text) <= 16384",
            name="ck_prediction_receipt_payload_bounds",
        ),
    )
    op.create_index(
        "ix_prediction_receipts_pull_cutoff",
        "prediction_receipts",
        ["pull_id", "requested_cutoff"],
    )
    op.create_index(
        "ix_prediction_receipts_binding_created",
        "prediction_receipts",
        ["binding_id", "created_at"],
    )

    op.execute(
        "CREATE FUNCTION reject_immutable_prediction_record_mutation() RETURNS trigger "
        "LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'Phase 9D prediction record is immutable'; "
        "END; $$"
    )
    for table in (
        "prediction_serving_bindings",
        "prediction_serving_events",
        "prediction_receipts",
    ):
        op.execute(
            f"CREATE TRIGGER trg_{table}_immutable BEFORE UPDATE OR DELETE ON {table} "
            "FOR EACH ROW EXECUTE FUNCTION reject_immutable_prediction_record_mutation()"
        )


def downgrade() -> None:
    for table in (
        "prediction_receipts",
        "prediction_serving_events",
        "prediction_serving_bindings",
    ):
        op.execute(f"DROP TRIGGER IF EXISTS trg_{table}_immutable ON {table}")
    op.execute("DROP FUNCTION IF EXISTS reject_immutable_prediction_record_mutation()")
    op.drop_index("ix_prediction_receipts_binding_created", table_name="prediction_receipts")
    op.drop_index("ix_prediction_receipts_pull_cutoff", table_name="prediction_receipts")
    op.drop_table("prediction_receipts")
    op.drop_index("ix_prediction_serving_events_slot_order", table_name="prediction_serving_events")
    op.drop_index(
        "ix_prediction_serving_events_binding_order", table_name="prediction_serving_events"
    )
    op.drop_table("prediction_serving_events")
    op.drop_index(
        "ix_prediction_bindings_detector_version", table_name="prediction_serving_bindings"
    )
    op.drop_index("ix_prediction_bindings_model_version", table_name="prediction_serving_bindings")
    op.drop_index("ix_prediction_bindings_scope", table_name="prediction_serving_bindings")
    op.drop_table("prediction_serving_bindings")
