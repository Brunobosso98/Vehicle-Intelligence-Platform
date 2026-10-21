from __future__ import annotations

import json
from datetime import datetime
from typing import Any, cast
from uuid import UUID, uuid4

from sqlalchemy import text

from vehicle_platform.anomalies.domain import SourceRole
from vehicle_platform.features.domain import canonical_json, stable_hash
from vehicle_platform.infrastructure.database import Database
from vehicle_platform.predictions.domain import (
    FeatureSnapshot,
    PredictionError,
    PredictionKind,
    PredictionResponse,
    PullContext,
    ServingBinding,
    ServingCandidate,
    ServingEventType,
)

CONTROLLED_SCOPE = "controlled-engineering-dataset"
FEATURE_SET_VERSION = "phase9a-pull-v2"
_SERVE_ROLES = {role.value: role for role in SourceRole if role is not SourceRole.MIXED}


def slot_key(
    result_kind: PredictionKind,
    subject_key: str,
    source_role: SourceRole,
    environment: str,
    scope: str = CONTROLLED_SCOPE,
) -> str:
    return stable_hash(
        {
            "result_kind": result_kind,
            "subject_key": subject_key,
            "source_role": source_role.value,
            "environment": environment,
            "scope": scope,
        }
    )


def json_object(value: object) -> dict[str, Any]:
    if isinstance(value, dict):
        return cast(dict[str, Any], value)
    if isinstance(value, str):
        try:
            decoded = json.loads(value)
        except json.JSONDecodeError:
            return {}
        return decoded if isinstance(decoded, dict) else {}
    return {}


def _source_role(source_type: str, metadata: dict[str, Any]) -> SourceRole:
    declared = metadata.get("data_role")
    if source_type == "synthetic":
        return SourceRole.SYNTHETIC
    if isinstance(declared, str) and declared in _SERVE_ROLES:
        return _SERVE_ROLES[declared]
    if source_type in {"csv", "replay"}:
        return (
            SourceRole.IMPORTED_FIXTURE if metadata.get("fixture") is True else SourceRole.IMPORTED
        )
    if source_type == "obd":
        return SourceRole.REAL_VEHICLE
    return SourceRole.MIXED


class PredictionRepository:
    """Bounded persistence and canonical Phase 9A lookup for controlled serving."""

    def __init__(self, database: Database) -> None:
        self.database = database

    async def pull_context(self, pull_id: UUID) -> PullContext | None:
        async with self.database.session() as db:
            row = (
                (
                    await db.execute(
                        text(
                            "SELECT p.id,p.vehicle_id,p.session_id,p.configuration_id AS pull_configuration_id,"
                            "p.started_at AS pull_started_at,p.ended_at AS pull_ended_at,p.created_at AS pull_created_at,"
                            "s.configuration_id AS session_configuration_id,s.created_at AS session_created_at,"
                            "s.status AS session_status,s.source_type,s.metadata AS session_metadata,"
                            "v.created_at AS vehicle_created_at FROM pulls p "
                            "JOIN driving_sessions s ON s.id=p.session_id "
                            "JOIN vehicles v ON v.id=p.vehicle_id "
                            "WHERE p.id=:pull_id AND s.vehicle_id=p.vehicle_id"
                        ),
                        {"pull_id": pull_id},
                    )
                )
                .mappings()
                .one_or_none()
            )
        if row is None:
            return None
        metadata = json_object(row["session_metadata"])
        source_type = str(row["source_type"])
        return PullContext(
            pull_id=cast(UUID, row["id"]),
            vehicle_id=cast(UUID, row["vehicle_id"]),
            session_id=cast(UUID, row["session_id"]),
            pull_configuration_id=cast(UUID | None, row["pull_configuration_id"]),
            session_configuration_id=cast(UUID | None, row["session_configuration_id"]),
            pull_started_at=cast(datetime, row["pull_started_at"]),
            pull_ended_at=cast(datetime | None, row["pull_ended_at"]),
            pull_created_at=cast(datetime, row["pull_created_at"]),
            session_created_at=cast(datetime, row["session_created_at"]),
            vehicle_created_at=cast(datetime, row["vehicle_created_at"]),
            session_status=str(row["session_status"]),
            source_type=source_type,
            source_role=_source_role(source_type, metadata),
        )

    async def feature_snapshot(
        self, pull_id: UUID, observation_cutoff: datetime
    ) -> FeatureSnapshot | None:
        async with self.database.session() as db:
            row = (
                (
                    await db.execute(
                        text(
                            "SELECT fs.*,fv.version AS feature_version,fv.checksum AS feature_version_checksum,"
                            "p.started_at AS pull_started_at,p.ended_at AS pull_ended_at,"
                            "p.created_at AS pull_created_at,p.configuration_id AS pull_configuration_id,"
                            "s.created_at AS session_created_at,s.configuration_id AS session_configuration_id,"
                            "s.source_type,s.metadata AS session_metadata,v.created_at AS vehicle_created_at "
                            "FROM feature_sets fs JOIN feature_set_versions fv ON fv.id=fs.feature_set_version_id "
                            "JOIN pulls p ON p.id=fs.pull_id JOIN driving_sessions s ON s.id=fs.session_id "
                            "JOIN vehicles v ON v.id=fs.vehicle_id "
                            "WHERE fs.pull_id=:pull_id AND fs.entity_scope='pull' AND fv.version=:version "
                            "AND fs.observation_cutoff<=:cutoff "
                            "ORDER BY fs.observation_cutoff DESC,fs.generated_at DESC,fs.id DESC LIMIT 1"
                        ),
                        {
                            "pull_id": pull_id,
                            "version": FEATURE_SET_VERSION,
                            "cutoff": observation_cutoff,
                        },
                    )
                )
                .mappings()
                .one_or_none()
            )
            if row is None:
                return None
            fs_cutoff = cast(datetime, row["observation_cutoff"])
            started_at = cast(datetime, row["pull_started_at"])
            explicit_configuration_id = (
                row["session_configuration_id"] or row["pull_configuration_id"]
            )
            configuration = None
            if explicit_configuration_id is not None:
                configuration = (
                    (
                        await db.execute(
                            text(
                                "SELECT id,created_at,effective_at,ended_at FROM vehicle_configurations "
                                "WHERE id=:id AND vehicle_id=:vehicle AND created_at<=:cutoff"
                            ),
                            {
                                "id": explicit_configuration_id,
                                "vehicle": row["vehicle_id"],
                                "cutoff": fs_cutoff,
                            },
                        )
                    )
                    .mappings()
                    .one_or_none()
                )
                if configuration is not None and not (
                    configuration["effective_at"] <= started_at
                    and (
                        configuration["ended_at"] is None or configuration["ended_at"] > started_at
                    )
                ):
                    configuration = None
            if configuration is None:
                configuration = (
                    (
                        await db.execute(
                            text(
                                "SELECT id,created_at,effective_at,ended_at FROM vehicle_configurations "
                                "WHERE vehicle_id=:vehicle AND effective_at<=:at "
                                "AND (ended_at IS NULL OR ended_at>:at) AND created_at<=:cutoff "
                                "ORDER BY effective_at DESC,id LIMIT 1"
                            ),
                            {"vehicle": row["vehicle_id"], "at": started_at, "cutoff": fs_cutoff},
                        )
                    )
                    .mappings()
                    .one_or_none()
                )
            resolved_configuration_id = (
                cast(UUID | None, configuration["id"]) if configuration is not None else None
            )
            modifications = (
                (
                    await db.execute(
                        text(
                            "SELECT id FROM modifications WHERE vehicle_id=:vehicle "
                            "AND installed_at<=:at AND (removed_at IS NULL OR removed_at>:at) "
                            "AND created_at<=:cutoff "
                            "AND (configuration_id IS NULL OR configuration_id=CAST(:configuration AS uuid)) "
                            "ORDER BY installed_at,id LIMIT 1001"
                        ),
                        {
                            "vehicle": row["vehicle_id"],
                            "at": started_at,
                            "cutoff": fs_cutoff,
                            "configuration": resolved_configuration_id,
                        },
                    )
                )
                .scalars()
                .all()
            )
        source_type = str(row["source_type"])
        quality_metadata = json_object(row["quality_metadata"])
        provenance = json_object(row["provenance"])
        available_signals = quality_metadata.get("available_signals", [])
        return FeatureSnapshot(
            feature_set_id=cast(UUID, row["id"]),
            pull_id=cast(UUID, row["pull_id"]),
            vehicle_id=cast(UUID, row["vehicle_id"]),
            configuration_id=cast(UUID | None, row["configuration_id"]),
            session_id=cast(UUID, row["session_id"]),
            feature_set_version_id=cast(UUID, row["feature_set_version_id"]),
            feature_set_version=str(row["feature_version"]),
            feature_set_version_checksum=str(row["feature_version_checksum"]),
            generated_at=cast(datetime, row["generated_at"]),
            observation_cutoff=fs_cutoff,
            source_window_end=cast(datetime, row["source_window_end"]),
            source_hash=str(row["source_hash"]),
            provenance_hash=str(row["provenance_hash"]),
            source_role=_source_role(source_type, quality_metadata),
            source_type=source_type,
            available_signals=tuple(
                sorted(item for item in available_signals if isinstance(item, str))
            )
            if isinstance(available_signals, list)
            else (),
            resolved_configuration_id=resolved_configuration_id,
            values=json_object(row["feature_values"]),
            quality_metadata=quality_metadata,
            provenance=provenance,
            pull_started_at=started_at,
            pull_ended_at=cast(datetime, row["pull_ended_at"]),
            pull_created_at=cast(datetime, row["pull_created_at"]),
            session_created_at=cast(datetime, row["session_created_at"]),
            vehicle_created_at=cast(datetime, row["vehicle_created_at"]),
            configuration_created_at=(
                cast(datetime, configuration["created_at"]) if configuration is not None else None
            ),
            configuration_effective_at=(
                cast(datetime, configuration["effective_at"]) if configuration is not None else None
            ),
            configuration_ended_at=(
                cast(datetime | None, configuration["ended_at"])
                if configuration is not None
                else None
            ),
            current_modification_ids=tuple(sorted(str(item) for item in modifications)),
        )

    async def model_candidate(self, version_id: UUID) -> dict[str, Any] | None:
        async with self.database.session() as db:
            row = (
                (
                    await db.execute(
                        text(
                            "SELECT mv.*,m.task,m.state AS model_state,sd.manifest AS dataset_manifest,"
                            "fsv.version AS feature_version,fsv.checksum AS feature_version_checksum "
                            "FROM ml_model_versions mv JOIN ml_models m ON m.id=mv.ml_model_id "
                            "JOIN supervised_datasets sd ON sd.id=mv.supervised_dataset_id "
                            "JOIN feature_set_versions fsv ON fsv.id=mv.feature_set_version_id "
                            "WHERE mv.id=:version_id"
                        ),
                        {"version_id": version_id},
                    )
                )
                .mappings()
                .one_or_none()
            )
        return dict(row) if row is not None else None

    async def detector_candidate(self, version_id: UUID) -> dict[str, Any] | None:
        async with self.database.session() as db:
            row = (
                (
                    await db.execute(
                        text(
                            "SELECT dv.*,d.family,d.method,d.key,rd.source_role,rd.feature_set_version,"
                            "rd.feature_set_version_checksum,rd.manifest AS reference_manifest "
                            "FROM anomaly_detector_versions dv "
                            "JOIN anomaly_detector_definitions d ON d.id=dv.detector_definition_id "
                            "JOIN anomaly_reference_datasets rd ON rd.id=dv.reference_dataset_id "
                            "WHERE dv.id=:version_id"
                        ),
                        {"version_id": version_id},
                    )
                )
                .mappings()
                .one_or_none()
            )
        return dict(row) if row is not None else None

    async def create_approval(
        self,
        candidate: ServingCandidate,
        *,
        environment: str,
        reason: str,
        operator_id: str,
        review_reference: str,
    ) -> tuple[UUID, UUID]:
        binding_id = uuid4()
        key = slot_key(
            candidate.result_kind, candidate.subject_key, candidate.source_role, environment
        )
        async with self.database.session() as db, db.begin():
            await db.execute(
                text(
                    "INSERT INTO prediction_serving_bindings(id,result_kind,subject_key,source_role,"
                    "environment,scope,model_version_id,detector_version_id,artifact_checksum,"
                    "feature_set_version,feature_set_checksum,schema_checksum,reason,operator_id,"
                    "review_reference) VALUES(:id,:kind,:subject,:role,:environment,:scope,:model,:detector,"
                    ":artifact,:feature_version,:feature_checksum,:schema,:reason,:operator,:review)"
                ),
                {
                    "id": binding_id,
                    "kind": candidate.result_kind,
                    "subject": candidate.subject_key,
                    "role": candidate.source_role.value,
                    "environment": environment,
                    "scope": CONTROLLED_SCOPE,
                    "model": candidate.version_id if candidate.result_kind == "next_pull" else None,
                    "detector": candidate.version_id
                    if candidate.result_kind == "anomaly"
                    else None,
                    "artifact": candidate.artifact_checksum,
                    "feature_version": candidate.feature_set_version,
                    "feature_checksum": candidate.feature_set_checksum,
                    "schema": candidate.schema_checksum,
                    "reason": reason,
                    "operator": operator_id,
                    "review": review_reference,
                },
            )
            event_id = await self._append_event(
                db,
                binding_id=binding_id,
                slot=key,
                event_type="APPROVED",
                reason=reason,
                operator_id=operator_id,
                related_binding_id=None,
            )
        return binding_id, event_id

    async def bindings_for_slot(
        self,
        result_kind: PredictionKind,
        subject_key: str,
        source_role: SourceRole,
        environment: str,
        scope: str = CONTROLLED_SCOPE,
    ) -> list[ServingBinding]:
        async with self.database.session() as db:
            rows = (
                (
                    await db.execute(
                        text(
                            "SELECT b.*,latest.id AS latest_event_id,latest.event_type AS latest_event_type "
                            "FROM prediction_serving_bindings b JOIN LATERAL ("
                            "SELECT e.id,e.event_type,e.event_number FROM prediction_serving_events e "
                            "WHERE e.binding_id=b.id ORDER BY e.event_number DESC LIMIT 1) latest ON true "
                            "WHERE b.result_kind=:kind AND b.subject_key=:subject AND b.source_role=:role "
                            "AND b.environment=:environment AND b.scope=:scope "
                            "ORDER BY b.created_at DESC,b.id LIMIT 100"
                        ),
                        {
                            "kind": result_kind,
                            "subject": subject_key,
                            "role": source_role.value,
                            "environment": environment,
                            "scope": scope,
                        },
                    )
                )
                .mappings()
                .all()
            )
        return [self._binding(dict(row)) for row in rows]

    async def binding(self, binding_id: UUID) -> ServingBinding | None:
        async with self.database.session() as db:
            row = (
                (
                    await db.execute(
                        text(
                            "SELECT b.*,latest.id AS latest_event_id,latest.event_type AS latest_event_type "
                            "FROM prediction_serving_bindings b JOIN LATERAL ("
                            "SELECT e.id,e.event_type,e.event_number FROM prediction_serving_events e "
                            "WHERE e.binding_id=b.id ORDER BY e.event_number DESC LIMIT 1) latest ON true "
                            "WHERE b.id=:id"
                        ),
                        {"id": binding_id},
                    )
                )
                .mappings()
                .one_or_none()
            )
        return self._binding(dict(row)) if row is not None else None

    async def transition_binding(
        self,
        binding_id: UUID,
        action: str,
        *,
        reason: str,
        operator_id: str,
    ) -> tuple[ServingBinding, UUID]:
        async with self.database.session() as db, db.begin():
            row = (
                (
                    await db.execute(
                        text("SELECT * FROM prediction_serving_bindings WHERE id=:id"),
                        {"id": binding_id},
                    )
                )
                .mappings()
                .one_or_none()
            )
            if row is None:
                raise PredictionError(
                    404, "PREDICTION_BINDING_NOT_FOUND", "Serving approval not found"
                )
            raw = dict(row)
            key = slot_key(
                cast(PredictionKind, str(raw["result_kind"])),
                str(raw["subject_key"]),
                SourceRole(str(raw["source_role"])),
                str(raw["environment"]),
                str(raw["scope"]),
            )
            await db.execute(
                text("SELECT pg_advisory_xact_lock(hashtextextended(:key,0))"), {"key": key}
            )
            states = await self._binding_states_for_slot(db, raw)
            target = next(item for item in states if item.id == binding_id)
            if target.latest_event_type is ServingEventType.REVOKED:
                raise PredictionError(
                    409, "PREDICTION_APPROVAL_REVOKED", "Serving approval was revoked"
                )
            active = [item for item in states if item.is_active]
            if action == "activate" and target.is_active:
                return target, target.latest_event_id
            if action == "rollback" and target.latest_event_type is not ServingEventType.SUPERSEDED:
                raise PredictionError(
                    409,
                    "PREDICTION_ROLLBACK_CONFLICT",
                    "Rollback target is not a reviewed inactive version",
                )
            if action not in {"activate", "revoke", "rollback"}:
                raise ValueError("unknown serving binding transition")
            if action == "revoke":
                event_id = await self._append_event(
                    db,
                    binding_id=binding_id,
                    slot=key,
                    event_type="REVOKED",
                    reason=reason,
                    operator_id=operator_id,
                    related_binding_id=None,
                )
            else:
                for prior in active:
                    if prior.id == binding_id:
                        continue
                    await self._append_event(
                        db,
                        binding_id=prior.id,
                        slot=key,
                        event_type="SUPERSEDED",
                        reason=reason,
                        operator_id=operator_id,
                        related_binding_id=binding_id,
                    )
                event_id = await self._append_event(
                    db,
                    binding_id=binding_id,
                    slot=key,
                    event_type="ROLLED_BACK" if action == "rollback" else "ACTIVATED",
                    reason=reason,
                    operator_id=operator_id,
                    related_binding_id=active[0].id if active else None,
                )
            latest = await self._binding_states_for_slot(db, raw)
            updated = next(item for item in latest if item.id == binding_id)
        return updated, event_id

    async def active_bindings(
        self,
        environment: str,
        *,
        limit: int,
        offset: int,
        result_kind: PredictionKind | None = None,
        source_role: SourceRole | None = None,
    ) -> list[ServingBinding]:
        conditions = [
            "b.environment=:environment",
            "latest.event_type IN ('ACTIVATED','ROLLED_BACK')",
        ]
        parameters: dict[str, Any] = {
            "environment": environment,
            "limit": limit,
            "offset": offset,
        }
        if result_kind is not None:
            conditions.append("b.result_kind=:kind")
            parameters["kind"] = result_kind
        if source_role is not None:
            conditions.append("b.source_role=:role")
            parameters["role"] = source_role.value

        async with self.database.session() as db:
            rows = (
                (
                    await db.execute(
                        text(
                            "SELECT b.*,latest.id AS latest_event_id,latest.event_type AS latest_event_type "
                            "FROM prediction_serving_bindings b JOIN LATERAL ("
                            "SELECT e.id,e.event_type,e.event_number FROM prediction_serving_events e "
                            "WHERE e.binding_id=b.id ORDER BY e.event_number DESC LIMIT 1) latest ON true "
                            "WHERE " + " AND ".join(conditions) + " "
                            "ORDER BY b.result_kind,b.subject_key,b.source_role,b.model_version_id,b.detector_version_id,b.id "
                            "LIMIT :limit OFFSET :offset"
                        ),
                        parameters,
                    )
                )
                .mappings()
                .all()
            )
        return [self._binding(dict(row)) for row in rows]

    async def find_replay(
        self, fingerprint: str, client_key_hash: str | None
    ) -> tuple[str, dict[str, Any]] | None:
        async with self.database.session() as db:
            row = None
            if client_key_hash is not None:
                row = (
                    (
                        await db.execute(
                            text(
                                "SELECT request_fingerprint,response_body FROM prediction_receipts "
                                "WHERE client_key_hash=:client_key"
                            ),
                            {"client_key": client_key_hash},
                        )
                    )
                    .mappings()
                    .one_or_none()
                )
            if row is None:
                row = (
                    (
                        await db.execute(
                            text(
                                "SELECT request_fingerprint,response_body FROM prediction_receipts "
                                "WHERE request_fingerprint=:fingerprint"
                            ),
                            {"fingerprint": fingerprint},
                        )
                    )
                    .mappings()
                    .one_or_none()
                )
        return (str(row["request_fingerprint"]), json_object(row["response_body"])) if row else None

    async def persist_receipt(
        self,
        *,
        fingerprint: str,
        client_key_hash: str | None,
        binding: ServingBinding,
        response: PredictionResponse,
        pull_id: UUID,
        feature_snapshot: FeatureSnapshot | None,
        anomaly_run_id: UUID | None,
        anomaly_finding_id: UUID | None,
    ) -> tuple[PredictionResponse, bool]:
        body = response.model_dump(mode="json", exclude_none=True)
        values = {
            "id": response.receipt_id,
            "fingerprint": fingerprint,
            "client_key": client_key_hash,
            "schema": response.schema_version,
            "kind": binding.result_kind,
            "subject": binding.subject_key,
            "horizon": response.horizon,
            "status": response.status.value,
            "reason": response.reason_code,
            "binding": binding.id,
            "binding_event": binding.latest_event_id,
            "model": binding.model_version_id,
            "detector": binding.detector_version_id,
            "anomaly_run": anomaly_run_id,
            "anomaly_finding": anomaly_finding_id,
            "pull": pull_id,
            "feature_set": feature_snapshot.feature_set_id if feature_snapshot else None,
            "feature_version": feature_snapshot.feature_set_version if feature_snapshot else None,
            "feature_checksum": feature_snapshot.source_hash if feature_snapshot else None,
            "provenance_checksum": feature_snapshot.provenance_hash if feature_snapshot else None,
            "artifact": binding.artifact_checksum,
            "requested_cutoff": response.requested_cutoff,
            "effective_cutoff": response.effective_cutoff,
            "role": response.source_role.value,
            "engineering_score": response.engineering_validation_score,
            "anomaly_score": response.anomaly_score,
            "threshold": response.threshold,
            "decision": str(response.decision) if response.decision is not None else None,
            "coverage": response.quality.coverage,
            "quality": canonical_json(response.quality.model_dump(mode="json")),
            "body": canonical_json(body),
        }
        async with self.database.session() as db, db.begin():
            inserted = await db.execute(
                text(
                    "INSERT INTO prediction_receipts(id,request_fingerprint,client_key_hash,schema_version,"
                    "result_kind,subject_key,horizon,status,reason_code,binding_id,binding_event_id,"
                    "model_version_id,detector_version_id,anomaly_run_id,anomaly_finding_id,pull_id,"
                    "feature_set_id,feature_set_version,feature_set_checksum,feature_provenance_checksum,"
                    "artifact_checksum,requested_cutoff,effective_cutoff,source_role,engineering_validation_score,"
                    "anomaly_score,threshold,decision,coverage,quality_summary,response_body) VALUES(:id,"
                    ":fingerprint,:client_key,:schema,:kind,:subject,:horizon,:status,:reason,:binding,"
                    ":binding_event,:model,:detector,:anomaly_run,:anomaly_finding,:pull,:feature_set,"
                    ":feature_version,:feature_checksum,:provenance_checksum,:artifact,:requested_cutoff,"
                    ":effective_cutoff,:role,:engineering_score,:anomaly_score,:threshold,:decision,:coverage,"
                    "CAST(:quality AS jsonb),CAST(:body AS jsonb)) ON CONFLICT DO NOTHING RETURNING id"
                ),
                values,
            )
            created = inserted.scalar_one_or_none() is not None
            if not created:
                existing = (
                    (
                        await db.execute(
                            text(
                                "SELECT request_fingerprint,response_body FROM prediction_receipts "
                                "WHERE request_fingerprint=:fingerprint OR "
                                "(:client_key IS NOT NULL AND client_key_hash=:client_key) "
                                "ORDER BY CASE WHEN request_fingerprint=:fingerprint THEN 0 ELSE 1 END LIMIT 1"
                            ),
                            {"fingerprint": fingerprint, "client_key": client_key_hash},
                        )
                    )
                    .mappings()
                    .one_or_none()
                )
                if existing is None:
                    raise PredictionError(
                        503,
                        "PREDICTION_RECEIPT_UNAVAILABLE",
                        "Prediction receipt could not be persisted",
                    )
                old_fingerprint = str(existing["request_fingerprint"])
                if old_fingerprint != fingerprint:
                    raise PredictionError(
                        409,
                        "PREDICTION_IDEMPOTENCY_CONFLICT",
                        "Idempotency key is already bound to a different request",
                    )
                return PredictionResponse.model_validate(
                    json_object(existing["response_body"])
                ), False
        return response, True

    async def receipt(self, receipt_id: UUID) -> PredictionResponse | None:
        async with self.database.session() as db:
            body = (
                await db.execute(
                    text("SELECT response_body FROM prediction_receipts WHERE id=:id"),
                    {"id": receipt_id},
                )
            ).scalar_one_or_none()
        return PredictionResponse.model_validate(json_object(body)) if body is not None else None

    async def _append_event(
        self,
        db: Any,
        *,
        binding_id: UUID,
        slot: str,
        event_type: str,
        reason: str,
        operator_id: str,
        related_binding_id: UUID | None,
    ) -> UUID:
        event_id = (
            await db.execute(
                text(
                    "INSERT INTO prediction_serving_events(binding_id,related_binding_id,slot_key,"
                    "event_type,reason,operator_id) VALUES(:binding,:related,:slot,:event,:reason,:operator) "
                    "RETURNING id"
                ),
                {
                    "binding": binding_id,
                    "related": related_binding_id,
                    "slot": slot,
                    "event": event_type,
                    "reason": reason,
                    "operator": operator_id,
                },
            )
        ).scalar_one()
        return cast(UUID, event_id)

    async def _binding_states_for_slot(
        self, db: Any, binding: dict[str, Any]
    ) -> list[ServingBinding]:
        rows = (
            (
                await db.execute(
                    text(
                        "SELECT b.*,latest.id AS latest_event_id,latest.event_type AS latest_event_type "
                        "FROM prediction_serving_bindings b JOIN LATERAL ("
                        "SELECT e.id,e.event_type,e.event_number FROM prediction_serving_events e "
                        "WHERE e.binding_id=b.id ORDER BY e.event_number DESC LIMIT 1) latest ON true "
                        "WHERE b.result_kind=:kind AND b.subject_key=:subject AND b.source_role=:role "
                        "AND b.environment=:environment AND b.scope=:scope ORDER BY b.created_at DESC,b.id LIMIT 100"
                    ),
                    {
                        "kind": binding["result_kind"],
                        "subject": binding["subject_key"],
                        "role": binding["source_role"],
                        "environment": binding["environment"],
                        "scope": binding["scope"],
                    },
                )
            )
            .mappings()
            .all()
        )
        return [self._binding(dict(row)) for row in rows]

    @staticmethod
    def _binding(row: dict[str, Any]) -> ServingBinding:
        return ServingBinding(
            id=cast(UUID, row["id"]),
            result_kind=cast(PredictionKind, str(row["result_kind"])),
            subject_key=str(row["subject_key"]),
            source_role=SourceRole(str(row["source_role"])),
            environment=str(row["environment"]),
            scope=str(row["scope"]),
            model_version_id=cast(UUID | None, row["model_version_id"]),
            detector_version_id=cast(UUID | None, row["detector_version_id"]),
            artifact_checksum=str(row["artifact_checksum"]),
            feature_set_version=str(row["feature_set_version"]),
            feature_set_checksum=str(row["feature_set_checksum"]),
            schema_checksum=str(row["schema_checksum"]),
            reason=str(row["reason"]),
            operator_id=str(row["operator_id"]),
            review_reference=str(row["review_reference"]),
            latest_event_id=cast(UUID, row["latest_event_id"]),
            latest_event_type=ServingEventType(str(row["latest_event_type"])),
        )
