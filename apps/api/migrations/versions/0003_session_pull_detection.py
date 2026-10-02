"""Persist versioned derived session segments and pulls."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    def common() -> tuple[sa.Column[object], ...]:
        return (
            sa.Column(
                "id",
                postgresql.UUID(),
                server_default=sa.text("gen_random_uuid()"),
                primary_key=True,
            ),
            sa.Column(
                "session_id",
                postgresql.UUID(),
                sa.ForeignKey("driving_sessions.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("ended_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("duration_ms", sa.BigInteger(), nullable=False),
            sa.Column("confidence", sa.Float(), nullable=False),
            sa.Column("detector_name", sa.String(80), nullable=False),
            sa.Column("algorithm_version", sa.String(80), nullable=False),
            sa.Column("configuration_hash", sa.String(64), nullable=False),
            sa.Column(
                "quality_flags",
                postgresql.ARRAY(sa.String(80)),
                server_default="{}",
                nullable=False,
            ),
            sa.Column(
                "metadata",
                postgresql.JSONB(),
                server_default=sa.text("'{}'::jsonb"),
                nullable=False,
            ),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("now()"),
                nullable=False,
            ),
            sa.CheckConstraint("ended_at > started_at"),
            sa.CheckConstraint("confidence >= 0 AND confidence <= 1"),
        )

    op.create_table(
        "session_segments",
        *common(),
        sa.Column("segment_type", sa.String(30), nullable=False),
        sa.Column("start_sample_id", sa.String(64)),
        sa.Column("end_sample_id", sa.String(64)),
        sa.UniqueConstraint(
            "session_id",
            "detector_name",
            "algorithm_version",
            "configuration_hash",
            "started_at",
            "segment_type",
            name="uq_segment_analysis_identity",
        ),
    )
    op.create_index("ix_segments_session_start", "session_segments", ["session_id", "started_at"])
    op.create_index("ix_segments_session_type", "session_segments", ["session_id", "segment_type"])
    op.create_index(
        "ix_segments_detector_version", "session_segments", ["detector_name", "algorithm_version"]
    )
    op.create_table(
        "pulls",
        *common(),
        sa.Column(
            "segment_id",
            postgresql.UUID(),
            sa.ForeignKey("session_segments.id", ondelete="SET NULL"),
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
        *[
            sa.Column(name, sa.Float())
            for name in (
                "start_rpm",
                "end_rpm",
                "min_rpm",
                "max_rpm",
                "start_speed",
                "end_speed",
                "max_speed",
                "max_boost",
                "average_boost",
                "start_iat",
                "end_iat",
                "iat_delta",
                "max_oil_temperature",
                "max_coolant_temperature",
                "average_throttle",
                "max_throttle",
                "data_completeness",
            )
        ],
        sa.Column("sample_count", sa.Integer(), nullable=False),
        sa.UniqueConstraint(
            "session_id",
            "detector_name",
            "algorithm_version",
            "configuration_hash",
            "started_at",
            name="uq_pull_analysis_identity",
        ),
    )
    op.create_index("ix_pulls_session_start", "pulls", ["session_id", "started_at"])
    op.create_index(
        "ix_pulls_vehicle_configuration_start",
        "pulls",
        ["vehicle_id", "configuration_id", "started_at"],
    )
    op.create_index("ix_pulls_detector_version", "pulls", ["detector_name", "algorithm_version"])


def downgrade() -> None:
    op.drop_table("pulls")
    op.drop_table("session_segments")
