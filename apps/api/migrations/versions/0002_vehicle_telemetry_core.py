"""Vehicle domain and canonical telemetry hypertable.

Indexes match session/signal/time and vehicle/time window reads. No retention or compression
policy is installed: raw observations are preserved until measured operations justify one.
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE TYPE session_status AS ENUM ('pending','ingesting','completed','failed')")
    op.create_table(
        "vehicles",
        sa.Column(
            "id", postgresql.UUID(), server_default=sa.text("gen_random_uuid()"), primary_key=True
        ),
        sa.Column("vin", sa.String(17), unique=True),
        sa.Column("manufacturer", sa.String(80), nullable=False),
        sa.Column("model", sa.String(80), nullable=False),
        sa.Column("generation", sa.String(40)),
        sa.Column("model_year", sa.SmallInteger()),
        sa.Column("engine_code", sa.String(40)),
        sa.Column("transmission", sa.String(80)),
        sa.Column("nickname", sa.String(80)),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_table(
        "vehicle_configurations",
        sa.Column(
            "id", postgresql.UUID(), server_default=sa.text("gen_random_uuid()"), primary_key=True
        ),
        sa.Column(
            "vehicle_id",
            postgresql.UUID(),
            sa.ForeignKey("vehicles.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("effective_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ended_at", sa.DateTime(timezone=True)),
        sa.Column("description", sa.String(500), nullable=False),
        sa.Column(
            "metadata", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb"), nullable=False
        ),
        sa.Column("provenance", sa.String(120), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("ended_at IS NULL OR ended_at > effective_at"),
    )
    op.create_index(
        "ix_configuration_vehicle_effective",
        "vehicle_configurations",
        ["vehicle_id", sa.text("effective_at DESC")],
    )
    op.create_table(
        "modifications",
        sa.Column(
            "id", postgresql.UUID(), server_default=sa.text("gen_random_uuid()"), primary_key=True
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
        sa.Column("category", sa.String(80), nullable=False),
        sa.Column("manufacturer", sa.String(80)),
        sa.Column("product", sa.String(120)),
        sa.Column("installed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("removed_at", sa.DateTime(timezone=True)),
        sa.Column("notes", sa.String(1000)),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("removed_at IS NULL OR removed_at > installed_at"),
    )
    op.create_table(
        "driving_sessions",
        sa.Column(
            "id", postgresql.UUID(), server_default=sa.text("gen_random_uuid()"), primary_key=True
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
        sa.Column("source_type", sa.String(20), nullable=False),
        sa.Column("source_reference", sa.String(255)),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("ended_at", sa.DateTime(timezone=True)),
        sa.Column("source_timezone", sa.String(80)),
        sa.Column("sample_count", sa.BigInteger(), server_default="0", nullable=False),
        sa.Column(
            "status",
            postgresql.ENUM(name="session_status", create_type=False),
            server_default="pending",
            nullable=False,
        ),
        sa.Column(
            "metadata", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb"), nullable=False
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("ended_at IS NULL OR started_at IS NULL OR ended_at >= started_at"),
    )
    op.create_index(
        "ix_sessions_vehicle_started",
        "driving_sessions",
        ["vehicle_id", sa.text("started_at DESC")],
    )
    op.create_table(
        "telemetry_samples",
        sa.Column("sample_id", sa.String(64), nullable=False),
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
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "ingested_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("signal_key", sa.String(120), nullable=False),
        sa.Column("numeric_value", sa.Float(), nullable=False),
        sa.Column("normalized_unit", sa.String(20), nullable=False),
        sa.Column("raw_signal", sa.String(120), nullable=False),
        sa.Column("raw_value", sa.Text()),
        sa.Column("source", sa.String(30), nullable=False),
        sa.Column("source_record_id", sa.String(255), nullable=False),
        sa.Column("sequence_number", sa.BigInteger()),
        sa.Column("quality", sa.String(30), nullable=False),
        sa.Column("schema_version", sa.SmallInteger(), nullable=False),
        sa.Column(
            "source_metadata",
            postgresql.JSONB(),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.PrimaryKeyConstraint("sample_id", "observed_at"),
    )
    op.execute(
        "SELECT create_hypertable('telemetry_samples', 'observed_at', "
        "if_not_exists => TRUE, chunk_time_interval => INTERVAL '1 day')"
    )
    op.create_index(
        "ix_telemetry_session_signal_time",
        "telemetry_samples",
        ["session_id", "signal_key", sa.text("observed_at DESC")],
    )
    op.create_index(
        "ix_telemetry_vehicle_time",
        "telemetry_samples",
        ["vehicle_id", sa.text("observed_at DESC")],
    )
    op.execute("CREATE INDEX ix_telemetry_sample_identity ON telemetry_samples(sample_id)")


def downgrade() -> None:
    op.drop_table("telemetry_samples")
    op.drop_table("driving_sessions")
    op.drop_table("modifications")
    op.drop_table("vehicle_configurations")
    op.drop_table("vehicles")
    op.execute("DROP TYPE session_status")
