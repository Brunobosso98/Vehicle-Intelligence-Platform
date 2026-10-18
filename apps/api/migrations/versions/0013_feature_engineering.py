"""Persist immutable Phase 9A feature definitions, vectors and dataset runs."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0013"
down_revision = "0012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "feature_set_versions",
        sa.Column(
            "id", postgresql.UUID(), primary_key=True, server_default=sa.text("gen_random_uuid()")
        ),
        sa.Column("version", sa.String(80), nullable=False, unique=True),
        sa.Column("generator_version", sa.String(80), nullable=False),
        sa.Column("source_schema_version", sa.String(80), nullable=False),
        sa.Column("feature_definitions", postgresql.JSONB(), nullable=False),
        sa.Column("selection_policy", postgresql.JSONB(), nullable=False),
        sa.Column("quality_policy", postgresql.JSONB(), nullable=False),
        sa.Column("temporal_policy", postgresql.JSONB(), nullable=False),
        sa.Column("checksum", sa.String(64), nullable=False, unique=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.CheckConstraint("length(checksum)=64", name="ck_feature_version_checksum"),
    )
    op.create_table(
        "feature_sets",
        sa.Column(
            "id", postgresql.UUID(), primary_key=True, server_default=sa.text("gen_random_uuid()")
        ),
        sa.Column(
            "vehicle_id",
            postgresql.UUID(),
            sa.ForeignKey("vehicles.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "configuration_id",
            postgresql.UUID(),
            sa.ForeignKey("vehicle_configurations.id", ondelete="SET NULL"),
        ),
        sa.Column(
            "session_id",
            postgresql.UUID(),
            sa.ForeignKey("driving_sessions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "pull_id",
            postgresql.UUID(),
            sa.ForeignKey("pulls.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("entity_scope", sa.String(24), nullable=False),
        sa.Column(
            "feature_set_version_id",
            postgresql.UUID(),
            sa.ForeignKey("feature_set_versions.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("source_window_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source_window_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("observation_cutoff", sa.DateTime(timezone=True), nullable=False),
        sa.Column("feature_values", postgresql.JSONB(), nullable=False),
        sa.Column("quality_metadata", postgresql.JSONB(), nullable=False),
        sa.Column("provenance", postgresql.JSONB(), nullable=False),
        sa.Column("source_hash", sa.String(64), nullable=False),
        sa.Column("provenance_hash", sa.String(64), nullable=False),
        sa.Column("generator_version", sa.String(80), nullable=False),
        sa.Column(
            "generated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.CheckConstraint("entity_scope='pull'", name="ck_feature_set_scope"),
        sa.CheckConstraint(
            "source_window_end >= source_window_start", name="ck_feature_set_window"
        ),
        sa.CheckConstraint(
            "length(source_hash)=64 AND length(provenance_hash)=64", name="ck_feature_set_hashes"
        ),
        sa.CheckConstraint(
            "octet_length(feature_values::text) <= 262144", name="ck_feature_set_payload_bound"
        ),
        sa.UniqueConstraint(
            "vehicle_id",
            "entity_scope",
            "pull_id",
            "feature_set_version_id",
            "source_hash",
            name="uq_feature_set_identity",
        ),
    )
    op.create_index(
        "ix_feature_sets_vehicle_version_cutoff",
        "feature_sets",
        ["vehicle_id", "feature_set_version_id", "observation_cutoff"],
    )
    op.create_index(
        "ix_feature_sets_configuration_version",
        "feature_sets",
        ["configuration_id", "feature_set_version_id"],
    )
    op.create_index(
        "ix_feature_sets_session_version", "feature_sets", ["session_id", "feature_set_version_id"]
    )
    op.create_index(
        "ix_feature_sets_pull_version_cutoff",
        "feature_sets",
        ["pull_id", "feature_set_version_id", "observation_cutoff"],
    )
    op.create_table(
        "feature_generation_runs",
        sa.Column(
            "id", postgresql.UUID(), primary_key=True, server_default=sa.text("gen_random_uuid()")
        ),
        sa.Column(
            "feature_set_version_id",
            postgresql.UUID(),
            sa.ForeignKey("feature_set_versions.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("requested_scope", sa.String(24), nullable=False),
        sa.Column("requested_entity_id", postgresql.UUID()),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("generated_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("reused_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("failed_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "error_categories", postgresql.ARRAY(sa.String(80)), nullable=False, server_default="{}"
        ),
        sa.Column("source_snapshot_hash", sa.String(64)),
        sa.Column("trace_id", sa.String(32)),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "finished_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.CheckConstraint(
            "status IN ('completed','partial','failed')", name="ck_feature_generation_status"
        ),
        sa.CheckConstraint(
            "generated_count >= 0 AND reused_count >= 0 AND failed_count >= 0",
            name="ck_feature_generation_counts",
        ),
    )
    op.create_index(
        "ix_feature_generation_version_started",
        "feature_generation_runs",
        ["feature_set_version_id", "started_at"],
    )
    op.create_table(
        "dataset_definitions",
        sa.Column(
            "id", postgresql.UUID(), primary_key=True, server_default=sa.text("gen_random_uuid()")
        ),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("version", sa.String(80), nullable=False),
        sa.Column("definition", postgresql.JSONB(), nullable=False),
        sa.Column("checksum", sa.String(64), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.UniqueConstraint("name", "version", name="uq_dataset_definition_name_version"),
        sa.CheckConstraint("length(checksum)=64", name="ck_dataset_definition_checksum"),
    )
    op.create_table(
        "dataset_build_runs",
        sa.Column(
            "id", postgresql.UUID(), primary_key=True, server_default=sa.text("gen_random_uuid()")
        ),
        sa.Column(
            "dataset_definition_id",
            postgresql.UUID(),
            sa.ForeignKey("dataset_definitions.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "feature_set_version_id",
            postgresql.UUID(),
            sa.ForeignKey("feature_set_versions.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("observation_cutoff", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("row_count", sa.Integer(), nullable=False),
        sa.Column("excluded_count", sa.Integer(), nullable=False),
        sa.Column("checksum", sa.String(64), nullable=False),
        sa.Column("manifest", postgresql.JSONB(), nullable=False),
        sa.Column(
            "generated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.CheckConstraint("status IN ('completed','failed')", name="ck_dataset_build_status"),
        sa.CheckConstraint(
            "row_count >= 0 AND excluded_count >= 0", name="ck_dataset_build_counts"
        ),
        sa.CheckConstraint("length(checksum)=64", name="ck_dataset_build_checksum"),
    )
    op.create_index(
        "ix_dataset_builds_definition_generated",
        "dataset_build_runs",
        ["dataset_definition_id", "generated_at"],
    )
    op.create_index(
        "ix_dataset_builds_version_cutoff",
        "dataset_build_runs",
        ["feature_set_version_id", "observation_cutoff"],
    )


def downgrade() -> None:
    op.drop_table("dataset_build_runs")
    op.drop_table("dataset_definitions")
    op.drop_table("feature_generation_runs")
    op.drop_table("feature_sets")
    op.drop_table("feature_set_versions")
