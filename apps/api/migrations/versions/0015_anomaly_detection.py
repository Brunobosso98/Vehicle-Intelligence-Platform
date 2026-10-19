"""Persist immutable offline Phase 9C detector, reference and finding evidence."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0015"
down_revision = "0014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "CREATE SEQUENCE anomaly_detector_version_seq START WITH 1 MINVALUE 1 "
        "MAXVALUE 99999999 NO CYCLE"
    )
    op.create_table(
        "anomaly_detector_definitions",
        sa.Column(
            "id", postgresql.UUID(), primary_key=True, server_default=sa.text("gen_random_uuid()")
        ),
        sa.Column("key", sa.String(120), nullable=False),
        sa.Column("version", sa.String(80), nullable=False),
        sa.Column("family", sa.String(32), nullable=False),
        sa.Column("method", sa.String(32), nullable=False),
        sa.Column("definition", postgresql.JSONB(), nullable=False),
        sa.Column("checksum", sa.String(64), nullable=False, unique=True),
        sa.Column("lifecycle_status", sa.String(20), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.UniqueConstraint("key", "version", name="uq_anomaly_definition_key_version"),
        sa.CheckConstraint(
            "family IN ('thermal','boost_air','performance','fuel')",
            name="ck_anomaly_definition_family",
        ),
        sa.CheckConstraint(
            "method IN ('robust_mad','isolation_forest')",
            name="ck_anomaly_definition_method",
        ),
        sa.CheckConstraint(
            "lifecycle_status IN ('CANDIDATE','ACCEPTED','REJECTED','RETIRED')",
            name="ck_anomaly_definition_lifecycle",
        ),
        sa.CheckConstraint("length(checksum)=64", name="ck_anomaly_definition_checksum"),
    )
    op.create_table(
        "anomaly_reference_datasets",
        sa.Column(
            "id", postgresql.UUID(), primary_key=True, server_default=sa.text("gen_random_uuid()")
        ),
        sa.Column(
            "detector_definition_id",
            postgresql.UUID(),
            sa.ForeignKey("anomaly_detector_definitions.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "feature_set_version_id",
            postgresql.UUID(),
            sa.ForeignKey("feature_set_versions.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "vehicle_id",
            postgresql.UUID(),
            sa.ForeignKey("vehicles.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "configuration_id",
            postgresql.UUID(),
            sa.ForeignKey("vehicle_configurations.id", ondelete="RESTRICT"),
        ),
        sa.Column("feature_set_version", sa.String(80), nullable=False),
        sa.Column("feature_set_version_checksum", sa.String(64), nullable=False),
        sa.Column("cohort_checksum", sa.String(64), nullable=False),
        sa.Column("observation_cutoff", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source_role", sa.String(32), nullable=False),
        sa.Column("source_type", sa.String(20), nullable=False),
        sa.Column("policy_version", sa.String(80), nullable=False),
        sa.Column("checksum", sa.String(64), nullable=False),
        sa.Column("row_count", sa.Integer(), nullable=False),
        sa.Column("session_count", sa.Integer(), nullable=False),
        sa.Column("exclusions", postgresql.JSONB(), nullable=False),
        sa.Column("manifest", postgresql.JSONB(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.UniqueConstraint(
            "detector_definition_id", "checksum", name="uq_anomaly_reference_definition_checksum"
        ),
        sa.CheckConstraint("length(checksum)=64", name="ck_anomaly_reference_checksum"),
        sa.CheckConstraint(
            "length(feature_set_version_checksum)=64 AND length(cohort_checksum)=64",
            name="ck_anomaly_reference_source_checksums",
        ),
        sa.CheckConstraint(
            "source_role IN ('synthetic','real_vehicle','imported','imported_fixture')",
            name="ck_anomaly_reference_source_role",
        ),
        sa.CheckConstraint("row_count BETWEEN 0 AND 10000", name="ck_anomaly_reference_row_count"),
        sa.CheckConstraint("session_count >= 0", name="ck_anomaly_reference_session_count"),
    )
    op.create_index(
        "ix_anomaly_reference_cohort_cutoff",
        "anomaly_reference_datasets",
        ["vehicle_id", "configuration_id", "observation_cutoff"],
    )
    op.create_index(
        "ix_anomaly_reference_detector_created",
        "anomaly_reference_datasets",
        ["detector_definition_id", "created_at"],
    )
    op.create_table(
        "anomaly_reference_rows",
        sa.Column("reference_dataset_id", postgresql.UUID(), nullable=False),
        sa.Column("row_id", sa.String(64), nullable=False),
        sa.Column(
            "feature_set_id",
            postgresql.UUID(),
            sa.ForeignKey("feature_sets.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "vehicle_id",
            postgresql.UUID(),
            sa.ForeignKey("vehicles.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "configuration_id",
            postgresql.UUID(),
            sa.ForeignKey("vehicle_configurations.id", ondelete="RESTRICT"),
        ),
        sa.Column(
            "session_id",
            postgresql.UUID(),
            sa.ForeignKey("driving_sessions.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "pull_id",
            postgresql.UUID(),
            sa.ForeignKey("pulls.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("pull_started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("pull_ended_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("observation_cutoff", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source_role", sa.String(32), nullable=False),
        sa.Column("source_type", sa.String(20), nullable=False),
        sa.Column("source_hash", sa.String(64), nullable=False),
        sa.Column("provenance_hash", sa.String(64), nullable=False),
        sa.Column("modification_ids", postgresql.JSONB(), nullable=False),
        sa.Column("available_signals", postgresql.JSONB(), nullable=False),
        sa.Column("feature_values", postgresql.JSONB(), nullable=False),
        sa.Column("feature_quality", postgresql.JSONB(), nullable=False),
        sa.Column("feature_missing", postgresql.JSONB(), nullable=False),
        sa.Column("feature_availability", postgresql.JSONB(), nullable=False),
        sa.Column("quality_metadata", postgresql.JSONB(), nullable=False),
        sa.ForeignKeyConstraint(
            ["reference_dataset_id"],
            ["anomaly_reference_datasets.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("reference_dataset_id", "row_id"),
        sa.UniqueConstraint(
            "reference_dataset_id", "feature_set_id", name="uq_anomaly_reference_feature_set"
        ),
        sa.CheckConstraint("length(row_id)=64", name="ck_anomaly_reference_row_id"),
        sa.CheckConstraint(
            "length(source_hash)=64 AND length(provenance_hash)=64",
            name="ck_anomaly_reference_row_hashes",
        ),
        sa.CheckConstraint(
            "pull_ended_at >= pull_started_at", name="ck_anomaly_reference_pull_range"
        ),
        sa.CheckConstraint(
            "octet_length(feature_values::text) <= 65536",
            name="ck_anomaly_reference_feature_payload",
        ),
    )
    op.create_index(
        "ix_anomaly_reference_rows_session_time",
        "anomaly_reference_rows",
        ["reference_dataset_id", "session_id", "pull_started_at"],
    )
    op.create_table(
        "anomaly_detector_versions",
        sa.Column(
            "id", postgresql.UUID(), primary_key=True, server_default=sa.text("gen_random_uuid()")
        ),
        sa.Column(
            "detector_definition_id",
            postgresql.UUID(),
            sa.ForeignKey("anomaly_detector_definitions.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "reference_dataset_id",
            postgresql.UUID(),
            sa.ForeignKey("anomaly_reference_datasets.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("version", sa.String(16), nullable=False, unique=True),
        sa.Column("fit_checksum", sa.String(64), nullable=False, unique=True),
        sa.Column("algorithm_version", sa.String(80), nullable=False),
        sa.Column("hyperparameters", postgresql.JSONB(), nullable=False),
        sa.Column("library_versions", postgresql.JSONB(), nullable=False),
        sa.Column("input_schema", postgresql.JSONB(), nullable=False),
        sa.Column("training_metrics", postgresql.JSONB(), nullable=False),
        sa.Column("threshold", sa.Float()),
        sa.Column("artifact_path", sa.String(240), unique=True),
        sa.Column("artifact_checksum", sa.String(64)),
        sa.Column("artifact_size_bytes", sa.BigInteger()),
        sa.Column("repository_sha", sa.String(64), nullable=False),
        sa.Column("state", sa.String(24), nullable=False),
        sa.Column("rejection_reason", sa.String(80)),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.CheckConstraint(
            "length(fit_checksum)=64 AND length(repository_sha) BETWEEN 7 AND 64",
            name="ck_anomaly_detector_version_hashes",
        ),
        sa.CheckConstraint(
            "state IN ('CANDIDATE','ACCEPTED','REJECTED')",
            name="ck_anomaly_detector_version_state",
        ),
        sa.CheckConstraint(
            "(state IN ('CANDIDATE','ACCEPTED') AND threshold IS NOT NULL AND artifact_path IS NOT NULL "
            "AND artifact_checksum IS NOT NULL AND artifact_size_bytes BETWEEN 1 AND 52428800 "
            "AND rejection_reason IS NULL) OR (state='REJECTED' AND artifact_path IS NULL "
            "AND artifact_checksum IS NULL AND artifact_size_bytes IS NULL "
            "AND rejection_reason IS NOT NULL)",
            name="ck_anomaly_detector_artifact_state",
        ),
        sa.CheckConstraint(
            "artifact_checksum IS NULL OR length(artifact_checksum)=64",
            name="ck_anomaly_detector_artifact_checksum",
        ),
    )
    op.create_index(
        "ix_anomaly_detector_version_definition_created",
        "anomaly_detector_versions",
        ["detector_definition_id", "created_at"],
    )
    op.create_index(
        "ix_anomaly_detector_versions_reference",
        "anomaly_detector_versions",
        ["detector_definition_id", "reference_dataset_id"],
    )
    op.create_table(
        "anomaly_detection_runs",
        sa.Column(
            "id", postgresql.UUID(), primary_key=True, server_default=sa.text("gen_random_uuid()")
        ),
        sa.Column("run_identity", sa.String(64), nullable=False, unique=True),
        sa.Column(
            "detector_version_id",
            postgresql.UUID(),
            sa.ForeignKey("anomaly_detector_versions.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "reference_dataset_id",
            postgresql.UUID(),
            sa.ForeignKey("anomaly_reference_datasets.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("observation_cutoff", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source_role", sa.String(32), nullable=False),
        sa.Column("input_checksum", sa.String(64), nullable=False),
        sa.Column("artifact_checksum", sa.String(64)),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("requested_count", sa.Integer(), nullable=False),
        sa.Column("finding_count", sa.Integer(), nullable=False),
        sa.Column("status_counts", postgresql.JSONB(), nullable=False),
        sa.Column("summary", postgresql.JSONB(), nullable=False),
        sa.Column("duration_seconds", sa.Float(), nullable=False),
        sa.Column("error_category", sa.String(80)),
        sa.Column("trace_id", sa.String(32)),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.CheckConstraint("length(run_identity)=64", name="ck_anomaly_run_identity"),
        sa.CheckConstraint("length(input_checksum)=64", name="ck_anomaly_run_input_checksum"),
        sa.CheckConstraint(
            "artifact_checksum IS NULL OR length(artifact_checksum)=64",
            name="ck_anomaly_run_artifact_checksum",
        ),
        sa.CheckConstraint(
            "source_role IN ('synthetic','real_vehicle','imported','imported_fixture')",
            name="ck_anomaly_run_source_role",
        ),
        sa.CheckConstraint("status IN ('COMPLETED','FAILED')", name="ck_anomaly_run_status"),
        sa.CheckConstraint(
            "requested_count BETWEEN 0 AND 1000 AND finding_count BETWEEN 0 AND requested_count",
            name="ck_anomaly_run_counts",
        ),
        sa.CheckConstraint("duration_seconds >= 0", name="ck_anomaly_run_duration"),
        sa.CheckConstraint(
            "trace_id IS NULL OR length(trace_id)=32", name="ck_anomaly_run_trace_id"
        ),
    )
    op.create_index(
        "ix_anomaly_runs_detector_created",
        "anomaly_detection_runs",
        ["detector_version_id", "created_at"],
    )
    op.create_table(
        "anomaly_findings",
        sa.Column(
            "id", postgresql.UUID(), primary_key=True, server_default=sa.text("gen_random_uuid()")
        ),
        sa.Column(
            "run_id",
            postgresql.UUID(),
            sa.ForeignKey("anomaly_detection_runs.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "detector_version_id",
            postgresql.UUID(),
            sa.ForeignKey("anomaly_detector_versions.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "reference_dataset_id",
            postgresql.UUID(),
            sa.ForeignKey("anomaly_reference_datasets.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "feature_set_id",
            postgresql.UUID(),
            sa.ForeignKey("feature_sets.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "vehicle_id",
            postgresql.UUID(),
            sa.ForeignKey("vehicles.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "configuration_id",
            postgresql.UUID(),
            sa.ForeignKey("vehicle_configurations.id", ondelete="RESTRICT"),
        ),
        sa.Column(
            "session_id",
            postgresql.UUID(),
            sa.ForeignKey("driving_sessions.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "pull_id",
            postgresql.UUID(),
            sa.ForeignKey("pulls.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("finding_identity", sa.String(64), nullable=False, unique=True),
        sa.Column("correlation_group_id", sa.String(64), nullable=False),
        sa.Column("family", sa.String(32), nullable=False),
        sa.Column("horizon", sa.String(32), nullable=False),
        sa.Column("observation_cutoff", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source_role", sa.String(32), nullable=False),
        sa.Column("source_hash", sa.String(64), nullable=False),
        sa.Column("provenance_hash", sa.String(64), nullable=False),
        sa.Column("score", sa.Float()),
        sa.Column("threshold", sa.Float()),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("coverage", sa.Float(), nullable=False),
        sa.Column("observed_features", postgresql.JSONB(), nullable=False),
        sa.Column("absent_features", postgresql.JSONB(), nullable=False),
        sa.Column("contributions", postgresql.JSONB(), nullable=False),
        sa.Column("reason_codes", postgresql.JSONB(), nullable=False),
        sa.Column("reference_summary", postgresql.JSONB(), nullable=False),
        sa.Column("provenance", postgresql.JSONB(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.UniqueConstraint(
            "run_id",
            "detector_version_id",
            "feature_set_id",
            "observation_cutoff",
            name="uq_anomaly_finding_run_input",
        ),
        sa.CheckConstraint("length(finding_identity)=64", name="ck_anomaly_finding_identity"),
        sa.CheckConstraint("length(correlation_group_id)=64", name="ck_anomaly_finding_group"),
        sa.CheckConstraint(
            "length(source_hash)=64 AND length(provenance_hash)=64",
            name="ck_anomaly_finding_source_hashes",
        ),
        sa.CheckConstraint(
            "family IN ('thermal','boost_air','performance','fuel')",
            name="ck_anomaly_finding_family",
        ),
        sa.CheckConstraint("horizon='AFTER_PULL_OFFLINE'", name="ck_anomaly_finding_horizon"),
        sa.CheckConstraint(
            "source_role IN ('synthetic','real_vehicle','imported','imported_fixture')",
            name="ck_anomaly_finding_source_role",
        ),
        sa.CheckConstraint(
            "status IN ('ANOMALOUS','INLIER','INSUFFICIENT_REFERENCE','INSUFFICIENT_SIGNAL',"
            "'LOW_QUALITY','INCOMPATIBLE_CONTEXT','UNSUPPORTED_SOURCE','NOT_EVALUABLE')",
            name="ck_anomaly_finding_status",
        ),
        sa.CheckConstraint("coverage BETWEEN 0 AND 1", name="ck_anomaly_finding_coverage"),
        sa.CheckConstraint(
            "score IS NULL OR (score > '-Infinity'::float8 AND score < 'Infinity'::float8)",
            name="ck_anomaly_finding_finite_score",
        ),
        sa.CheckConstraint(
            "threshold IS NULL OR (threshold >= 0 AND threshold < 'Infinity'::float8)",
            name="ck_anomaly_finding_finite_threshold",
        ),
        sa.CheckConstraint(
            "octet_length(contributions::text) <= 16384 AND octet_length(provenance::text) <= 32768",
            name="ck_anomaly_finding_payload_bounds",
        ),
    )
    op.create_index(
        "ix_anomaly_findings_vehicle_time",
        "anomaly_findings",
        ["vehicle_id", "observation_cutoff"],
    )
    op.create_index(
        "ix_anomaly_findings_family_status_time",
        "anomaly_findings",
        ["family", "status", "observation_cutoff"],
    )

    op.execute(
        "CREATE FUNCTION reject_immutable_anomaly_mutation() RETURNS trigger "
        "LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'Phase 9C anomaly evidence is immutable'; "
        "END; $$"
    )
    for table in (
        "anomaly_detector_definitions",
        "anomaly_reference_datasets",
        "anomaly_reference_rows",
        "anomaly_detector_versions",
        "anomaly_detection_runs",
        "anomaly_findings",
    ):
        op.execute(
            f"CREATE TRIGGER trg_{table}_immutable BEFORE UPDATE OR DELETE ON {table} "
            "FOR EACH ROW EXECUTE FUNCTION reject_immutable_anomaly_mutation()"
        )


def downgrade() -> None:
    for table in (
        "anomaly_detector_definitions",
        "anomaly_reference_datasets",
        "anomaly_reference_rows",
        "anomaly_detector_versions",
        "anomaly_detection_runs",
        "anomaly_findings",
    ):
        op.execute(f"DROP TRIGGER IF EXISTS trg_{table}_immutable ON {table}")
    op.execute("DROP FUNCTION IF EXISTS reject_immutable_anomaly_mutation()")
    op.drop_index("ix_anomaly_findings_family_status_time", table_name="anomaly_findings")
    op.drop_index("ix_anomaly_findings_vehicle_time", table_name="anomaly_findings")
    op.drop_table("anomaly_findings")
    op.drop_index("ix_anomaly_runs_detector_created", table_name="anomaly_detection_runs")
    op.drop_table("anomaly_detection_runs")
    op.drop_index(
        "ix_anomaly_detector_version_definition_created", table_name="anomaly_detector_versions"
    )
    op.drop_index("ix_anomaly_detector_versions_reference", table_name="anomaly_detector_versions")
    op.drop_table("anomaly_detector_versions")
    op.drop_index("ix_anomaly_reference_rows_session_time", table_name="anomaly_reference_rows")
    op.drop_table("anomaly_reference_rows")
    op.drop_index("ix_anomaly_reference_detector_created", table_name="anomaly_reference_datasets")
    op.drop_index("ix_anomaly_reference_cohort_cutoff", table_name="anomaly_reference_datasets")
    op.drop_table("anomaly_reference_datasets")
    op.drop_table("anomaly_detector_definitions")
    op.execute("DROP SEQUENCE IF EXISTS anomaly_detector_version_seq")
