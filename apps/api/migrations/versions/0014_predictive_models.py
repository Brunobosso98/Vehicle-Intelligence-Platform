"""Persist versioned offline predictive-model training records."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0014"
down_revision = "0013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "CREATE SEQUENCE ml_model_version_seq START WITH 1 MINVALUE 1 MAXVALUE 99999999 NO CYCLE"
    )
    op.create_table(
        "label_definitions",
        sa.Column(
            "id", postgresql.UUID(), primary_key=True, server_default=sa.text("gen_random_uuid()")
        ),
        sa.Column("key", sa.String(120), nullable=False),
        sa.Column("version", sa.String(80), nullable=False),
        sa.Column("definition", postgresql.JSONB(), nullable=False),
        sa.Column("checksum", sa.String(64), nullable=False, unique=True),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.UniqueConstraint("key", "version", name="uq_label_definition_key_version"),
        sa.CheckConstraint("length(checksum)=64", name="ck_label_definition_checksum"),
    )
    op.create_table(
        "ml_models",
        sa.Column(
            "id", postgresql.UUID(), primary_key=True, server_default=sa.text("gen_random_uuid()")
        ),
        sa.Column("task", sa.String(80), nullable=False, unique=True),
        sa.Column("description", sa.String(500), nullable=False),
        sa.Column("label_key", sa.String(120), nullable=False),
        sa.Column("prediction_horizon", sa.String(40), nullable=False),
        sa.Column("intended_scope", sa.String(240), nullable=False),
        sa.Column("state", sa.String(20), nullable=False, server_default="CANDIDATE"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.CheckConstraint(
            "state IN ('TRAINING','EVALUATED','REJECTED','CANDIDATE')",
            name="ck_ml_model_state",
        ),
    )
    op.create_table(
        "supervised_datasets",
        sa.Column(
            "id", postgresql.UUID(), primary_key=True, server_default=sa.text("gen_random_uuid()")
        ),
        sa.Column("task", sa.String(80), nullable=False),
        sa.Column(
            "label_definition_id",
            postgresql.UUID(),
            sa.ForeignKey("label_definitions.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "feature_set_version_id",
            postgresql.UUID(),
            sa.ForeignKey("feature_set_versions.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "dataset_definition_id",
            postgresql.UUID(),
            sa.ForeignKey("dataset_definitions.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "outcome_dataset_definition_id",
            postgresql.UUID(),
            sa.ForeignKey("dataset_definitions.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("repository_sha", sa.String(64), nullable=False),
        sa.Column("source_fingerprint", sa.String(64), nullable=False),
        sa.Column("checksum", sa.String(64), nullable=False),
        sa.Column("row_count", sa.Integer(), nullable=False),
        sa.Column("exclusion_count", sa.Integer(), nullable=False),
        sa.Column("manifest", postgresql.JSONB(), nullable=False),
        sa.Column("exclusions", postgresql.JSONB(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.UniqueConstraint("task", "checksum", name="uq_supervised_dataset_task_checksum"),
        sa.CheckConstraint(
            "length(repository_sha) BETWEEN 7 AND 64", name="ck_supervised_dataset_repository_sha"
        ),
        sa.CheckConstraint(
            "length(source_fingerprint)=64", name="ck_supervised_dataset_source_fingerprint"
        ),
        sa.CheckConstraint("length(checksum)=64", name="ck_supervised_dataset_checksum"),
        sa.CheckConstraint(
            "row_count >= 0 AND exclusion_count >= 0", name="ck_supervised_dataset_counts"
        ),
        sa.CheckConstraint("row_count <= 100000", name="ck_supervised_dataset_row_limit"),
    )
    op.create_index(
        "ix_supervised_datasets_task_created", "supervised_datasets", ["task", "created_at"]
    )
    op.create_table(
        "supervised_dataset_rows",
        sa.Column("supervised_dataset_id", postgresql.UUID(), nullable=False),
        sa.Column("row_id", sa.String(64), nullable=False),
        sa.Column("vehicle_id", postgresql.UUID(), nullable=False),
        sa.Column("configuration_id", postgresql.UUID(), nullable=False),
        sa.Column("session_id", postgresql.UUID(), nullable=False),
        sa.Column("input_pull_id", postgresql.UUID(), nullable=False),
        sa.Column("target_pull_id", postgresql.UUID(), nullable=False),
        sa.Column("input_feature_set_id", postgresql.UUID(), nullable=False),
        sa.Column("target_feature_set_id", postgresql.UUID(), nullable=False),
        sa.Column("input_source_hash", sa.String(64), nullable=False),
        sa.Column("target_source_hash", sa.String(64), nullable=False),
        sa.Column("input_started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("input_available_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("target_started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("target_value", sa.Boolean(), nullable=False),
        sa.Column("features", postgresql.JSONB(), nullable=False),
        sa.Column("missing", postgresql.JSONB(), nullable=False),
        sa.Column("feature_quality", postgresql.JSONB(), nullable=False),
        sa.Column("label_provenance", postgresql.JSONB(), nullable=False),
        sa.Column("scenario_family", sa.String(120)),
        sa.Column("quality_class", sa.String(40), nullable=False),
        sa.ForeignKeyConstraint(
            ["supervised_dataset_id"], ["supervised_datasets.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(["vehicle_id"], ["vehicles.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["configuration_id"], ["vehicle_configurations.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(["session_id"], ["driving_sessions.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["input_pull_id"], ["pulls.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["target_pull_id"], ["pulls.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["input_feature_set_id"], ["feature_sets.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["target_feature_set_id"], ["feature_sets.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("supervised_dataset_id", "row_id"),
        sa.CheckConstraint("length(row_id)=64", name="ck_supervised_row_id"),
        sa.CheckConstraint(
            "length(input_source_hash)=64 AND length(target_source_hash)=64",
            name="ck_supervised_row_source_hashes",
        ),
        sa.CheckConstraint(
            "input_pull_id <> target_pull_id", name="ck_supervised_row_distinct_pulls"
        ),
        sa.CheckConstraint(
            "input_available_at < target_started_at", name="ck_supervised_row_no_future_input"
        ),
        sa.CheckConstraint(
            "quality_class IN ('high_quality','degraded_but_eligible')",
            name="ck_supervised_row_quality_class",
        ),
    )
    op.create_index(
        "ix_supervised_rows_dataset_session",
        "supervised_dataset_rows",
        ["supervised_dataset_id", "session_id", "target_started_at"],
    )
    op.create_index(
        "ix_supervised_rows_dataset_configuration",
        "supervised_dataset_rows",
        ["supervised_dataset_id", "configuration_id"],
    )
    op.create_table(
        "ml_model_versions",
        sa.Column(
            "id", postgresql.UUID(), primary_key=True, server_default=sa.text("gen_random_uuid()")
        ),
        sa.Column(
            "ml_model_id",
            postgresql.UUID(),
            sa.ForeignKey("ml_models.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "label_definition_id",
            postgresql.UUID(),
            sa.ForeignKey("label_definitions.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "feature_set_version_id",
            postgresql.UUID(),
            sa.ForeignKey("feature_set_versions.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "dataset_definition_id",
            postgresql.UUID(),
            sa.ForeignKey("dataset_definitions.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "outcome_dataset_definition_id",
            postgresql.UUID(),
            sa.ForeignKey("dataset_definitions.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "supervised_dataset_id",
            postgresql.UUID(),
            sa.ForeignKey("supervised_datasets.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("version", sa.String(80), nullable=False),
        sa.Column("algorithm", sa.String(80), nullable=False),
        sa.Column("hyperparameters", postgresql.JSONB(), nullable=False),
        sa.Column("random_seed", sa.Integer(), nullable=False),
        sa.Column("dataset_checksum", sa.String(64), nullable=False),
        sa.Column("source_fingerprint", sa.String(64), nullable=False),
        sa.Column("train_count", sa.Integer(), nullable=False),
        sa.Column("validation_count", sa.Integer(), nullable=False),
        sa.Column("test_count", sa.Integer(), nullable=False),
        sa.Column("temporal_range", postgresql.JSONB(), nullable=False),
        sa.Column("metrics", postgresql.JSONB(), nullable=False),
        sa.Column("input_schema", postgresql.JSONB(), nullable=False),
        sa.Column("threshold", sa.Float(), nullable=False),
        sa.Column("artifact_path", sa.String(240), nullable=False, unique=True),
        sa.Column("artifact_checksum", sa.String(64), nullable=False),
        sa.Column("repository_sha", sa.String(64), nullable=False),
        sa.Column("library_versions", postgresql.JSONB(), nullable=False),
        sa.Column("state", sa.String(20), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.UniqueConstraint("ml_model_id", "version", name="uq_ml_model_version"),
        sa.CheckConstraint("length(dataset_checksum)=64", name="ck_ml_version_dataset_checksum"),
        sa.CheckConstraint(
            "length(source_fingerprint)=64", name="ck_ml_version_source_fingerprint"
        ),
        sa.CheckConstraint("length(artifact_checksum)=64", name="ck_ml_version_artifact_checksum"),
        sa.CheckConstraint(
            "train_count > 0 AND validation_count > 0 AND test_count > 0",
            name="ck_ml_version_counts",
        ),
        sa.CheckConstraint("threshold > 0 AND threshold < 1", name="ck_ml_version_threshold"),
        sa.CheckConstraint(
            "state IN ('EVALUATED','REJECTED','CANDIDATE')", name="ck_ml_version_state"
        ),
    )
    op.create_index(
        "ix_ml_model_versions_model_created", "ml_model_versions", ["ml_model_id", "created_at"]
    )
    op.create_table(
        "training_runs",
        sa.Column(
            "id", postgresql.UUID(), primary_key=True, server_default=sa.text("gen_random_uuid()")
        ),
        sa.Column("task", sa.String(80), nullable=False),
        sa.Column(
            "label_definition_id",
            postgresql.UUID(),
            sa.ForeignKey("label_definitions.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "dataset_definition_id",
            postgresql.UUID(),
            sa.ForeignKey("dataset_definitions.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "outcome_dataset_definition_id",
            postgresql.UUID(),
            sa.ForeignKey("dataset_definitions.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "supervised_dataset_id",
            postgresql.UUID(),
            sa.ForeignKey("supervised_datasets.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "ml_model_version_id",
            postgresql.UUID(),
            sa.ForeignKey("ml_model_versions.id", ondelete="RESTRICT"),
        ),
        sa.Column("dataset_checksum", sa.String(64), nullable=False),
        sa.Column("repository_sha", sa.String(64), nullable=False),
        sa.Column("model_spec", postgresql.JSONB(), nullable=False),
        sa.Column("candidate_models", postgresql.JSONB(), nullable=False),
        sa.Column("selected_model_family", sa.String(80)),
        sa.Column("seed", sa.Integer(), nullable=False),
        sa.Column("state", sa.String(20), nullable=False),
        sa.Column(
            "metrics", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")
        ),
        sa.Column("artifact_checksum", sa.String(64)),
        sa.Column("error_category", sa.String(80)),
        sa.Column("trace_id", sa.String(32)),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True)),
        sa.CheckConstraint("length(dataset_checksum)=64", name="ck_training_run_dataset_checksum"),
        sa.CheckConstraint(
            "length(repository_sha) BETWEEN 7 AND 64", name="ck_training_run_repository_sha"
        ),
        sa.CheckConstraint(
            "artifact_checksum IS NULL OR length(artifact_checksum)=64",
            name="ck_training_run_artifact_checksum",
        ),
        sa.CheckConstraint(
            "trace_id IS NULL OR length(trace_id)=32", name="ck_training_run_trace_id"
        ),
        sa.CheckConstraint(
            "state IN ('TRAINING','EVALUATED','REJECTED','CANDIDATE')",
            name="ck_training_run_state",
        ),
        sa.CheckConstraint(
            "finished_at IS NULL OR finished_at >= started_at",
            name="ck_training_run_time_range",
        ),
    )
    op.create_index("ix_training_runs_task_started", "training_runs", ["task", "started_at"])

    op.execute(
        "CREATE FUNCTION reject_immutable_ml_record_mutation() RETURNS trigger "
        "LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'registered model metadata is immutable'; "
        "END; $$"
    )
    for table in (
        "label_definitions",
        "supervised_datasets",
        "supervised_dataset_rows",
        "ml_model_versions",
    ):
        op.execute(
            f"CREATE TRIGGER trg_{table}_immutable BEFORE UPDATE OR DELETE ON {table} "
            "FOR EACH ROW EXECUTE FUNCTION reject_immutable_ml_record_mutation()"
        )


def downgrade() -> None:
    for table in (
        "label_definitions",
        "supervised_datasets",
        "supervised_dataset_rows",
        "ml_model_versions",
    ):
        op.execute(f"DROP TRIGGER IF EXISTS trg_{table}_immutable ON {table}")
    op.execute("DROP FUNCTION IF EXISTS reject_immutable_ml_record_mutation()")
    op.drop_index("ix_training_runs_task_started", table_name="training_runs")
    op.drop_table("training_runs")
    op.drop_index("ix_ml_model_versions_model_created", table_name="ml_model_versions")
    op.drop_table("ml_model_versions")
    op.drop_table("ml_models")
    op.drop_index("ix_supervised_rows_dataset_configuration", table_name="supervised_dataset_rows")
    op.drop_index("ix_supervised_rows_dataset_session", table_name="supervised_dataset_rows")
    op.drop_table("supervised_dataset_rows")
    op.drop_index("ix_supervised_datasets_task_created", table_name="supervised_datasets")
    op.drop_table("supervised_datasets")
    op.drop_table("label_definitions")
    op.execute("DROP SEQUENCE IF EXISTS ml_model_version_seq")
