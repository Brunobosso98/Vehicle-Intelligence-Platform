"""Agent-owned runs, concise MCP audit and replayable public stream events.

Additive tables only: earlier phase records and the telemetry hypertable are untouched.
Downgrade destroys agent audit records and is intended only for disposable validation.
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "agent_runs",
        sa.Column("id", postgresql.UUID(), primary_key=True),
        sa.Column(
            "vehicle_id",
            postgresql.UUID(),
            sa.ForeignKey("vehicles.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("snapshot", postgresql.JSONB(), nullable=False),
        sa.CheckConstraint(
            "status IN ('running','completed','failed','cancelled')", name="ck_agent_status"
        ),
        sa.CheckConstraint(
            "octet_length(snapshot::text) <= 1048576", name="ck_agent_snapshot_size"
        ),
    )
    op.create_index(
        "ix_agent_vehicle_started", "agent_runs", ["vehicle_id", sa.text("started_at DESC"), "id"]
    )
    op.create_table(
        "agent_tool_calls",
        sa.Column("id", postgresql.UUID(), primary_key=True),
        sa.Column(
            "agent_run_id",
            postgresql.UUID(),
            sa.ForeignKey("agent_runs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("snapshot", postgresql.JSONB(), nullable=False),
        sa.CheckConstraint(
            "octet_length(snapshot::text) <= 16384", name="ck_agent_tool_snapshot_size"
        ),
    )
    op.create_index(
        "ix_agent_tool_run_started", "agent_tool_calls", ["agent_run_id", "started_at", "id"]
    )
    op.create_table(
        "agent_stream_events",
        sa.Column(
            "agent_run_id",
            postgresql.UUID(),
            sa.ForeignKey("agent_runs.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("sequence", sa.Integer(), primary_key=True),
        sa.Column("snapshot", postgresql.JSONB(), nullable=False),
        sa.CheckConstraint("sequence BETWEEN 1 AND 400", name="ck_agent_event_sequence"),
        sa.CheckConstraint("octet_length(snapshot::text) <= 131072", name="ck_agent_event_size"),
    )


def downgrade() -> None:
    op.drop_table("agent_stream_events")
    op.drop_table("agent_tool_calls")
    op.drop_table("agent_runs")
