from __future__ import annotations

import json
from typing import Any, cast
from uuid import UUID, uuid4

from sqlalchemy import text

from vehicle_platform.anomalies.domain import SourceRole as ServingSourceRole
from vehicle_platform.features.domain import stable_hash
from vehicle_platform.infrastructure.database import Database
from vehicle_platform.mlops.contracts import PipelineDefinition, ReviewProposal, RunState
from vehicle_platform.mlops.policy import require_controlled_environment
from vehicle_platform.predictions.domain import PredictionKind
from vehicle_platform.predictions.repository import slot_key


class ControlPlaneConflict(ValueError):
    """A requested operation conflicts with immutable intent or current ownership."""


def _scientific_limitations_valid(candidate_kind: str, value: object) -> bool:
    required = {
        "supervised": (
            "Synthetic calibration does not prove real-world predictive validity.",
            "Supervised scores are not mechanical failure probabilities.",
            "Unlabeled telemetry cannot establish accuracy, recall or calibration.",
            "Real-world mechanical failure predictive reliability remains NOT_ESTABLISHED.",
        ),
        "anomaly": (
            "Synthetic anomaly injections do not establish real-world detection performance.",
            "Anomaly scores are not engine-health percentages or confirmed diagnoses.",
            "Unlabeled real-world telemetry cannot establish accuracy, recall or calibration.",
            "Real-world mechanical failure predictive reliability remains NOT_ESTABLISHED.",
        ),
    }
    return (
        candidate_kind in required
        and isinstance(value, list)
        and all(isinstance(item, str) for item in value)
        and all(item in value for item in required[candidate_kind])
    )


def _candidate_dossier_valid(candidate_kind: str, body: object) -> bool:
    if not isinstance(body, dict):
        return False
    dossier = body.get("candidate_dossier")
    if (
        not isinstance(dossier, dict)
        or dossier.get("schema_version") != "phase10-candidate-dossier-v1"
        or dossier.get("candidate_kind") != candidate_kind
        or dossier.get("source_role") != "synthetic"
        or dossier.get("candidate_version_id") != body.get("candidate_version_id")
        or dossier.get("artifact_checksum") != body.get("artifact_checksum")
        or dossier.get("holdout_status") != body.get("comparison_status")
        or dossier.get("serving_action") != "NONE"
        or dossier.get("real_world_predictive_validity") != "NOT_ESTABLISHED"
        or dossier.get("real_world_mechanical_failure_predictive_reliability") != "NOT_ESTABLISHED"
        or dossier.get("review_status") != "REVIEW_REQUIRED"
        or dossier.get("serving_approval") != "PENDING_SEPARATE_AUTHORIZED_PHASE_9D_ACTION"
        or dossier.get("intended_environment") not in {"development", "test"}
        or body.get("candidate_dossier_checksum") != stable_hash(dossier)
    ):
        return False
    lineage = dossier.get("dataset_lineage")
    if not isinstance(lineage, dict):
        return False
    for key in (
        "source_fingerprint",
        "dataset_checksum",
        "evaluation_source_fingerprint",
        "evaluation_dataset_checksum",
        "feature_checksum",
        "label_checksum",
    ):
        value = lineage.get(key)
        if not isinstance(value, str) or len(value) != 64:
            return False
    if not isinstance(lineage.get("feature_set_version"), str):
        return False
    if not isinstance(lineage.get("training_rows"), int) or not isinstance(
        lineage.get("evaluation_rows"), int
    ):
        return False
    if not isinstance(dossier.get("holdout_performance_and_uncertainty"), dict):
        return False
    if not _scientific_limitations_valid(candidate_kind, dossier.get("scientific_limitations")):
        return False
    if dossier.get("scientific_limitations") != dossier.get("applicability_limits"):
        return False
    if candidate_kind == "anomaly" and not isinstance(
        dossier.get("cross_family_specificity"), dict
    ):
        return False
    return True


class ControlPlaneRepository:
    def __init__(self, database: Database) -> None:
        require_controlled_environment()
        self.database = database

    async def inspect_run(self, run_id: UUID) -> dict[str, Any]:
        """Return bounded, immutable lifecycle receipts without exposing lease secrets."""
        require_controlled_environment()
        async with self.database.session() as db, db.begin():
            await db.execute(text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY"))
            run = (
                (
                    await db.execute(
                        text(
                            "SELECT id,parent_run_id,definition_fingerprint,attempt,"
                            "source_role,state,"
                            "fencing_token,lease_expires_at,created_at,updated_at "
                            "FROM mlops_runs WHERE id=:id"
                        ),
                        {"id": run_id},
                    )
                )
                .mappings()
                .one_or_none()
            )
            if run is None:
                raise ControlPlaneConflict("run does not exist")
            events = (
                (
                    await db.execute(
                        text(
                            "SELECT from_state,to_state,reason,fencing_token,created_at "
                            "FROM mlops_run_events WHERE run_id=:id "
                            "ORDER BY event_number LIMIT 1001"
                        ),
                        {"id": run_id},
                    )
                )
                .mappings()
                .all()
            )
            steps = (
                (
                    await db.execute(
                        text(
                            "SELECT step_name,step_attempt,state,input_checksum,output_checksum,"
                            "output_body,fencing_token,checkpoint_source_run_id,created_at "
                            "FROM mlops_step_events "
                            "WHERE run_id=:id ORDER BY event_number LIMIT 1001"
                        ),
                        {"id": run_id},
                    )
                )
                .mappings()
                .all()
            )
            if len(events) > 1000 or len(steps) > 1000:
                raise ControlPlaneConflict("run history exceeds the inspection bound")
            return {
                "schema_version": "phase10-inspection-v1",
                "run": dict(run),
                "events": [dict(event) for event in events],
                "steps": [dict(step) for step in steps],
                "real_world_predictive_validity": "NOT_ESTABLISHED",
                "serving_action": "NONE",
            }

    async def create_run(self, definition: PipelineDefinition) -> tuple[UUID, bool]:
        """Register one immutable definition and idempotently create its first attempt."""
        require_controlled_environment()
        digest = definition.fingerprint
        payload = json.dumps(
            definition.model_dump(mode="json"),
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
        async with self.database.session() as db, db.begin():
            # Serialize competing creations for the same logical intent, even before a row exists.
            await db.execute(
                text("SELECT pg_advisory_xact_lock(hashtextextended(:key, 0))"),
                {"key": digest},
            )
            await db.execute(
                text(
                    "INSERT INTO "
                    "mlops_definitions(fingerprint,definition_version,schema_version,body) "
                    "VALUES (:id,:version,:schema,CAST(:body AS jsonb)) ON CONFLICT DO NOTHING"
                ),
                {
                    "id": digest,
                    "version": definition.definition_version,
                    "schema": definition.schema_version,
                    "body": payload,
                },
            )
            stored = (
                (
                    await db.execute(
                        text(
                            "SELECT fingerprint,body FROM mlops_definitions WHERE "
                            "definition_version=:version"
                        ),
                        {"version": definition.definition_version},
                    )
                )
                .mappings()
                .one_or_none()
            )
            if (
                stored is None
                or stored["fingerprint"] != digest
                or stored["body"] != json.loads(payload)
            ):
                raise ControlPlaneConflict("definition version conflicts with immutable content")
            existing = (
                await db.execute(
                    text(
                        "SELECT id FROM mlops_runs WHERE logical_fingerprint=:fingerprint AND "
                        "attempt=1"
                    ),
                    {"fingerprint": digest},
                )
            ).scalar_one_or_none()
            if existing is not None:
                return UUID(str(existing)), False
            run_id = uuid4()
            await db.execute(
                text(
                    "INSERT INTO "
                    "mlops_runs(id,definition_fingerprint,logical_fingerprint,"
                    "attempt,source_role,state) VALUES "
                    "(:id,:fingerprint,:fingerprint,1,:source,'PLANNED')"
                ),
                {
                    "id": run_id,
                    "fingerprint": digest,
                    "source": definition.source_role.value,
                },
            )
            await db.execute(
                text(
                    "INSERT INTO "
                    "mlops_run_events(id,run_id,from_state,to_state,reason,fencing_token) VALUES "
                    "(:id,:run,NULL,'PLANNED','CREATED',0)"
                ),
                {"id": uuid4(), "run": run_id},
            )
            return run_id, True

    async def find_exact_run(self, definition: PipelineDefinition) -> dict[str, Any] | None:
        """Read an exact prior execution before planning an idempotent replay."""
        require_controlled_environment()
        digest = definition.fingerprint
        payload = json.dumps(
            definition.model_dump(mode="json"),
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
        async with self.database.session() as db, db.begin():
            await db.execute(text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY"))
            stored = (
                (
                    await db.execute(
                        text(
                            "SELECT fingerprint,body FROM mlops_definitions "
                            "WHERE definition_version=:version"
                        ),
                        {"version": definition.definition_version},
                    )
                )
                .mappings()
                .one_or_none()
            )
            if stored is not None and (
                stored["fingerprint"] != digest or stored["body"] != json.loads(payload)
            ):
                raise ControlPlaneConflict("definition version conflicts with immutable content")
            run = (
                (
                    await db.execute(
                        text(
                            "SELECT r.id,r.definition_fingerprint,r.logical_fingerprint,"
                            "r.source_role,r.state,EXISTS(SELECT 1 FROM mlops_step_events s "
                            "WHERE s.run_id=r.id) AS has_steps FROM mlops_runs r "
                            "WHERE r.logical_fingerprint=:fingerprint AND r.attempt=1"
                        ),
                        {"fingerprint": digest},
                    )
                )
                .mappings()
                .one_or_none()
            )
        if run is None:
            return None
        if (
            stored is None
            or run["definition_fingerprint"] != digest
            or run["logical_fingerprint"] != digest
            or run["source_role"] != definition.source_role.value
        ):
            raise ControlPlaneConflict("existing run has mismatched immutable identity")
        return {
            "run_id": UUID(str(run["id"])),
            "state": str(run["state"]),
            "has_steps": bool(run["has_steps"]),
        }

    async def create_checkpoint_retry(self, failed_run_id: UUID) -> tuple[UUID, bool]:
        """Create one linked attempt from verified read-only checkpoints before model fitting."""
        require_controlled_environment()
        async with self.database.session() as db, db.begin():
            prior = (
                (
                    await db.execute(
                        text(
                            "SELECT id,definition_fingerprint,logical_fingerprint,attempt,"
                            "source_role,state FROM mlops_runs WHERE id=:id FOR UPDATE"
                        ),
                        {"id": failed_run_id},
                    )
                )
                .mappings()
                .one_or_none()
            )
            if prior is None:
                raise ControlPlaneConflict("retry source run does not exist")
            existing_child = await db.scalar(
                text("SELECT id FROM mlops_runs WHERE parent_run_id=:id ORDER BY attempt LIMIT 1"),
                {"id": failed_run_id},
            )
            if existing_child is not None:
                return UUID(str(existing_child)), False
            if prior["state"] != RunState.FAILED.value:
                raise ControlPlaneConflict("only a fenced failed run may create a retry")
            reason = await db.scalar(
                text(
                    "SELECT reason FROM mlops_run_events WHERE run_id=:id "
                    "ORDER BY event_number DESC LIMIT 1"
                ),
                {"id": failed_run_id},
            )
            if reason != "LEASE_EXPIRED_UNRECONCILED":
                raise ControlPlaneConflict("run failure is not an expired-lease recovery")
            latest_rows = (
                (
                    await db.execute(
                        text(
                            "SELECT DISTINCT ON (step_name) step_name,step_attempt,state,"
                            "input_checksum,output_checksum,output_body FROM mlops_step_events "
                            "WHERE run_id=:id ORDER BY step_name,event_number DESC"
                        ),
                        {"id": failed_run_id},
                    )
                )
                .mappings()
                .all()
            )
            latest: dict[str, Any] = {str(item["step_name"]): item for item in latest_rows}
            if set(latest) - {"select", "validate"}:
                raise ControlPlaneConflict("retry cannot cross a model-fit side-effect boundary")
            if (
                latest.get("validate", {}).get("state") == "SUCCEEDED"
                and latest.get("select", {}).get("state") != "SUCCEEDED"
            ):
                raise ControlPlaneConflict("retry checkpoint prerequisite is incomplete")
            checkpoints: list[dict[str, Any]] = []
            for name in ("select", "validate"):
                item = latest.get(name)
                if item is None:
                    continue
                if item["state"] == "RUNNING":
                    continue
                body = item["output_body"]
                if (
                    item["state"] != "SUCCEEDED"
                    or not isinstance(body, dict)
                    or item["output_checksum"] != stable_hash(body)
                ):
                    raise ControlPlaneConflict("retry checkpoint is incomplete or tampered")
                checkpoints.append(
                    {
                        "step_name": name,
                        "step_attempt": int(item["step_attempt"]),
                        "input_checksum": str(item["input_checksum"]),
                        "output_checksum": str(item["output_checksum"]),
                        "output_body": body,
                    }
                )
            if int(prior["attempt"]) >= 3:
                raise ControlPlaneConflict("bounded Phase 10 retry limit was reached")
            attempt = int(prior["attempt"]) + 1
            retry_id = uuid4()
            await db.execute(
                text(
                    "INSERT INTO mlops_runs(id,parent_run_id,definition_fingerprint,"
                    "logical_fingerprint,attempt,source_role,state) VALUES "
                    "(:id,:parent,:definition,:logical,:attempt,:source,'PLANNED')"
                ),
                {
                    "id": retry_id,
                    "parent": failed_run_id,
                    "definition": prior["definition_fingerprint"],
                    "logical": prior["logical_fingerprint"],
                    "attempt": attempt,
                    "source": prior["source_role"],
                },
            )
            await db.execute(
                text(
                    "INSERT INTO mlops_run_events(id,run_id,from_state,to_state,reason,"
                    "fencing_token) VALUES (:id,:run,NULL,'PLANNED','RETRY_CREATED',0)"
                ),
                {"id": uuid4(), "run": retry_id},
            )
            for checkpoint in checkpoints:
                await db.execute(
                    text(
                        "INSERT INTO mlops_step_events(id,run_id,checkpoint_source_run_id,"
                        "step_name,step_attempt,state,input_checksum,output_checksum,output_body,"
                        "fencing_token) VALUES (:id,:run,:source,:name,:attempt,'SUCCEEDED',"
                        ":input,:output,CAST(:body AS jsonb),0)"
                    ),
                    {
                        "id": uuid4(),
                        "run": retry_id,
                        "source": failed_run_id,
                        "name": checkpoint["step_name"],
                        "attempt": checkpoint["step_attempt"],
                        "input": checkpoint["input_checksum"],
                        "output": checkpoint["output_checksum"],
                        "body": json.dumps(
                            checkpoint["output_body"],
                            sort_keys=True,
                            separators=(",", ":"),
                            allow_nan=False,
                        ),
                    },
                )
            return retry_id, True

    async def claim(self, run_id: UUID, *, lease_seconds: int = 120) -> tuple[UUID, int]:
        require_controlled_environment()
        if not 10 <= lease_seconds <= 600:
            raise ValueError("lease duration must be between 10 and 600 seconds")
        token = uuid4()
        async with self.database.session() as db, db.begin():
            row = (
                await db.execute(
                    text(
                        "UPDATE mlops_runs SET state='CLAIMED', lease_token=:token, "
                        "lease_expires_at=now()+(:duration * interval '1 second'), "
                        "fencing_token=fencing_token+1, updated_at=now() WHERE id=:id AND "
                        "state='PLANNED' AND lease_token IS NULL RETURNING fencing_token"
                    ),
                    {"id": run_id, "token": token, "duration": lease_seconds},
                )
            ).one_or_none()
            if row is None:
                raise ControlPlaneConflict("run is not available for a new claim")
            fence = int(row[0])
            await db.execute(
                text(
                    "INSERT INTO "
                    "mlops_run_events(id,run_id,from_state,to_state,reason,fencing_token) VALUES "
                    "(:event,:run,'PLANNED','CLAIMED','CLAIMED',:fence)"
                ),
                {"event": uuid4(), "run": run_id, "fence": fence},
            )
            return token, fence

    async def transition(
        self,
        run_id: UUID,
        *,
        token: UUID,
        fence: int,
        expected: RunState,
        target: RunState,
        reason: str,
    ) -> None:
        require_controlled_environment()
        allowed = {
            RunState.CLAIMED: {RunState.RUNNING, RunState.CANCELLED, RunState.FAILED},
            RunState.RUNNING: {
                RunState.COMPLETED,
                RunState.INSUFFICIENT_SUPPORT,
                RunState.FAILED,
                RunState.CANCELLED,
                RunState.TIMED_OUT,
                RunState.BLOCKED_BY_POLICY,
            },
        }
        if target not in allowed.get(expected, set()):
            raise ValueError("invalid run state transition")
        if target is RunState.COMPLETED:
            raise ControlPlaneConflict("completion requires verified stage and artifact receipts")
        if (
            not reason.isascii()
            or not reason.replace("_", "").isalnum()
            or reason.upper() != reason
            or len(reason) > 80
        ):
            raise ValueError("reason must be a bounded uppercase code")
        terminal = target is not RunState.RUNNING
        async with self.database.session() as db, db.begin():
            result = await db.execute(
                text(
                    "UPDATE mlops_runs SET state=:target, lease_token=CASE WHEN :terminal THEN "
                    "NULL ELSE lease_token END, lease_expires_at=CASE WHEN :terminal THEN NULL "
                    "ELSE lease_expires_at END, updated_at=now() WHERE id=:id AND "
                    "state=:expected AND lease_token=:token AND fencing_token=:fence AND "
                    "lease_expires_at>now() RETURNING id"
                ),
                {
                    "id": run_id,
                    "token": token,
                    "fence": fence,
                    "expected": expected.value,
                    "target": target.value,
                    "terminal": terminal,
                },
            )
            if result.scalar_one_or_none() is None:
                raise ControlPlaneConflict("lease or run state changed")
            await db.execute(
                text(
                    "INSERT INTO "
                    "mlops_run_events(id,run_id,from_state,to_state,reason,fencing_token) VALUES "
                    "(:id,:run,:previous,:target,:reason,:fence)"
                ),
                {
                    "id": uuid4(),
                    "run": run_id,
                    "previous": expected.value,
                    "target": target.value,
                    "reason": reason,
                    "fence": fence,
                },
            )

    async def complete_run(
        self,
        run_id: UUID,
        *,
        token: UUID,
        fence: int,
        reason: str = "RECEIPTS_VERIFIED",
    ) -> None:
        """Atomically complete only a fully receipted, currently fenced run."""
        require_controlled_environment()
        if (
            reason != reason.upper()
            or not reason.isascii()
            or not reason.replace("_", "").isalnum()
        ):
            raise ValueError("reason must be a bounded uppercase code")
        async with self.database.session() as db, db.begin():
            owner = await db.scalar(
                text(
                    "SELECT id FROM mlops_runs WHERE id=:id AND state='RUNNING' "
                    "AND lease_token=:token AND fencing_token=:fence AND lease_expires_at>now() "
                    "FOR UPDATE"
                ),
                {"id": run_id, "token": token, "fence": fence},
            )
            if owner is None:
                raise ControlPlaneConflict("lease or run state changed")
            rows = (
                (
                    await db.execute(
                        text(
                            "SELECT DISTINCT ON (step_name) step_name,state,input_checksum,"
                            "output_checksum,output_body FROM mlops_step_events WHERE run_id=:id "
                            "ORDER BY step_name,event_number DESC"
                        ),
                        {"id": run_id},
                    )
                )
                .mappings()
                .all()
            )
            latest = {str(row["step_name"]): row for row in rows}
            stages = (
                "select",
                "validate",
                "fit",
                "verify_artifact",
                "evaluate",
                "compare",
                "report",
            )
            if set(latest) != set(stages):
                raise ControlPlaneConflict("required pipeline receipts are incomplete")
            for stage in stages:
                row = latest[stage]
                state = row["state"]
                output = row["output_body"]
                if not isinstance(output, dict):
                    raise ControlPlaneConflict("pipeline receipt body is invalid")
                if state == "SKIPPED_INELIGIBLE":
                    if stage != "compare" or output.get("status") != "NOT_COMPARABLE":
                        raise ControlPlaneConflict(
                            "only an incomparable offline comparison may skip"
                        )
                elif state != "SUCCEEDED":
                    raise ControlPlaneConflict("required pipeline stage did not succeed")
                if row["output_checksum"] != stable_hash(output):
                    raise ControlPlaneConflict("pipeline stage output checksum is invalid")
            verified = latest["verify_artifact"]["output_body"]
            evaluated = latest["evaluate"]["output_body"]
            reported = latest["report"]["output_body"]
            fit_output = latest["fit"]["output_body"]
            selected = latest["select"]["output_body"]
            validated = latest["validate"]["output_body"]
            comparison = latest["compare"]["output_body"]
            proposal = reported
            if selected.get("source_role") != "synthetic":
                raise ControlPlaneConflict("execution source role is not eligible")
            if validated.get("plan_status") != "READY_TO_REVIEW":
                raise ControlPlaneConflict("pipeline plan was not eligible for execution")
            artifact_hash = verified.get("artifact_checksum")
            if (
                not isinstance(artifact_hash, str)
                or len(artifact_hash) != 64
                or any(char not in "0123456789abcdef" for char in artifact_hash)
                or fit_output.get("artifact_checksum") != artifact_hash
            ):
                raise ControlPlaneConflict("registered artifact receipt is missing")
            if not isinstance(evaluated.get("report_file_checksum"), str) or not isinstance(
                reported.get("report_file_checksum"), str
            ):
                raise ControlPlaneConflict("evaluation or review report receipt is missing")
            readiness = evaluated.get("scientific_readiness")
            if isinstance(readiness, dict):
                eligible_evaluation = (
                    readiness.get("engineering_pipeline") == "PASS"
                    and readiness.get("synthetic_calibration") == "SYNTHETIC_ONLY"
                    and readiness.get("real_world_predictive_validity") == "NOT_ESTABLISHED"
                )
            else:
                eligible_evaluation = (
                    readiness == "SYNTHETIC_ONLY"
                    and evaluated.get("evaluation_status") == "SYNTHETIC_EVALUATED"
                )
            if not eligible_evaluation:
                raise ControlPlaneConflict("scientific evaluation gate is not eligible")
            if evaluated.get("serving_action", "NONE") != "NONE":
                raise ControlPlaneConflict("evaluation receipt contains a serving action")
            comparison_state = latest["compare"]["state"]
            if comparison_state == "SKIPPED_INELIGIBLE":
                if comparison.get("serving_action", "NONE") != "NONE":
                    raise ControlPlaneConflict("comparison receipt contains a serving action")
            elif comparison.get("status") != "COMPARABLE_OFFLINE":
                raise ControlPlaneConflict("successful comparison lacks offline evidence")
            if (
                proposal.get("proposal_status") != "REVIEW_REQUIRED"
                or proposal.get("serving_permission") is not False
            ):
                raise ControlPlaneConflict("review report grants or omits proposal separation")
            proposal_id = proposal.get("proposal_id")
            proposal_checksum = proposal.get("proposal_checksum")
            if not isinstance(proposal_id, str) or not isinstance(proposal_checksum, str):
                raise ControlPlaneConflict("persisted review proposal receipt is missing")
            persisted_proposal = (
                (
                    await db.execute(
                        text(
                            "SELECT p.id,p.run_id,p.definition_fingerprint,p.candidate_kind,"
                            "p.model_version_id,"
                            "p.detector_version_id,"
                            "COALESCE(p.model_version_id,p.detector_version_id) "
                            "AS candidate_version_id,p.artifact_checksum,p.evaluation_checksum,"
                            "p.comparison_checksum,p.content_checksum,p.body,d.body->>'kind' "
                            "AS pipeline_kind FROM mlops_proposals p JOIN mlops_definitions d "
                            "ON d.fingerprint=p.definition_fingerprint WHERE p.id=:id"
                        ),
                        {"id": UUID(proposal_id)},
                    )
                )
                .mappings()
                .one_or_none()
            )
            evaluation_checksum = evaluated.get(
                "evaluation_report_checksum", evaluated.get("report_content_checksum")
            )
            expected_comparison_checksum = stable_hash(comparison)
            if (
                persisted_proposal is None
                or persisted_proposal["run_id"] != run_id
                or persisted_proposal["content_checksum"] != proposal_checksum
                or stable_hash(persisted_proposal["body"]) != proposal_checksum
                or persisted_proposal["candidate_kind"] != persisted_proposal["pipeline_kind"]
                or persisted_proposal["artifact_checksum"] != artifact_hash
                or persisted_proposal["evaluation_checksum"] != evaluation_checksum
                or persisted_proposal["comparison_checksum"] != expected_comparison_checksum
                or persisted_proposal["body"].get("run_id") != str(run_id)
                or persisted_proposal["body"].get("definition_fingerprint")
                != persisted_proposal["definition_fingerprint"]
                or persisted_proposal["body"].get("candidate_version_id")
                != str(persisted_proposal["candidate_version_id"])
                or persisted_proposal["body"].get("artifact_checksum") != artifact_hash
                or persisted_proposal["body"].get("evaluation_checksum") != evaluation_checksum
                or persisted_proposal["body"].get("comparison_checksum")
                != expected_comparison_checksum
                or persisted_proposal["body"].get("source_role") != "synthetic"
                or persisted_proposal["body"].get("status") != "REVIEW_REQUIRED"
                or persisted_proposal["body"].get("serving_permission") is not False
                or persisted_proposal["body"].get("serving_action") != "NONE"
                or persisted_proposal["body"].get("real_world_predictive_validity")
                != "NOT_ESTABLISHED"
                or not _candidate_dossier_valid(
                    str(persisted_proposal["candidate_kind"]), persisted_proposal["body"]
                )
            ):
                raise ControlPlaneConflict("persisted review proposal lineage is invalid")
            limitations = persisted_proposal["body"].get("scientific_limitations")
            if not _scientific_limitations_valid(
                str(persisted_proposal["candidate_kind"]), limitations
            ):
                raise ControlPlaneConflict("review proposal scientific limitations are missing")
            await db.execute(
                text(
                    "UPDATE mlops_runs SET state='COMPLETED',lease_token=NULL,"
                    "lease_expires_at=NULL,updated_at=now() WHERE id=:id"
                ),
                {"id": run_id},
            )
            await db.execute(
                text(
                    "INSERT INTO mlops_run_events(id,run_id,from_state,to_state,reason,"
                    "fencing_token) VALUES (:event,:run,'RUNNING','COMPLETED',:reason,:fence)"
                ),
                {"event": uuid4(), "run": run_id, "reason": reason, "fence": fence},
            )

    async def heartbeat(
        self, run_id: UUID, *, token: UUID, fence: int, lease_seconds: int = 120
    ) -> None:
        require_controlled_environment()
        if not 10 <= lease_seconds <= 600:
            raise ValueError("lease duration must be between 10 and 600 seconds")
        async with self.database.session() as db, db.begin():
            updated = await db.scalar(
                text(
                    "UPDATE mlops_runs SET "
                    "lease_expires_at=now()+(:seconds * interval '1 second'), "
                    "updated_at=now() WHERE id=:id AND lease_token=:token "
                    "AND fencing_token=:fence AND state IN ('CLAIMED','RUNNING') "
                    "AND lease_expires_at>now() RETURNING id"
                ),
                {"id": run_id, "token": token, "fence": fence, "seconds": lease_seconds},
            )
            if updated is None:
                raise ControlPlaneConflict("lease expired or ownership changed")

    async def fail_expired_run(self, run_id: UUID) -> None:
        """Fence a lost worker and fail closed rather than repeat uncertain side effects.

        Registration may have committed just before a worker died. Until its artifacts
        can be reconciled, a fresh fit would risk registering a duplicate candidate.
        """
        require_controlled_environment()
        async with self.database.session() as db, db.begin():
            row = (
                await db.execute(
                    text(
                        "SELECT state,fencing_token FROM mlops_runs WHERE id=:id "
                        "AND state IN ('CLAIMED','RUNNING') AND lease_expires_at<=now() "
                        "FOR UPDATE"
                    ),
                    {"id": run_id},
                )
            ).one_or_none()
            if row is None:
                raise ControlPlaneConflict("run is not eligible for expired-lease recovery")
            previous, previous_fence = row
            fence = int(previous_fence) + 1
            await db.execute(
                text(
                    "UPDATE mlops_runs SET state='FAILED',lease_token=NULL,"
                    "lease_expires_at=NULL,fencing_token=:fence,updated_at=now() WHERE id=:id"
                ),
                {"id": run_id, "fence": fence},
            )
            await db.execute(
                text(
                    "INSERT INTO mlops_run_events(id,run_id,from_state,to_state,reason,"
                    "fencing_token) VALUES (:event,:run,:previous,'FAILED',"
                    "'LEASE_EXPIRED_UNRECONCILED',:fence)"
                ),
                {"event": uuid4(), "run": run_id, "previous": previous, "fence": fence},
            )

    async def record_step(
        self,
        run_id: UUID,
        *,
        token: UUID,
        fence: int,
        name: str,
        attempt: int,
        state: str,
        input_checksum: str,
        output: dict[str, object] | None = None,
    ) -> None:
        """Append a fenced stage event; successful outputs are bound to a canonical hash."""
        from vehicle_platform.features.domain import stable_hash

        require_controlled_environment()
        stages = ("select", "validate", "fit", "verify_artifact", "evaluate", "compare", "report")
        if name not in stages or state not in {
            "RUNNING",
            "SUCCEEDED",
            "SKIPPED_INELIGIBLE",
            "FAILED",
            "CANCELLED",
        }:
            raise ValueError("unknown step or state")
        if (
            not 1 <= attempt <= 100
            or len(input_checksum) != 64
            or any(char not in "0123456789abcdef" for char in input_checksum)
        ):
            raise ValueError("invalid step attempt or input checksum")
        if state == "SUCCEEDED" and output is None:
            raise ValueError("successful steps require a hash-bound output")
        if state == "SKIPPED_INELIGIBLE" and (
            name != "compare" or output is None or output.get("status") != "NOT_COMPARABLE"
        ):
            raise ValueError("only an explicitly incomparable comparison may be skipped")
        body = output if output is not None else {}
        payload = json.dumps(body, sort_keys=True, separators=(",", ":"), allow_nan=False)
        if len(payload.encode("utf-8")) > 60000:
            raise ValueError("step output exceeds the database bound")
        output_checksum = stable_hash(body) if output is not None else None
        async with self.database.session() as db, db.begin():
            owner = await db.scalar(
                text(
                    "SELECT id FROM mlops_runs WHERE id=:id AND state='RUNNING' "
                    "AND lease_token=:token AND fencing_token=:fence AND lease_expires_at>now() "
                    "FOR UPDATE"
                ),
                {"id": run_id, "token": token, "fence": fence},
            )
            if owner is None:
                raise ControlPlaneConflict("lease or run state changed")
            latest = (
                (
                    await db.execute(
                        text(
                            "SELECT step_name,step_attempt,state,input_checksum FROM "
                            "(SELECT DISTINCT ON (step_name) step_name,step_attempt,state,"
                            "input_checksum "
                            "FROM mlops_step_events WHERE run_id=:run "
                            "ORDER BY step_name,event_number DESC) latest"
                        ),
                        {"run": run_id},
                    )
                )
                .mappings()
                .all()
            )
            previous = {str(row["step_name"]): row for row in latest}
            if state == "RUNNING":
                if name in previous:
                    raise ControlPlaneConflict("step already has an attempt")
                for predecessor in stages[: stages.index(name)]:
                    row = previous.get(predecessor)
                    if row is None or row["state"] not in {"SUCCEEDED", "SKIPPED_INELIGIBLE"}:
                        raise ControlPlaneConflict("step prerequisite is incomplete")
            else:
                row = previous.get(name)
                if (
                    row is None
                    or row["state"] != "RUNNING"
                    or row["step_attempt"] != attempt
                    or row["input_checksum"] != input_checksum
                ):
                    raise ControlPlaneConflict("step does not match its running attempt")
            await db.execute(
                text(
                    "INSERT INTO mlops_step_events(id,run_id,step_name,step_attempt,state,"
                    "input_checksum,output_checksum,output_body,fencing_token) VALUES "
                    "(:id,:run,:name,:attempt,:state,:input,:output,CAST(:body AS jsonb),:fence)"
                ),
                {
                    "id": uuid4(),
                    "run": run_id,
                    "name": name,
                    "attempt": attempt,
                    "state": state,
                    "input": input_checksum,
                    "output": output_checksum,
                    "body": payload,
                    "fence": fence,
                },
            )

    async def create_proposal(
        self,
        run_id: UUID,
        *,
        token: UUID,
        fence: int,
        definition_fingerprint: str,
        candidate_kind: str,
        candidate_version_id: UUID,
        artifact_checksum: str,
        evaluation_checksum: str,
        comparison_checksum: str | None,
        body: dict[str, object],
    ) -> tuple[UUID, str, bool]:
        """Persist one immutable review artifact while the execution lease is live."""
        environment = require_controlled_environment()
        if candidate_kind not in {"supervised", "anomaly"}:
            raise ValueError("candidate kind is not allowlisted")
        hashes = (definition_fingerprint, artifact_checksum, evaluation_checksum)
        if any(
            len(item) != 64 or any(char not in "0123456789abcdef" for char in item)
            for item in hashes
        ) or (
            comparison_checksum is not None
            and (
                len(comparison_checksum) != 64
                or any(char not in "0123456789abcdef" for char in comparison_checksum)
            )
        ):
            raise ValueError("proposal lineage checksum is invalid")
        readiness = body.get("scientific_readiness")
        readiness_status = (
            readiness.get("synthetic_calibration")
            if candidate_kind == "supervised" and isinstance(readiness, dict)
            else readiness
        )
        if (
            body.get("schema_version") != "phase10-proposal-v1"
            or body.get("run_id") != str(run_id)
            or body.get("definition_fingerprint") != definition_fingerprint
            or body.get("candidate_kind") != candidate_kind
            or body.get("candidate_version_id") != str(candidate_version_id)
            or body.get("artifact_checksum") != artifact_checksum
            or body.get("evaluation_checksum") != evaluation_checksum
            or body.get("comparison_checksum") != comparison_checksum
            or body.get("source_role") != "synthetic"
            or body.get("status") != "REVIEW_REQUIRED"
            or body.get("serving_permission") is not False
            or body.get("serving_action") != "NONE"
            or body.get("real_world_predictive_validity") != "NOT_ESTABLISHED"
            or readiness_status != "SYNTHETIC_ONLY"
            or not _scientific_limitations_valid(candidate_kind, body.get("scientific_limitations"))
            or not _candidate_dossier_valid(candidate_kind, body)
        ):
            raise ValueError("proposal is missing required scientific or serving limitations")
        payload = json.dumps(body, sort_keys=True, separators=(",", ":"), allow_nan=False)
        ReviewProposal.model_validate_json(payload)
        if len(payload.encode("utf-8")) > 60000:
            raise ValueError("proposal body exceeds the database bound")
        content_checksum = stable_hash(body)
        async with self.database.session() as db, db.begin():
            owner = (
                (
                    await db.execute(
                        text(
                            "SELECT definition_fingerprint,source_role FROM mlops_runs "
                            "WHERE id=:id "
                            "AND state='RUNNING' AND lease_token=:token AND fencing_token=:fence "
                            "AND lease_expires_at>now() FOR UPDATE"
                        ),
                        {"id": run_id, "token": token, "fence": fence},
                    )
                )
                .mappings()
                .one_or_none()
            )
            if (
                owner is None
                or owner["definition_fingerprint"] != definition_fingerprint
                or owner["source_role"] != "synthetic"
            ):
                raise ControlPlaneConflict("proposal is outside the current synthetic run")
            existing = (
                (
                    await db.execute(
                        text("SELECT id,content_checksum FROM mlops_proposals WHERE run_id=:run"),
                        {"run": run_id},
                    )
                )
                .mappings()
                .one_or_none()
            )
            if existing is not None:
                if existing["content_checksum"] != content_checksum:
                    raise ControlPlaneConflict("run already has a different immutable proposal")
                return UUID(str(existing["id"])), content_checksum, False
            proposal_id = uuid4()
            await db.execute(
                text(
                    "INSERT INTO mlops_proposals(id,run_id,definition_fingerprint,"
                    "candidate_kind,model_version_id,detector_version_id,source_role,"
                    "artifact_checksum,evaluation_checksum,comparison_checksum,"
                    "content_checksum,body) "
                    "VALUES (:id,:run,:definition,:kind,:model,:detector,'synthetic',"
                    ":artifact,:evaluation,:comparison,:checksum,CAST(:body AS jsonb))"
                ),
                {
                    "id": proposal_id,
                    "run": run_id,
                    "definition": definition_fingerprint,
                    "kind": candidate_kind,
                    "model": candidate_version_id if candidate_kind == "supervised" else None,
                    "detector": candidate_version_id if candidate_kind == "anomaly" else None,
                    "artifact": artifact_checksum,
                    "evaluation": evaluation_checksum,
                    "comparison": comparison_checksum,
                    "checksum": content_checksum,
                    "body": payload,
                },
            )
            for state, reason in (
                ("DRAFT", "PROPOSAL_DRAFTED"),
                ("EVALUATING", "EVALUATION_RECEIPTS_ATTACHED"),
                ("EVALUATED", "SCIENTIFIC_GATES_RECORDED"),
                ("REVIEW_REQUIRED", "CREATED_PROPOSAL"),
            ):
                await db.execute(
                    text(
                        "INSERT INTO mlops_proposal_events(id,proposal_id,state,proposal_checksum,"
                        "environment,reviewer_id,reviewer_role,reason) VALUES "
                        "(:id,:proposal,:state,:checksum,:environment,NULL,NULL,:reason)"
                    ),
                    {
                        "id": uuid4(),
                        "proposal": proposal_id,
                        "state": state,
                        "checksum": content_checksum,
                        "environment": environment,
                        "reason": reason,
                    },
                )
            return proposal_id, content_checksum, True

    async def inspect_proposal(self, proposal_id: UUID) -> dict[str, Any]:
        """Read a bounded immutable proposal and its append-only human decisions."""
        require_controlled_environment()
        async with self.database.session() as db, db.begin():
            await db.execute(text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY"))
            proposal = (
                (
                    await db.execute(
                        text(
                            "SELECT p.id,p.run_id,p.definition_fingerprint,p.candidate_kind,"
                            "p.model_version_id,p.detector_version_id,p.source_role,"
                            "p.artifact_checksum,p.evaluation_checksum,p.comparison_checksum,"
                            "p.content_checksum,p.body,p.created_at,r.state AS run_state "
                            "FROM mlops_proposals p JOIN mlops_runs r ON r.id=p.run_id "
                            "WHERE p.id=:id"
                        ),
                        {"id": proposal_id},
                    )
                )
                .mappings()
                .one_or_none()
            )
            if proposal is None:
                raise ControlPlaneConflict("proposal does not exist")
            events = (
                (
                    await db.execute(
                        text(
                            "SELECT state,proposal_checksum,environment,reviewer_id,"
                            "reviewer_role,reason,"
                            "created_at "
                            "FROM mlops_proposal_events WHERE proposal_id=:id "
                            "ORDER BY event_number LIMIT 101"
                        ),
                        {"id": proposal_id},
                    )
                )
                .mappings()
                .all()
            )
            if len(events) > 100:
                raise ControlPlaneConflict("proposal history exceeds the inspection bound")
            latest = dict(events[-1]) if events else None
            if stable_hash(proposal["body"]) != proposal["content_checksum"]:
                raise ControlPlaneConflict("proposal content checksum is invalid")
            if (
                not isinstance(proposal["body"], dict)
                or proposal["body"].get("serving_permission") is not False
                or proposal["body"].get("serving_action") != "NONE"
                or proposal["body"].get("real_world_predictive_validity") != "NOT_ESTABLISHED"
                or not _scientific_limitations_valid(
                    str(proposal["candidate_kind"]),
                    proposal["body"].get("scientific_limitations"),
                )
                or not _candidate_dossier_valid(str(proposal["candidate_kind"]), proposal["body"])
                or any(
                    event["proposal_checksum"] != proposal["content_checksum"] for event in events
                )
            ):
                raise ControlPlaneConflict("proposal scientific or serving boundary is invalid")
            return {
                "schema_version": "phase10-proposal-inspection-v1",
                "proposal": dict(proposal),
                "state": latest["state"] if latest else "INVALID",
                "events": [dict(event) for event in events],
                "serving_action": "NONE",
                "real_world_predictive_validity": "NOT_ESTABLISHED",
            }

    async def review_proposal(
        self,
        proposal_id: UUID,
        *,
        proposal_checksum: str,
        decision: str,
        reviewer_id: str,
        reviewer_role: str,
        reason: str,
    ) -> str:
        """Append a human decision; it cannot approve or change a Phase 9D binding."""
        environment = require_controlled_environment()
        if decision not in {"accept", "reject"}:
            raise ValueError("proposal decision must be accept or reject")
        if (
            reviewer_role != "mlops_reviewer"
            or not 2 <= len(reviewer_id.strip()) <= 120
            or not 20 <= len(reason.strip()) <= 500
            or len(proposal_checksum) != 64
            or any(char not in "0123456789abcdef" for char in proposal_checksum)
        ):
            raise ValueError("reviewer identity, proposal checksum and reason are required")
        target_state = "APPROVED_FOR_CONTROLLED_REVIEW" if decision == "accept" else "REJECTED"
        async with self.database.session() as db, db.begin():
            proposal = (
                (
                    await db.execute(
                        text(
                            "SELECT p.content_checksum,p.body,p.candidate_kind,"
                            "r.state AS run_state FROM mlops_proposals p "
                            "JOIN mlops_runs r ON r.id=p.run_id WHERE p.id=:id FOR UPDATE OF p"
                        ),
                        {"id": proposal_id},
                    )
                )
                .mappings()
                .one_or_none()
            )
            if proposal is None:
                raise ControlPlaneConflict("proposal does not exist")
            if (
                proposal["content_checksum"] != proposal_checksum
                or proposal["run_state"] != "COMPLETED"
            ):
                raise ControlPlaneConflict("proposal is stale or its pipeline is incomplete")
            if (
                stable_hash(proposal["body"]) != proposal_checksum
                or proposal["body"].get("serving_permission") is not False
                or proposal["body"].get("serving_action") != "NONE"
                or proposal["body"].get("real_world_predictive_validity") != "NOT_ESTABLISHED"
                or not _scientific_limitations_valid(
                    str(proposal["candidate_kind"]),
                    proposal["body"].get("scientific_limitations"),
                )
            ):
                raise ControlPlaneConflict("proposal scientific or serving boundary is invalid")
            latest = (
                (
                    await db.execute(
                        text(
                            "SELECT state,proposal_checksum,environment,reviewer_id,"
                            "reviewer_role,reason "
                            "FROM mlops_proposal_events WHERE proposal_id=:id "
                            "ORDER BY event_number DESC LIMIT 1"
                        ),
                        {"id": proposal_id},
                    )
                )
                .mappings()
                .one_or_none()
            )
            if latest is not None and latest["state"] == target_state:
                if (
                    latest["proposal_checksum"] == proposal_checksum
                    and latest["environment"] == environment
                    and latest["reviewer_id"] == reviewer_id.strip()
                    and latest["reviewer_role"] == reviewer_role
                    and latest["reason"] == reason.strip()
                ):
                    return target_state
                raise ControlPlaneConflict("proposal already has a different human decision")
            if latest is None or latest["state"] != "REVIEW_REQUIRED":
                raise ControlPlaneConflict("proposal is already reviewed or archived")
            await db.execute(
                text(
                    "INSERT INTO mlops_proposal_events(id,proposal_id,state,proposal_checksum,"
                    "environment,reviewer_id,reviewer_role,reason) "
                    "VALUES (:id,:proposal,:state,:checksum,:environment,"
                    ":reviewer,'mlops_reviewer',:reason)"
                ),
                {
                    "id": uuid4(),
                    "proposal": proposal_id,
                    "state": target_state,
                    "checksum": proposal_checksum,
                    "environment": environment,
                    "reviewer": reviewer_id.strip(),
                    "reason": reason.strip(),
                },
            )
        return target_state

    async def create_rollback_plan(
        self,
        proposal_id: UUID,
        *,
        target_binding_id: UUID,
        target_event_id: UUID,
        expected_active_binding_id: UUID,
        expected_active_event_id: UUID,
        body: dict[str, object],
    ) -> tuple[UUID, str]:
        """Persist a stale-checked 9D recovery plan without changing a serving binding."""
        require_controlled_environment()
        payload = json.dumps(body, sort_keys=True, separators=(",", ":"), allow_nan=False)
        if len(payload.encode("utf-8")) > 60_000:
            raise ValueError("rollback plan exceeds the database bound")
        content_checksum = stable_hash(body)
        async with self.database.session() as db, db.begin():
            proposal = (
                (
                    await db.execute(
                        text(
                            "SELECT p.source_role,p.candidate_kind,p.content_checksum,"
                            "r.state AS run_state,"
                            "(SELECT e.state FROM mlops_proposal_events e WHERE e.proposal_id=p.id "
                            "ORDER BY e.event_number DESC LIMIT 1) AS review_state "
                            "FROM mlops_proposals p JOIN mlops_runs r ON r.id=p.run_id "
                            "WHERE p.id=:id FOR UPDATE OF p"
                        ),
                        {"id": proposal_id},
                    )
                )
                .mappings()
                .one_or_none()
            )
            if (
                proposal is None
                or proposal["run_state"] != "COMPLETED"
                or proposal["review_state"] != "APPROVED_FOR_CONTROLLED_REVIEW"
            ):
                raise ControlPlaneConflict(
                    "rollback plan requires a completed human-reviewed proposal"
                )
            target = (
                (
                    await db.execute(
                        text(
                            "SELECT b.id,b.result_kind,b.subject_key,b.source_role,"
                            "b.environment,b.scope,b.model_version_id,b.detector_version_id,"
                            "b.artifact_checksum,b.feature_set_version,b.feature_set_checksum,"
                            "b.schema_checksum,"
                            "latest.id AS latest_event_id,latest.event_type AS latest_event_type "
                            "FROM prediction_serving_bindings b JOIN LATERAL ("
                            "SELECT e.id,e.event_type FROM prediction_serving_events e "
                            "WHERE e.binding_id=b.id ORDER BY e.event_number DESC LIMIT 1) "
                            "latest ON true "
                            "WHERE b.id=:id"
                        ),
                        {"id": target_binding_id},
                    )
                )
                .mappings()
                .one_or_none()
            )
            if (
                target is None
                or target["latest_event_type"] != "SUPERSEDED"
                or target["environment"] != require_controlled_environment()
                or target["source_role"] != proposal["source_role"]
            ):
                raise ControlPlaneConflict(
                    "rollback target is stale, revoked or outside proposal scope"
                )
            serving_slot = slot_key(
                cast(PredictionKind, str(target["result_kind"])),
                str(target["subject_key"]),
                ServingSourceRole(str(target["source_role"])),
                str(target["environment"]),
                str(target["scope"]),
            )
            await db.execute(
                text("SELECT pg_advisory_xact_lock(hashtextextended(:key,0))"),
                {"key": serving_slot},
            )
            target = (
                (
                    await db.execute(
                        text(
                            "SELECT b.id,b.result_kind,b.subject_key,b.source_role,"
                            "b.environment,b.scope,b.model_version_id,b.detector_version_id,"
                            "b.artifact_checksum,b.feature_set_version,b.feature_set_checksum,"
                            "b.schema_checksum,"
                            "latest.id AS latest_event_id,latest.event_type AS latest_event_type "
                            "FROM prediction_serving_bindings b JOIN LATERAL ("
                            "SELECT e.id,e.event_type FROM prediction_serving_events e "
                            "WHERE e.binding_id=b.id ORDER BY e.event_number DESC LIMIT 1) "
                            "latest ON true "
                            "WHERE b.id=:id FOR UPDATE OF b"
                        ),
                        {"id": target_binding_id},
                    )
                )
                .mappings()
                .one_or_none()
            )
            if (
                target is None
                or target["latest_event_id"] != target_event_id
                or target["latest_event_type"] != "SUPERSEDED"
            ):
                raise ControlPlaneConflict("rollback target changed during readiness verification")
            active = (
                (
                    await db.execute(
                        text(
                            "SELECT b.id,latest.id AS latest_event_id,"
                            "COALESCE(b.model_version_id,b.detector_version_id) AS version_id "
                            "FROM prediction_serving_bindings b "
                            "JOIN LATERAL (SELECT e.id,e.event_type "
                            "FROM prediction_serving_events e "
                            "WHERE e.binding_id=b.id ORDER BY e.event_number DESC LIMIT 1) "
                            "latest ON true "
                            "WHERE b.result_kind=:kind AND b.subject_key=:subject "
                            "AND b.source_role=:role "
                            "AND b.environment=:environment AND b.scope=:scope "
                            "AND latest.event_type IN ('ACTIVATED','ROLLED_BACK') ORDER BY b.id "
                            "LIMIT 3 FOR UPDATE OF b"
                        ),
                        {
                            "kind": target["result_kind"],
                            "subject": target["subject_key"],
                            "role": target["source_role"],
                            "environment": target["environment"],
                            "scope": target["scope"],
                        },
                    )
                )
                .mappings()
                .all()
            )
            if len(active) != 1 or (
                active[0]["id"] != expected_active_binding_id
                or active[0]["latest_event_id"] != expected_active_event_id
            ):
                raise ControlPlaneConflict(
                    "active binding changed while rollback plan was prepared"
                )
            if (
                body.get("expected_active_binding_id") != str(expected_active_binding_id)
                or body.get("expected_active_event_id") != str(expected_active_event_id)
                or body.get("target_binding_id") != str(target_binding_id)
                or body.get("target_event_id") != str(target_event_id)
                or body.get("proposal_id") != str(proposal_id)
                or body.get("proposal_checksum") != proposal["content_checksum"]
                or body.get("candidate_kind") != proposal["candidate_kind"]
                or body.get("result_kind") != target["result_kind"]
                or body.get("subject_key") != target["subject_key"]
                or body.get("source_role") != target["source_role"]
                or body.get("environment") != target["environment"]
                or body.get("scope") != target["scope"]
                or body.get("target_artifact_checksum") != target["artifact_checksum"]
                or body.get("target_version_id")
                != str(target["model_version_id"] or target["detector_version_id"])
                or body.get("target_feature_set_version") != target["feature_set_version"]
                or body.get("target_feature_set_checksum") != target["feature_set_checksum"]
                or body.get("target_schema_checksum") != target["schema_checksum"]
                or body.get("expected_active_version_id") != str(active[0]["version_id"])
                or body.get("serving_action") != "NONE"
                or body.get("real_world_predictive_validity") != "NOT_ESTABLISHED"
                or body.get("target_latest_event_type") != "SUPERSEDED"
                or body.get("candidate_validation") != "PASS"
            ):
                raise ValueError("rollback plan body does not match its immutable binding")
            rollback_limitations = body.get("scientific_limitations")
            required_rollback_limitations = (
                "A rollback readiness plan does not change the active serving binding.",
                "Any rollback requires a separate authorized Phase 9D operator action.",
                "Synthetic evaluation does not establish real-world predictive validity.",
                "Real-world mechanical failure predictive reliability remains NOT_ESTABLISHED.",
            )
            if not isinstance(rollback_limitations, list) or any(
                item not in rollback_limitations for item in required_rollback_limitations
            ):
                raise ValueError("rollback plan is missing required scientific limitations")
            existing = await db.scalar(
                text("SELECT id FROM mlops_rollback_plans WHERE content_checksum=:checksum"),
                {"checksum": content_checksum},
            )
            if existing is not None:
                return UUID(str(existing)), content_checksum
            plan_id = uuid4()
            await db.execute(
                text(
                    "INSERT INTO mlops_rollback_plans(id,proposal_id,target_binding_id,"
                    "target_event_id,"
                    "state,content_checksum,body) VALUES (:id,:proposal,:target,:event,"
                    "'READY_FOR_SEPARATE_9D_REVIEW',:checksum,CAST(:body AS jsonb))"
                ),
                {
                    "id": plan_id,
                    "proposal": proposal_id,
                    "target": target_binding_id,
                    "event": target_event_id,
                    "checksum": content_checksum,
                    "body": payload,
                },
            )
            return plan_id, content_checksum

    async def inspect_rollback_plan(self, plan_id: UUID) -> dict[str, Any]:
        """Read and checksum one immutable rollback readiness record."""
        require_controlled_environment()
        async with self.database.session() as db, db.begin():
            await db.execute(text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY"))
            row = (
                (
                    await db.execute(
                        text(
                            "SELECT id,proposal_id,target_binding_id,target_event_id,state,"
                            "content_checksum,body,created_at FROM mlops_rollback_plans "
                            "WHERE id=:id"
                        ),
                        {"id": plan_id},
                    )
                )
                .mappings()
                .one_or_none()
            )
        if row is None:
            raise ControlPlaneConflict("rollback plan does not exist")
        if stable_hash(row["body"]) != row["content_checksum"]:
            raise ControlPlaneConflict("rollback plan checksum is invalid")
        return {
            "schema_version": "phase10-rollback-inspection-v1",
            "plan": dict(row),
            "serving_action": "NONE",
            "real_world_predictive_validity": "NOT_ESTABLISHED",
        }
