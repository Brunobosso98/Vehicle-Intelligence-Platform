"""Persist immutable offline Phase 9G evaluation evidence."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0019"
down_revision = "0018"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "evaluation_protocols",
        sa.Column("protocol_version", sa.String(80), primary_key=True),
        sa.Column("schema_version", sa.String(80), nullable=False),
        sa.Column("protocol_checksum", sa.String(64), nullable=False, unique=True),
        sa.Column("protocol_body", postgresql.JSONB(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.CheckConstraint("length(protocol_checksum)=64", name="ck_evaluation_protocol_checksum"),
        sa.CheckConstraint(
            "jsonb_typeof(protocol_body)='object' AND octet_length(protocol_body::text)<=65536",
            name="ck_evaluation_protocol_body_bound",
        ),
    )
    op.create_table(
        "evaluation_runs",
        sa.Column("id", postgresql.UUID(), primary_key=True),
        sa.Column(
            "protocol_version",
            sa.String(80),
            sa.ForeignKey("evaluation_protocols.protocol_version", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("logical_fingerprint", sa.String(64), nullable=False, unique=True),
        sa.Column("source_role", sa.String(32), nullable=False),
        sa.Column("engineering_status", sa.String(16), nullable=False),
        sa.Column("git_sha", sa.String(40), nullable=False),
        sa.Column("dataset_fingerprint", sa.String(64), nullable=False),
        sa.Column("report_checksum", sa.String(64), nullable=False),
        sa.Column("source_manifest", postgresql.JSONB(), nullable=False),
        sa.Column("summary_body", postgresql.JSONB(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.CheckConstraint(
            "length(logical_fingerprint)=64", name="ck_evaluation_run_logical_fingerprint"
        ),
        sa.CheckConstraint(
            "length(dataset_fingerprint)=64", name="ck_evaluation_run_dataset_fingerprint"
        ),
        sa.CheckConstraint("length(report_checksum)=64", name="ck_evaluation_run_report_checksum"),
        sa.CheckConstraint("length(git_sha)=40", name="ck_evaluation_run_git_sha"),
        sa.CheckConstraint(
            "source_role IN ('synthetic','imported_fixture','imported','real_vehicle')",
            name="ck_evaluation_run_source_role",
        ),
        sa.CheckConstraint(
            "engineering_status IN ('PASS','FAIL')", name="ck_evaluation_run_status"
        ),
        sa.CheckConstraint(
            "jsonb_typeof(source_manifest)='object' AND octet_length(source_manifest::text)<=131072",
            name="ck_evaluation_run_manifest_bound",
        ),
        sa.CheckConstraint(
            "jsonb_typeof(summary_body)='object' AND octet_length(summary_body::text)<=262144",
            name="ck_evaluation_run_summary_bound",
        ),
    )
    op.create_index("ix_evaluation_runs_created", "evaluation_runs", ["created_at", "source_role"])
    op.create_table(
        "evaluation_metric_reports",
        sa.Column("id", postgresql.UUID(), primary_key=True),
        sa.Column(
            "evaluation_run_id",
            postgresql.UUID(),
            sa.ForeignKey("evaluation_runs.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("report_key", sa.String(120), nullable=False),
        sa.Column("report_checksum", sa.String(64), nullable=False),
        sa.Column("report_body", postgresql.JSONB(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.UniqueConstraint(
            "evaluation_run_id", "report_key", name="uq_evaluation_metric_report_key"
        ),
        sa.CheckConstraint(
            "length(report_checksum)=64", name="ck_evaluation_metric_report_checksum"
        ),
        sa.CheckConstraint(
            "jsonb_typeof(report_body)='object' AND octet_length(report_body::text)<=262144",
            name="ck_evaluation_metric_report_bound",
        ),
    )
    op.create_table(
        "evaluation_calibration_candidates",
        sa.Column("id", postgresql.UUID(), primary_key=True),
        sa.Column(
            "evaluation_run_id",
            postgresql.UUID(),
            sa.ForeignKey("evaluation_runs.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("task", sa.String(80), nullable=False),
        sa.Column("method", sa.String(24), nullable=False),
        sa.Column("candidate_state", sa.String(32), nullable=False),
        sa.Column(
            "model_version_id",
            postgresql.UUID(),
            sa.ForeignKey("ml_model_versions.id", ondelete="RESTRICT"),
            nullable=True,
        ),
        sa.Column("label_definition_checksum", sa.String(64), nullable=False),
        sa.Column("calibration_dataset_checksum", sa.String(64), nullable=False),
        sa.Column("artifact_checksum", sa.String(64)),
        sa.Column("artifact_bytes", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("candidate_body", postgresql.JSONB(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.UniqueConstraint(
            "evaluation_run_id", "task", "method", name="uq_evaluation_candidate_method"
        ),
        sa.CheckConstraint(
            "task IN ('NEXT_PULL_THERMAL_DEGRADATION','NEXT_PULL_PERFORMANCE_DEGRADATION','NEXT_PULL_FUEL_DEVIATION')",
            name="ck_evaluation_candidate_task",
        ),
        sa.CheckConstraint(
            "method IN ('identity','sigmoid','isotonic')", name="ck_evaluation_candidate_method"
        ),
        sa.CheckConstraint(
            "candidate_state IN ('ELIGIBLE','INSUFFICIENT_SUPPORT','SELECTED','REJECTED')",
            name="ck_evaluation_candidate_state",
        ),
        sa.CheckConstraint(
            "length(label_definition_checksum)=64", name="ck_evaluation_candidate_label_hash"
        ),
        sa.CheckConstraint(
            "length(calibration_dataset_checksum)=64", name="ck_evaluation_candidate_data_hash"
        ),
        sa.CheckConstraint(
            "artifact_checksum IS NULL OR length(artifact_checksum)=64",
            name="ck_evaluation_candidate_artifact_hash",
        ),
        sa.CheckConstraint(
            "artifact_bytes BETWEEN 0 AND 65536", name="ck_evaluation_candidate_artifact_size"
        ),
        sa.CheckConstraint(
            "jsonb_typeof(candidate_body)='object' AND octet_length(candidate_body::text)<=32768",
            name="ck_evaluation_candidate_body_bound",
        ),
    )
    op.create_table(
        "evaluation_applicability_assessments",
        sa.Column("id", postgresql.UUID(), primary_key=True),
        sa.Column(
            "evaluation_run_id",
            postgresql.UUID(),
            sa.ForeignKey("evaluation_runs.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("subject_kind", sa.String(24), nullable=False),
        sa.Column("subject_key", sa.String(80), nullable=False),
        sa.Column("subject_version", sa.String(80), nullable=False),
        sa.Column("source_role", sa.String(32), nullable=False),
        sa.Column("applicability_status", sa.String(32), nullable=False),
        sa.Column("assessment_checksum", sa.String(64), nullable=False),
        sa.Column("assessment_body", postgresql.JSONB(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.UniqueConstraint(
            "evaluation_run_id",
            "subject_kind",
            "subject_key",
            "subject_version",
            "source_role",
            name="uq_evaluation_applicability_identity",
        ),
        sa.CheckConstraint(
            "subject_kind IN ('9B_TASK','9C_FAMILY','9D_RECEIPT','9E_EVIDENCE','9F_AGENT')",
            name="ck_evaluation_applicability_subject",
        ),
        sa.CheckConstraint(
            "source_role IN ('synthetic','imported_fixture','imported','real_vehicle')",
            name="ck_evaluation_applicability_role",
        ),
        sa.CheckConstraint(
            "applicability_status IN ('SYNTHETIC_ONLY','EVALUATION_INSUFFICIENT','REAL_DATA_UNLABELED','INCOMPATIBLE','OOD_WARNING','NO_REFERENCE','NOT_CALIBRATED','REVIEW_REQUIRED')",
            name="ck_evaluation_applicability_status",
        ),
        sa.CheckConstraint(
            "length(assessment_checksum)=64", name="ck_evaluation_applicability_checksum"
        ),
        sa.CheckConstraint(
            "jsonb_typeof(assessment_body)='object' AND octet_length(assessment_body::text)<=32768",
            name="ck_evaluation_applicability_body_bound",
        ),
    )
    op.execute(
        "CREATE FUNCTION reject_immutable_evaluation_mutation() RETURNS trigger "
        "LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'Phase 9G evaluation records are immutable'; END $$"
    )
    for table in (
        "evaluation_protocols",
        "evaluation_runs",
        "evaluation_metric_reports",
        "evaluation_calibration_candidates",
        "evaluation_applicability_assessments",
    ):
        op.execute(
            f"CREATE TRIGGER trg_{table}_immutable BEFORE UPDATE OR DELETE ON {table} "
            "FOR EACH ROW EXECUTE FUNCTION reject_immutable_evaluation_mutation()"
        )
        op.execute(
            f"CREATE TRIGGER trg_{table}_immutable_truncate BEFORE TRUNCATE ON {table} "
            "FOR EACH STATEMENT EXECUTE FUNCTION reject_immutable_evaluation_mutation()"
        )


def downgrade() -> None:
    for table in (
        "evaluation_applicability_assessments",
        "evaluation_calibration_candidates",
        "evaluation_metric_reports",
        "evaluation_runs",
        "evaluation_protocols",
    ):
        op.execute(f"DROP TRIGGER IF EXISTS trg_{table}_immutable ON {table}")
        op.execute(f"DROP TRIGGER IF EXISTS trg_{table}_immutable_truncate ON {table}")
    op.execute("DROP FUNCTION IF EXISTS reject_immutable_evaluation_mutation()")
    op.drop_table("evaluation_applicability_assessments")
    op.drop_table("evaluation_calibration_candidates")
    op.drop_table("evaluation_metric_reports")
    op.drop_index("ix_evaluation_runs_created", table_name="evaluation_runs")
    op.drop_table("evaluation_runs")
    op.drop_table("evaluation_protocols")
