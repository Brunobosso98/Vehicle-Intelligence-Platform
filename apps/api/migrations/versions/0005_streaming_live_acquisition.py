"""Add durable live acquisition lifecycle and idempotent stream receipt."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "acquisition_sessions",
        sa.Column(
            "id", postgresql.UUID(), primary_key=True, server_default=sa.text("gen_random_uuid()")
        ),
        sa.Column(
            "driving_session_id",
            postgresql.UUID(),
            sa.ForeignKey("driving_sessions.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("recipe_key", sa.String(80), nullable=False),
        sa.Column("recipe_version", sa.Integer(), nullable=False),
        sa.Column("recipe_configuration_hash", sa.String(64), nullable=False),
        sa.Column("adapter", sa.String(80), nullable=False),
        sa.Column("state", sa.String(24), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("token_expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_sequence", sa.BigInteger()),
        sa.Column("quality", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column(
            "started_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column("ended_at", sa.DateTime(timezone=True)),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.CheckConstraint(
            "state IN ('created','active','disconnected','stopping','finalizing','completed','failed')",
            name="ck_acquisition_state",
        ),
    )
    op.create_table(
        "stream_receipts",
        sa.Column("message_id", postgresql.UUID(), primary_key=True),
        sa.Column(
            "acquisition_session_id",
            postgresql.UUID(),
            sa.ForeignKey("acquisition_sessions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("topic", sa.String(100), nullable=False),
        sa.Column("partition", sa.Integer()),
        sa.Column("offset", sa.BigInteger()),
        sa.Column(
            "received_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )
    op.create_index(
        "ix_stream_receipts_session", "stream_receipts", ["acquisition_session_id", "received_at"]
    )


def downgrade() -> None:
    op.drop_table("stream_receipts")
    op.drop_table("acquisition_sessions")
