"""Add bounded, separate Phase 10 control-plane records."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0020"
down_revision = "0019"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "mlops_definitions",
        sa.Column("fingerprint", sa.String(64), primary_key=True),
        sa.Column("definition_version", sa.String(80), nullable=False, unique=True),
        sa.Column("schema_version", sa.String(80), nullable=False),
        sa.Column("body", postgresql.JSONB(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint("fingerprint ~ '^[0-9a-f]{64}$'", name="ck_mlops_definition_hash"),
        sa.CheckConstraint(
            "jsonb_typeof(body)='object' AND octet_length(body::text)<=65536",
            name="ck_mlops_definition_body",
        ),
    )
    op.create_table(
        "mlops_runs",
        sa.Column("id", postgresql.UUID(), primary_key=True),
        sa.Column(
            "parent_run_id",
            postgresql.UUID(),
            sa.ForeignKey("mlops_runs.id", ondelete="RESTRICT"),
        ),
        sa.Column(
            "definition_fingerprint",
            sa.String(64),
            sa.ForeignKey("mlops_definitions.fingerprint", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("logical_fingerprint", sa.String(64), nullable=False),
        sa.Column("attempt", sa.Integer(), nullable=False),
        sa.Column("source_role", sa.String(32), nullable=False),
        sa.Column("state", sa.String(32), nullable=False),
        sa.Column("lease_token", postgresql.UUID()),
        sa.Column("lease_expires_at", sa.DateTime(timezone=True)),
        sa.Column("fencing_token", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint("logical_fingerprint", "attempt", name="uq_mlops_run_attempt"),
        sa.CheckConstraint("logical_fingerprint ~ '^[0-9a-f]{64}$'", name="ck_mlops_run_hash"),
        sa.CheckConstraint("attempt BETWEEN 1 AND 100", name="ck_mlops_run_attempt"),
        sa.CheckConstraint(
            "source_role IN ('synthetic','imported_fixture','imported','real_vehicle')",
            name="ck_mlops_run_source",
        ),
        sa.CheckConstraint(
            "state IN ('PLANNED','QUEUED','CLAIMED','RUNNING','COMPLETED','INSUFFICIENT_SUPPORT','FAILED','CANCELLED','TIMED_OUT','BLOCKED_BY_POLICY')",
            name="ck_mlops_run_state",
        ),
        sa.CheckConstraint(
            "(lease_token IS NULL) = (lease_expires_at IS NULL)",
            name="ck_mlops_run_lease_pair",
        ),
        sa.CheckConstraint("fencing_token >= 0", name="ck_mlops_run_fencing"),
    )
    op.create_index("ix_mlops_runs_logical", "mlops_runs", ["logical_fingerprint", "created_at"])
    op.create_table(
        "mlops_proposals",
        sa.Column("id", postgresql.UUID(), primary_key=True),
        sa.Column(
            "run_id",
            postgresql.UUID(),
            sa.ForeignKey("mlops_runs.id", ondelete="RESTRICT"),
            nullable=False,
            unique=True,
        ),
        sa.Column(
            "definition_fingerprint",
            sa.String(64),
            sa.ForeignKey("mlops_definitions.fingerprint", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("candidate_kind", sa.String(24), nullable=False),
        sa.Column(
            "model_version_id",
            postgresql.UUID(),
            sa.ForeignKey("ml_model_versions.id", ondelete="RESTRICT"),
        ),
        sa.Column(
            "detector_version_id",
            postgresql.UUID(),
            sa.ForeignKey("anomaly_detector_versions.id", ondelete="RESTRICT"),
        ),
        sa.Column("source_role", sa.String(32), nullable=False),
        sa.Column("artifact_checksum", sa.String(64), nullable=False),
        sa.Column("evaluation_checksum", sa.String(64), nullable=False),
        sa.Column("comparison_checksum", sa.String(64)),
        sa.Column("content_checksum", sa.String(64), nullable=False),
        sa.Column("body", postgresql.JSONB(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint(
            "(candidate_kind='supervised' AND model_version_id IS NOT NULL AND detector_version_id IS NULL) "
            "OR (candidate_kind='anomaly' AND model_version_id IS NULL AND detector_version_id IS NOT NULL)",
            name="ck_mlops_proposal_candidate_kind",
        ),
        sa.CheckConstraint("source_role='synthetic'", name="ck_mlops_proposal_source"),
        sa.CheckConstraint(
            "artifact_checksum ~ '^[0-9a-f]{64}$' AND evaluation_checksum ~ '^[0-9a-f]{64}$' "
            "AND content_checksum ~ '^[0-9a-f]{64}$' AND "
            "(comparison_checksum IS NULL OR comparison_checksum ~ '^[0-9a-f]{64}$')",
            name="ck_mlops_proposal_hashes",
        ),
        sa.CheckConstraint(
            "jsonb_typeof(body)='object' AND octet_length(body::text)<=65536",
            name="ck_mlops_proposal_body",
        ),
    )
    op.create_index("ix_mlops_proposal_run", "mlops_proposals", ["run_id"])
    op.create_table(
        "mlops_proposal_events",
        sa.Column("id", postgresql.UUID(), primary_key=True),
        sa.Column(
            "proposal_id",
            postgresql.UUID(),
            sa.ForeignKey("mlops_proposals.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("event_number", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column("state", sa.String(40), nullable=False),
        sa.Column("proposal_checksum", sa.String(64), nullable=False),
        sa.Column("environment", sa.String(20), nullable=False),
        sa.Column("reviewer_id", sa.String(120)),
        sa.Column("reviewer_role", sa.String(80)),
        sa.Column("reason", sa.String(500), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint("event_number", name="uq_mlops_proposal_event_number"),
        sa.CheckConstraint(
            "state IN ('DRAFT','EVALUATING','EVALUATED','REVIEW_REQUIRED',"
            "'APPROVED_FOR_CONTROLLED_REVIEW','REJECTED','ARCHIVED')",
            name="ck_mlops_proposal_event_state",
        ),
        sa.CheckConstraint(
            "proposal_checksum ~ '^[0-9a-f]{64}$'",
            name="ck_mlops_proposal_event_hash",
        ),
        sa.CheckConstraint(
            "environment IN ('development','test')", name="ck_mlops_proposal_event_environment"
        ),
        sa.CheckConstraint(
            "(state IN ('DRAFT','EVALUATING','EVALUATED','REVIEW_REQUIRED') "
            "AND reviewer_id IS NULL AND reviewer_role IS NULL) OR "
            "(state IN ('APPROVED_FOR_CONTROLLED_REVIEW','REJECTED','ARCHIVED') "
            "AND length(trim(reviewer_id)) BETWEEN 2 AND 120 "
            "AND reviewer_role='mlops_reviewer')",
            name="ck_mlops_proposal_event_reviewer",
        ),
        sa.CheckConstraint(
            "length(trim(reason)) BETWEEN 8 AND 500", name="ck_mlops_proposal_event_reason"
        ),
    )
    op.create_index(
        "ix_mlops_proposal_events_proposal",
        "mlops_proposal_events",
        ["proposal_id", "event_number"],
    )
    op.create_table(
        "mlops_rollback_plans",
        sa.Column("id", postgresql.UUID(), primary_key=True),
        sa.Column(
            "proposal_id",
            postgresql.UUID(),
            sa.ForeignKey("mlops_proposals.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "target_binding_id",
            postgresql.UUID(),
            sa.ForeignKey("prediction_serving_bindings.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "target_event_id",
            postgresql.UUID(),
            sa.ForeignKey("prediction_serving_events.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("state", sa.String(40), nullable=False),
        sa.Column("content_checksum", sa.String(64), nullable=False),
        sa.Column("body", postgresql.JSONB(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint("content_checksum", name="uq_mlops_rollback_plan_checksum"),
        sa.CheckConstraint(
            "state IN ('READY_FOR_SEPARATE_9D_REVIEW','BLOCKED')",
            name="ck_mlops_rollback_plan_state",
        ),
        sa.CheckConstraint(
            "content_checksum ~ '^[0-9a-f]{64}$'",
            name="ck_mlops_rollback_plan_hash",
        ),
        sa.CheckConstraint(
            "jsonb_typeof(body)='object' AND octet_length(body::text)<=65536",
            name="ck_mlops_rollback_plan_body",
        ),
    )
    op.create_index("ix_mlops_rollback_plan_binding", "mlops_rollback_plans", ["target_binding_id"])
    op.create_table(
        "mlops_run_events",
        sa.Column("id", postgresql.UUID(), primary_key=True),
        sa.Column(
            "run_id",
            postgresql.UUID(),
            sa.ForeignKey("mlops_runs.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "event_number",
            sa.BigInteger(),
            sa.Identity(always=True),
            nullable=False,
            unique=True,
        ),
        sa.Column("from_state", sa.String(32)),
        sa.Column("to_state", sa.String(32), nullable=False),
        sa.Column("reason", sa.String(80), nullable=False),
        sa.Column("fencing_token", sa.BigInteger(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint("fencing_token >= 0", name="ck_mlops_event_fence"),
        sa.CheckConstraint("reason ~ '^[A-Z][A-Z0-9_]{0,79}$'", name="ck_mlops_event_reason"),
    )
    op.create_table(
        "mlops_step_events",
        sa.Column("id", postgresql.UUID(), primary_key=True),
        sa.Column(
            "run_id",
            postgresql.UUID(),
            sa.ForeignKey("mlops_runs.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "checkpoint_source_run_id",
            postgresql.UUID(),
            sa.ForeignKey("mlops_runs.id", ondelete="RESTRICT"),
        ),
        sa.Column(
            "event_number",
            sa.BigInteger(),
            sa.Identity(always=True),
            nullable=False,
            unique=True,
        ),
        sa.Column("step_name", sa.String(40), nullable=False),
        sa.Column("step_attempt", sa.Integer(), nullable=False),
        sa.Column("state", sa.String(32), nullable=False),
        sa.Column("input_checksum", sa.String(64), nullable=False),
        sa.Column("output_checksum", sa.String(64)),
        sa.Column(
            "output_body",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("fencing_token", sa.BigInteger(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint(
            "step_name IN ('select','validate','fit','verify_artifact','evaluate','compare','report')",
            name="ck_mlops_step_name",
        ),
        sa.CheckConstraint(
            "state IN ('PENDING','RUNNING','SUCCEEDED','SKIPPED_INELIGIBLE','FAILED','CANCELLED')",
            name="ck_mlops_step_state",
        ),
        sa.CheckConstraint("step_attempt BETWEEN 1 AND 100", name="ck_mlops_step_attempt"),
        sa.CheckConstraint(
            "input_checksum ~ '^[0-9a-f]{64}$' AND (output_checksum IS NULL OR output_checksum ~ '^[0-9a-f]{64}$')",
            name="ck_mlops_step_checksum",
        ),
        sa.CheckConstraint(
            "jsonb_typeof(output_body)='object' AND octet_length(output_body::text)<=65536",
            name="ck_mlops_step_body",
        ),
    )
    op.create_index("ix_mlops_step_events_run", "mlops_step_events", ["run_id", "event_number"])
    op.execute(
        "CREATE FUNCTION reject_immutable_mlops_mutation() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'Phase 10 records are immutable'; END $$"
    )
    for table in (
        "mlops_definitions",
        "mlops_run_events",
        "mlops_step_events",
        "mlops_proposals",
        "mlops_proposal_events",
        "mlops_rollback_plans",
    ):
        op.execute(
            f"CREATE TRIGGER trg_{table}_immutable BEFORE UPDATE OR DELETE ON {table} FOR EACH ROW EXECUTE FUNCTION reject_immutable_mlops_mutation()"
        )
        op.execute(
            f"CREATE TRIGGER trg_{table}_no_truncate BEFORE TRUNCATE ON {table} FOR EACH STATEMENT EXECUTE FUNCTION reject_immutable_mlops_mutation()"
        )
    op.execute(
        "CREATE FUNCTION protect_final_mlops_run() RETURNS trigger LANGUAGE plpgsql AS $$ "
        "DECLARE transition_allowed boolean := false; BEGIN "
        "IF TG_OP = 'DELETE' OR OLD.state IN "
        "('COMPLETED','INSUFFICIENT_SUPPORT','FAILED','CANCELLED','TIMED_OUT','BLOCKED_BY_POLICY') "
        "THEN RAISE EXCEPTION 'final Phase 10 runs are immutable'; END IF; "
        "IF ROW(NEW.id,NEW.definition_fingerprint,NEW.logical_fingerprint,NEW.attempt,"
        "NEW.source_role,NEW.parent_run_id,NEW.created_at) IS DISTINCT FROM ROW(OLD.id,OLD.definition_fingerprint,"
        "OLD.logical_fingerprint,OLD.attempt,OLD.source_role,OLD.parent_run_id,OLD.created_at) "
        "THEN RAISE EXCEPTION 'Phase 10 run identity is immutable'; END IF; "
        "IF NEW.fencing_token < OLD.fencing_token OR NEW.fencing_token > OLD.fencing_token + 1 "
        "THEN RAISE EXCEPTION 'Phase 10 fencing token is invalid'; END IF; "
        "IF NEW.state <> OLD.state THEN transition_allowed := "
        "(OLD.state='PLANNED' AND NEW.state IN ('QUEUED','CLAIMED','CANCELLED')) OR "
        "(OLD.state='QUEUED' AND NEW.state IN ('CLAIMED','CANCELLED','FAILED')) OR "
        "(OLD.state='CLAIMED' AND NEW.state IN ('RUNNING','CANCELLED','FAILED')) OR "
        "(OLD.state='RUNNING' AND NEW.state IN ('COMPLETED','INSUFFICIENT_SUPPORT','FAILED',"
        "'CANCELLED','TIMED_OUT','BLOCKED_BY_POLICY')); "
        "IF NOT transition_allowed THEN RAISE EXCEPTION 'invalid Phase 10 run state transition'; END IF; "
        "END IF; RETURN NEW; END $$"
    )
    op.execute(
        "CREATE TRIGGER trg_mlops_run_final BEFORE UPDATE OR DELETE ON mlops_runs FOR EACH ROW EXECUTE FUNCTION protect_final_mlops_run()"
    )
    op.execute(
        "CREATE TRIGGER trg_mlops_run_no_truncate BEFORE TRUNCATE ON mlops_runs FOR EACH STATEMENT EXECUTE FUNCTION reject_immutable_mlops_mutation()"
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER trg_mlops_run_no_truncate ON mlops_runs")
    op.execute("DROP TRIGGER trg_mlops_run_final ON mlops_runs")
    op.execute("DROP FUNCTION protect_final_mlops_run()")
    for table in (
        "mlops_rollback_plans",
        "mlops_proposal_events",
        "mlops_proposals",
        "mlops_step_events",
        "mlops_run_events",
        "mlops_definitions",
    ):
        op.execute(f"DROP TRIGGER trg_{table}_no_truncate ON {table}")
        op.execute(f"DROP TRIGGER trg_{table}_immutable ON {table}")
    op.execute("DROP FUNCTION reject_immutable_mlops_mutation()")
    op.drop_index("ix_mlops_rollback_plan_binding", table_name="mlops_rollback_plans")
    op.drop_table("mlops_rollback_plans")
    op.drop_index("ix_mlops_proposal_events_proposal", table_name="mlops_proposal_events")
    op.drop_table("mlops_proposal_events")
    op.drop_index("ix_mlops_proposal_run", table_name="mlops_proposals")
    op.drop_table("mlops_proposals")
    op.drop_index("ix_mlops_step_events_run", table_name="mlops_step_events")
    op.drop_table("mlops_step_events")
    op.drop_table("mlops_run_events")
    op.drop_index("ix_mlops_runs_logical", table_name="mlops_runs")
    op.drop_table("mlops_runs")
    op.drop_table("mlops_definitions")
