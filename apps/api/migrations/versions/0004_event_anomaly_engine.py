"""Persist versioned Phase 3 event analysis runs and factual detected events."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "event_analysis_runs",
        sa.Column(
            "id", postgresql.UUID(), primary_key=True, server_default=sa.text("gen_random_uuid()")
        ),
        sa.Column(
            "session_id",
            postgresql.UUID(),
            sa.ForeignKey("driving_sessions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("profile", sa.String(80), nullable=False),
        sa.Column("configuration_hash", sa.String(64), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("detector_states", postgresql.JSONB(), nullable=False),
        sa.Column("event_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("warnings", postgresql.ARRAY(sa.Text()), nullable=False, server_default="{}"),
        sa.Column(
            "started_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column("finished_at", sa.DateTime(timezone=True)),
        sa.CheckConstraint("event_count >= 0", name="ck_event_run_count"),
    )
    op.create_index(
        "ix_event_runs_session_started", "event_analysis_runs", ["session_id", "started_at"]
    )
    op.create_table(
        "detected_events",
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
            "session_id",
            postgresql.UUID(),
            sa.ForeignKey("driving_sessions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "segment_id",
            postgresql.UUID(),
            sa.ForeignKey("session_segments.id", ondelete="SET NULL"),
        ),
        sa.Column("pull_id", postgresql.UUID(), sa.ForeignKey("pulls.id", ondelete="SET NULL")),
        sa.Column(
            "analysis_run_id",
            postgresql.UUID(),
            sa.ForeignKey("event_analysis_runs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("event_type", sa.String(80), nullable=False),
        sa.Column("category", sa.String(40), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("duration_ms", sa.BigInteger(), nullable=False),
        sa.Column("severity", sa.String(16), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("algorithm_name", sa.String(100), nullable=False),
        sa.Column("algorithm_version", sa.String(40), nullable=False),
        sa.Column("configuration_hash", sa.String(64), nullable=False),
        sa.Column("baseline_type", sa.String(50), nullable=False),
        sa.Column("baseline_reference", postgresql.JSONB(), nullable=False),
        sa.Column("evidence", postgresql.JSONB(), nullable=False),
        sa.Column(
            "quality_flags", postgresql.ARRAY(sa.Text()), nullable=False, server_default="{}"
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.CheckConstraint("ended_at >= started_at", name="ck_detected_event_time"),
        sa.CheckConstraint("duration_ms >= 0", name="ck_detected_event_duration"),
        sa.CheckConstraint(
            "confidence >= 0 AND confidence <= 1", name="ck_detected_event_confidence"
        ),
        sa.CheckConstraint(
            "severity IN ('info','low','moderate','high')", name="ck_detected_event_severity"
        ),
        sa.UniqueConstraint(
            "session_id",
            "algorithm_name",
            "algorithm_version",
            "configuration_hash",
            "event_type",
            "started_at",
            "ended_at",
            name="uq_detected_event_identity",
        ),
    )
    op.create_index("ix_events_session_start", "detected_events", ["session_id", "started_at"])
    op.create_index("ix_events_session_type", "detected_events", ["session_id", "event_type"])
    op.create_index("ix_events_vehicle_start", "detected_events", ["vehicle_id", "started_at"])
    op.create_index("ix_events_pull", "detected_events", ["pull_id", "started_at"])


def downgrade() -> None:
    op.drop_table("detected_events")
    op.drop_table("event_analysis_runs")
