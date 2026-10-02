"""Persist provisional findings, reconciliation, and post-log capability evidence."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "provisional_findings",
        sa.Column(
            "id", postgresql.UUID(), primary_key=True, server_default=sa.text("gen_random_uuid()")
        ),
        sa.Column(
            "acquisition_session_id",
            postgresql.UUID(),
            sa.ForeignKey("acquisition_sessions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("finding_type", sa.String(80), nullable=False),
        sa.Column("category", sa.String(40), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ended_at", sa.DateTime(timezone=True)),
        sa.Column("status", sa.String(24), nullable=False, server_default="provisional"),
        sa.Column("evidence", postgresql.JSONB(), nullable=False),
        sa.Column("canonical_reference", postgresql.UUID()),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.CheckConstraint(
            "status IN ('provisional','confirmed','boundary_adjusted','merged','changed','absent')",
            name="ck_provisional_reconciliation",
        ),
    )
    op.create_index(
        "ix_provisional_session_time",
        "provisional_findings",
        ["acquisition_session_id", "started_at"],
    )
    op.create_table(
        "dataset_capability_reports",
        sa.Column(
            "id", postgresql.UUID(), primary_key=True, server_default=sa.text("gen_random_uuid()")
        ),
        sa.Column(
            "driving_session_id",
            postgresql.UUID(),
            sa.ForeignKey("driving_sessions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("recipe_key", sa.String(80), nullable=False),
        sa.Column("recipe_configuration_hash", sa.String(64), nullable=False),
        sa.Column("duration_seconds", sa.Float(), nullable=False),
        sa.Column("report", postgresql.JSONB(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.UniqueConstraint(
            "driving_session_id", "recipe_configuration_hash", name="uq_dataset_capability_recipe"
        ),
    )


def downgrade() -> None:
    op.drop_table("dataset_capability_reports")
    op.drop_table("provisional_findings")
