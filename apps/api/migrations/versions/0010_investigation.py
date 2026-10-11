"""Add bounded, agent-owned investigation lifecycle and session links.

No existing vehicle, telemetry, acquisition or AgentRun rows are rewritten.
Downgrade discards only Phase 7B investigation records and is for disposable validation.
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "acquisition_source_capabilities",
        sa.Column("id", postgresql.UUID(), primary_key=True),
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
            nullable=False,
        ),
        sa.Column("adapter", sa.String(20), nullable=False),
        sa.Column("source_id", sa.String(80), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("report", postgresql.JSONB(), nullable=False),
        sa.UniqueConstraint(
            "vehicle_id",
            "configuration_id",
            "adapter",
            "source_id",
            name="uq_acquisition_source_capability",
        ),
        sa.CheckConstraint("adapter IN ('obd','replay')", name="ck_source_capability_adapter"),
        sa.CheckConstraint(
            "octet_length(report::text) <= 32768", name="ck_source_capability_report_size"
        ),
    )
    op.create_table(
        "investigation_plans",
        sa.Column("id", postgresql.UUID(), primary_key=True),
        sa.Column(
            "vehicle_id",
            postgresql.UUID(),
            sa.ForeignKey("vehicles.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "agent_run_id",
            postgresql.UUID(),
            sa.ForeignKey("agent_runs.id", ondelete="RESTRICT"),
            nullable=False,
            unique=True,
        ),
        sa.Column(
            "reanalysis_run_id",
            postgresql.UUID(),
            sa.ForeignKey("agent_runs.id", ondelete="RESTRICT"),
            nullable=True,
        ),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("recipe_hash", sa.String(64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("snapshot", postgresql.JSONB(), nullable=False),
        sa.CheckConstraint("version >= 1", name="ck_investigation_version"),
        sa.CheckConstraint(
            "status IN ('DRAFT','EVIDENCE_GAPS_IDENTIFIED','CAPABILITIES_RESOLVED',"
            "'RECIPE_PROPOSED','AWAITING_APPROVAL','APPROVED','ACQUISITION_READY',"
            "'AWAITING_DATA','DATA_RECEIVED','REANALYZING','COMPLETED','INCONCLUSIVE',"
            "'REJECTED','CANCELLED','FAILED')",
            name="ck_investigation_status",
        ),
        sa.CheckConstraint(
            "recipe_hash IS NULL OR recipe_hash ~ '^[0-9a-f]{64}$'",
            name="ck_investigation_recipe_hash",
        ),
        sa.CheckConstraint(
            "octet_length(snapshot::text) <= 262144", name="ck_investigation_snapshot_size"
        ),
    )
    op.create_index(
        "ix_investigation_vehicle_created",
        "investigation_plans",
        ["vehicle_id", sa.text("created_at DESC"), "id"],
    )
    op.create_table(
        "investigation_session_links",
        sa.Column(
            "investigation_id",
            postgresql.UUID(),
            sa.ForeignKey("investigation_plans.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "session_id",
            postgresql.UUID(),
            sa.ForeignKey("driving_sessions.id", ondelete="RESTRICT"),
            primary_key=True,
        ),
        sa.Column("recipe_hash", sa.String(64), nullable=False),
        sa.Column("linked_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "recipe_hash ~ '^[0-9a-f]{64}$'", name="ck_investigation_link_recipe_hash"
        ),
    )
    op.create_table(
        "investigation_events",
        sa.Column(
            "investigation_id",
            postgresql.UUID(),
            sa.ForeignKey("investigation_plans.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("sequence", sa.Integer(), primary_key=True),
        sa.Column("snapshot", postgresql.JSONB(), nullable=False),
        sa.CheckConstraint("sequence BETWEEN 1 AND 100", name="ck_investigation_event_sequence"),
        sa.CheckConstraint(
            "octet_length(snapshot::text) <= 32768", name="ck_investigation_event_size"
        ),
    )


def downgrade() -> None:
    op.drop_table("investigation_events")
    op.drop_table("investigation_session_links")
    op.drop_table("investigation_plans")
    op.drop_table("acquisition_source_capabilities")
