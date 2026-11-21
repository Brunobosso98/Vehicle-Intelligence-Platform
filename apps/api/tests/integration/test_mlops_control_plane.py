"""Disposable PostgreSQL tests for Phase 10 control-plane ownership."""

import asyncio
import os
from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from vehicle_platform.core.config import Settings
from vehicle_platform.evaluation.contracts import SourceRole
from vehicle_platform.features.domain import stable_hash
from vehicle_platform.infrastructure.database import Database
from vehicle_platform.ml.domain import MLTask
from vehicle_platform.mlops.contracts import PipelineDefinition, PipelineKind, RunState
from vehicle_platform.mlops.repository import ControlPlaneConflict, ControlPlaneRepository

pytestmark = pytest.mark.integration
api = Path(__file__).resolve().parents[2]


@pytest.fixture
async def migrated_database_url() -> AsyncIterator[str]:
    url = os.environ.get("TEST_DATABASE_URL", "")
    assert url.rsplit("/", 1)[-1].startswith("vehicle_test")
    env = os.environ | {"DATABASE_URL": url, "ENVIRONMENT": "test"}
    alembic = str(api / ".venv/bin/alembic")
    upgrade = await asyncio.create_subprocess_exec(
        alembic,
        "upgrade",
        "head",
        cwd=api,
        env=env,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await upgrade.communicate()
    assert upgrade.returncode == 0, (stdout.decode(), stderr.decode())
    try:
        yield url
    finally:
        downgrade = await asyncio.create_subprocess_exec(
            alembic,
            "downgrade",
            "base",
            cwd=api,
            env=env,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await downgrade.communicate()
        assert downgrade.returncode == 0, (stdout.decode(), stderr.decode())


@pytest.mark.asyncio
async def test_control_plane_idempotence_claim_and_immutable_history(
    migrated_database_url: str,
) -> None:
    url = migrated_database_url
    database = Database(Settings(database_url=url, environment="test"))
    definition = PipelineDefinition(
        definition_version="integration-v1",
        kind=PipelineKind.SUPERVISED,
        task=MLTask.THERMAL_DEGRADATION,
        source_role=SourceRole.SYNTHETIC,
        cutoff=datetime(2026, 1, 1, tzinfo=UTC),
        git_sha="a" * 40,
        expected_source_fingerprint="b" * 64,
        expected_dataset_checksum="d" * 64,
        expected_feature_checksum="c" * 64,
        evaluation_cutoff=datetime(2026, 1, 1, tzinfo=UTC) + timedelta(days=1),
        evaluation_pull_ids=(uuid4(),),
        expected_evaluation_checksum="e" * 64,
        expected_evaluation_source_fingerprint="f" * 64,
    )
    repo = ControlPlaneRepository(database)
    try:
        first, second = await asyncio.gather(
            repo.create_run(definition), repo.create_run(definition)
        )
        assert first[0] == second[0]
        assert {first[1], second[1]} == {True, False}
        claims = await asyncio.gather(
            repo.claim(first[0]), repo.claim(first[0]), return_exceptions=True
        )
        accepted = [claim for claim in claims if isinstance(claim, tuple)]
        assert len(accepted) == 1
        assert sum(isinstance(claim, ControlPlaneConflict) for claim in claims) == 1
        token, fence = accepted[0]
        await repo.transition(
            first[0],
            token=token,
            fence=fence,
            expected=RunState.CLAIMED,
            target=RunState.RUNNING,
            reason="STARTED",
        )
        step = {
            "run_id": first[0],
            "token": token,
            "fence": fence,
            "attempt": 1,
            "input_checksum": "a" * 64,
        }
        with pytest.raises(ControlPlaneConflict):
            await repo.record_step(**step, name="fit", state="RUNNING")
        await repo.record_step(**step, name="select", state="RUNNING")
        with pytest.raises(ControlPlaneConflict):
            await repo.record_step(
                **{**step, "fence": fence + 1}, name="select", state="SUCCEEDED", output={"rows": 1}
            )
        await repo.record_step(**step, name="select", state="SUCCEEDED", output={"rows": 1})
        await repo.record_step(**step, name="validate", state="RUNNING")
        await repo.record_step(
            **step, name="validate", state="SUCCEEDED", output={"eligible": True}
        )
        with pytest.raises(ControlPlaneConflict):
            await repo.transition(
                first[0],
                token=token,
                fence=fence,
                expected=RunState.RUNNING,
                target=RunState.COMPLETED,
                reason="DONE",
            )
        await repo.transition(
            first[0],
            token=token,
            fence=fence,
            expected=RunState.RUNNING,
            target=RunState.FAILED,
            reason="MISSING_EVALUATION",
        )
        async with database.session() as db:
            events = (
                await db.execute(
                    text(
                        "SELECT from_state,to_state FROM mlops_run_events "
                        "WHERE run_id=:id ORDER BY event_number"
                    ),
                    {"id": first[0]},
                )
            ).all()
        assert [(row[0], row[1]) for row in events] == [
            (None, "PLANNED"),
            ("PLANNED", "CLAIMED"),
            ("CLAIMED", "RUNNING"),
            ("RUNNING", "FAILED"),
        ]
        inspection = await repo.inspect_run(first[0])
        assert inspection["run"]["state"] == "FAILED"
        assert "lease_token" not in inspection["run"]
        assert len(inspection["events"]) == 4
        for sql in (
            "UPDATE mlops_run_events SET reason='CHANGED' WHERE run_id=:id",
            "DELETE FROM mlops_step_events WHERE run_id=:id",
            "UPDATE mlops_runs SET state='RUNNING' WHERE id=:id",
        ):
            with pytest.raises(DBAPIError):
                async with database.session() as db, db.begin():
                    await db.execute(text(sql), {"id": first[0]})

        recovery_definition = definition.model_copy(update={"definition_version": "recovery-v1"})
        recovery_id, _ = await repo.create_run(recovery_definition)
        for sql in (
            "UPDATE mlops_runs SET logical_fingerprint=:hash WHERE id=:id",
            "UPDATE mlops_runs SET state='COMPLETED' WHERE id=:id",
        ):
            with pytest.raises(DBAPIError):
                async with database.session() as db, db.begin():
                    await db.execute(text(sql), {"id": recovery_id, "hash": "f" * 64})
        recovery_token, recovery_fence = await repo.claim(recovery_id)
        with pytest.raises(ControlPlaneConflict):
            await repo.fail_expired_run(recovery_id)
        async with database.session() as db, db.begin():
            await db.execute(
                text(
                    "UPDATE mlops_runs SET lease_expires_at=now()-interval '1 second' WHERE id=:id"
                ),
                {"id": recovery_id},
            )
        await repo.fail_expired_run(recovery_id)
        with pytest.raises(ControlPlaneConflict):
            await repo.heartbeat(recovery_id, token=recovery_token, fence=recovery_fence)
        with pytest.raises(ControlPlaneConflict):
            await repo.fail_expired_run(recovery_id)
        async with database.session() as db:
            recovered = (
                await db.execute(
                    text(
                        "SELECT r.state,r.fencing_token,e.reason FROM mlops_runs r "
                        "JOIN mlops_run_events e ON e.run_id=r.id WHERE r.id=:id "
                        "ORDER BY e.event_number DESC LIMIT 1"
                    ),
                    {"id": recovery_id},
                )
            ).one()
        assert tuple(recovered) == ("FAILED", recovery_fence + 1, "LEASE_EXPIRED_UNRECONCILED")

        checkpoint_definition = definition.model_copy(
            update={"definition_version": "checkpoint-retry-v1"}
        )
        checkpoint_run, _ = await repo.create_run(checkpoint_definition)
        checkpoint_token, checkpoint_fence = await repo.claim(checkpoint_run)
        await repo.transition(
            checkpoint_run,
            token=checkpoint_token,
            fence=checkpoint_fence,
            expected=RunState.CLAIMED,
            target=RunState.RUNNING,
            reason="STARTED",
        )
        select_output = {
            "source_role": "synthetic",
            "dataset_checksum": "d" * 64,
            "evaluation_dataset_checksum": "e" * 64,
            "row_count": 12,
            "evaluation_row_count": 4,
        }
        validate_output = {
            "plan_fingerprint": checkpoint_definition.fingerprint,
            "plan_status": "READY_TO_REVIEW",
            "plan_reason": "ELIGIBLE",
            "feature_checksum": "a" * 64,
            "label_checksum": "b" * 64,
            "training_source_fingerprint": "c" * 64,
            "evaluation_source_fingerprint": "f" * 64,
        }
        for step_name, input_hash, output in (
            ("select", checkpoint_definition.expected_source_fingerprint, select_output),
            ("validate", checkpoint_definition.fingerprint, validate_output),
        ):
            await repo.record_step(
                checkpoint_run,
                token=checkpoint_token,
                fence=checkpoint_fence,
                name=step_name,
                attempt=1,
                state="RUNNING",
                input_checksum=input_hash,
            )
            await repo.record_step(
                checkpoint_run,
                token=checkpoint_token,
                fence=checkpoint_fence,
                name=step_name,
                attempt=1,
                state="SUCCEEDED",
                input_checksum=input_hash,
                output=output,
            )
        async with database.session() as db, db.begin():
            await db.execute(
                text(
                    "UPDATE mlops_runs SET lease_expires_at=now()-interval '1 second' WHERE id=:id"
                ),
                {"id": checkpoint_run},
            )
        await repo.fail_expired_run(checkpoint_run)
        retry_id, retry_created = await repo.create_checkpoint_retry(checkpoint_run)
        duplicate_retry_id, duplicate_retry_created = await repo.create_checkpoint_retry(
            checkpoint_run
        )
        assert retry_created and not duplicate_retry_created
        assert duplicate_retry_id == retry_id
        retry_inspection = await repo.inspect_run(retry_id)
        assert retry_inspection["run"]["parent_run_id"] == checkpoint_run
        assert [item["step_name"] for item in retry_inspection["steps"]] == [
            "select",
            "validate",
        ]
        assert all(
            item["state"] == "SUCCEEDED" and item["checkpoint_source_run_id"] == checkpoint_run
            for item in retry_inspection["steps"]
        )
        retry_token, retry_fence = await repo.claim(retry_id)
        await repo.transition(
            retry_id,
            token=retry_token,
            fence=retry_fence,
            expected=RunState.CLAIMED,
            target=RunState.RUNNING,
            reason="RETRY_STARTED",
        )
        await repo.record_step(
            retry_id,
            token=retry_token,
            fence=retry_fence,
            name="fit",
            attempt=1,
            state="RUNNING",
            input_checksum=checkpoint_definition.expected_dataset_checksum,
        )
        await repo.transition(
            retry_id,
            token=retry_token,
            fence=retry_fence,
            expected=RunState.RUNNING,
            target=RunState.CANCELLED,
            reason="CHECKPOINT_REPLAY_TEST",
        )

        final_definition = definition.model_copy(update={"definition_version": "final-v1"})
        final_id, _ = await repo.create_run(final_definition)
        final_token, final_fence = await repo.claim(final_id)
        await repo.transition(
            final_id,
            token=final_token,
            fence=final_fence,
            expected=RunState.CLAIMED,
            target=RunState.RUNNING,
            reason="STARTED",
        )
        with pytest.raises(ControlPlaneConflict, match="receipts are incomplete"):
            await repo.complete_run(final_id, token=final_token, fence=final_fence)
        outputs = {
            "select": {"source_role": "synthetic"},
            "validate": {"plan_status": "READY_TO_REVIEW"},
            "fit": {"artifact_checksum": "a" * 64},
            "verify_artifact": {"artifact_checksum": "a" * 64},
            "evaluate": {
                "report_file_checksum": "b" * 64,
                "scientific_readiness": {
                    "engineering_pipeline": "PASS",
                    "synthetic_calibration": "SYNTHETIC_ONLY",
                    "real_world_predictive_validity": "NOT_ESTABLISHED",
                },
            },
            "compare": {"status": "NOT_COMPARABLE"},
            "report": {
                "report_file_checksum": "c" * 64,
                "proposal_status": "REVIEW_REQUIRED",
                "serving_permission": False,
            },
        }
        for name, output in outputs.items():
            receipt = {
                "run_id": final_id,
                "token": final_token,
                "fence": final_fence,
                "attempt": 1,
                "input_checksum": stable_hash([name, "input"]),
                "name": name,
            }
            await repo.record_step(**receipt, state="RUNNING")
            await repo.record_step(
                **receipt,
                state="SKIPPED_INELIGIBLE" if name == "compare" else "SUCCEEDED",
                output=output,
            )
        with pytest.raises(
            ControlPlaneConflict, match="persisted review proposal receipt is missing"
        ):
            await repo.complete_run(final_id, token=final_token, fence=final_fence)
        await repo.transition(
            final_id,
            token=final_token,
            fence=final_fence,
            expected=RunState.RUNNING,
            target=RunState.FAILED,
            reason="MISSING_PROPOSAL_RECEIPT",
        )
        assert (await repo.inspect_run(final_id))["run"]["state"] == "FAILED"
    finally:
        await database.close()
