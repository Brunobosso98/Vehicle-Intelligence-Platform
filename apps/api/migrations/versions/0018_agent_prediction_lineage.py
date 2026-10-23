"""Keep Phase 9E identifiers out of public AgentRun evidence snapshots."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0018"
down_revision = "0017"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "agent_prediction_evidence_links",
        sa.Column(
            "agent_run_id",
            postgresql.UUID(),
            sa.ForeignKey("agent_runs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("run_evidence_id", postgresql.UUID(), nullable=False),
        sa.Column("source_evidence_id", postgresql.UUID(), nullable=False),
        sa.Column("receipt_id", postgresql.UUID(), nullable=False),
        sa.Column("source_vehicle_id", postgresql.UUID(), nullable=False),
        sa.Column("source_session_id", postgresql.UUID(), nullable=False),
        sa.Column("source_pull_id", postgresql.UUID(), nullable=False),
        sa.Column("source_configuration_id", postgresql.UUID()),
        sa.Column("source_feature_set_id", postgresql.UUID()),
        sa.Column("result_type", sa.String(24), nullable=False),
        sa.Column("horizon", sa.String(32), nullable=False),
        sa.Column("task", sa.String(80)),
        sa.Column("family", sa.String(32)),
        sa.Column("model_version", sa.String(80)),
        sa.Column("model_algorithm", sa.String(80)),
        sa.Column("detector_version", sa.String(80)),
        sa.Column("detector_algorithm_version", sa.String(80)),
        sa.Column("detector_method", sa.String(32)),
        sa.Column("source_role", sa.String(32), nullable=False),
        sa.Column("effective_cutoff", sa.DateTime(timezone=True), nullable=False),
        sa.Column("integrity", sa.String(48), nullable=False),
        sa.Column("completeness", sa.String(16), nullable=False),
        sa.Column("artifact_availability", sa.String(32), nullable=False),
        sa.Column("projection_version", sa.String(80), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.PrimaryKeyConstraint("agent_run_id", "run_evidence_id"),
        sa.CheckConstraint(
            "source_role IN ('synthetic','real_vehicle','imported','imported_fixture')",
            name="ck_agent_prediction_link_role",
        ),
        sa.CheckConstraint(
            "integrity IN ('VERIFIED','VERIFIED_SNAPSHOT_ARTIFACT_UNAVAILABLE')",
            name="ck_agent_prediction_link_integrity",
        ),
        sa.CheckConstraint(
            "completeness IN ('COMPLETE','PARTIAL','ABSTAINED')",
            name="ck_agent_prediction_link_completeness",
        ),
        sa.CheckConstraint(
            "(result_type='next_pull' AND horizon='NEXT_PULL') OR "
            "(result_type='anomaly' AND horizon='AFTER_PULL_OFFLINE')",
            name="ck_agent_prediction_link_horizon",
        ),
        sa.CheckConstraint(
            "family IS NULL OR family IN ('thermal','boost_air','performance','fuel')",
            name="ck_agent_prediction_link_family",
        ),
        sa.CheckConstraint(
            "artifact_availability IN ('VERIFIED','NOT_APPLICABLE','UNAVAILABLE','CHECKSUM_MISMATCH')",
            name="ck_agent_prediction_link_artifact",
        ),
        sa.CheckConstraint(
            "length(projection_version)<=80",
            name="ck_agent_prediction_link_projection_version",
        ),
    )


def downgrade() -> None:
    op.drop_table("agent_prediction_evidence_links")
