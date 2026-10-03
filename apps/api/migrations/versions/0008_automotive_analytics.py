"""Persist immutable, versioned Phase 5 analytics results."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "analytics_runs",
        sa.Column(
            "id", postgresql.UUID(), primary_key=True, server_default=sa.text("gen_random_uuid()")
        ),
        sa.Column("analytics_type", sa.String(40), nullable=False),
        sa.Column("algorithm_name", sa.String(100), nullable=False),
        sa.Column("algorithm_version", sa.String(40), nullable=False),
        sa.Column("configuration_hash", sa.String(64), nullable=False),
        sa.Column("source_fingerprint", sa.String(64), nullable=False),
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
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("warnings", postgresql.ARRAY(sa.Text()), nullable=False, server_default="{}"),
        sa.Column("input_summary", postgresql.JSONB(), nullable=False),
        sa.Column("result", postgresql.JSONB(), nullable=False),
        sa.Column(
            "generated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.CheckConstraint(
            "status IN ('completed','limited','insufficient','failed')",
            name="ck_analytics_run_status",
        ),
    )
    op.create_index(
        "ix_analytics_vehicle_type_generated",
        "analytics_runs",
        ["vehicle_id", "analytics_type", "generated_at"],
    )
    op.create_index(
        "ix_analytics_configuration_generated",
        "analytics_runs",
        ["configuration_id", "generated_at"],
    )
    op.create_index(
        "ix_analytics_identity",
        "analytics_runs",
        ["analytics_type", "algorithm_version", "configuration_hash", "source_fingerprint"],
    )


def downgrade() -> None:
    op.drop_table("analytics_runs")
