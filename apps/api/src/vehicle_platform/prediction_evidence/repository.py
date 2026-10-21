"""Bounded source resolution and immutable Phase 9E persistence."""

from __future__ import annotations

import asyncio
import hashlib
import json
from concurrent.futures import Future, ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast
from uuid import UUID, uuid5

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from vehicle_platform.anomalies.domain import MAX_REFERENCE_ROWS
from vehicle_platform.features.domain import stable_hash
from vehicle_platform.features.registry import DEFAULT_REGISTRY
from vehicle_platform.infrastructure.database import Database
from vehicle_platform.ml.domain import MLTask
from vehicle_platform.ml.labels import get_model_spec
from vehicle_platform.prediction_evidence.canonical import (
    EVIDENCE_NAMESPACE,
    canonical_json,
    evidence_content_payload,
    evidence_identity_payload,
    sha256,
)
from vehicle_platform.prediction_evidence.domain import (
    ArtifactAvailability,
    EvidenceGapCode,
    EvidenceIntegrity,
    EvidenceSourceSnapshot,
    EvidenceVerificationResult,
    PredictionEvidenceBundle,
    SourceKind,
    SourceRecordSnapshot,
    VerificationOutcome,
)
from vehicle_platform.predictions.domain import PredictionError, PredictionResponse

_SOURCE_SCHEMA = {
    SourceKind.PREDICTION_RECEIPT: "0016:prediction_receipts:v1",
    SourceKind.SERVING_BINDING: "0016:prediction_serving_bindings:v1",
    SourceKind.APPROVAL_EVENT: "0016:prediction_serving_events:v1",
    SourceKind.FEATURE_SET: "0013:feature_sets:v1",
    SourceKind.FEATURE_VERSION: "0013:feature_set_versions:v1",
    SourceKind.MODEL_VERSION: "0014:ml_model_versions+label_definitions:v1",
    SourceKind.DETECTOR_VERSION: "0015:anomaly_detector_versions+definitions:v1",
    SourceKind.ANOMALY_RUN: "0015:anomaly_detection_runs:v1",
    SourceKind.ANOMALY_FINDING: "0015:anomaly_findings:v1",
    SourceKind.REFERENCE_DATASET: "0015:anomaly_reference_datasets+bounded-row-counts:v2",
}
_ARTIFACT_CHECK_EXECUTOR = ThreadPoolExecutor(
    max_workers=2, thread_name_prefix="prediction-evidence-artifact-check"
)


class PredictionEvidenceRepository:
    def __init__(
        self,
        database: Database,
        *,
        model_artifacts: Any | None = None,
        anomaly_artifacts: Any | None = None,
    ) -> None:
        self.database = database
        self.model_artifacts = model_artifacts
        self.anomaly_artifacts = anomaly_artifacts
        self._artifact_slots = asyncio.Semaphore(2)

    async def source_snapshot(self, receipt_id: UUID) -> EvidenceSourceSnapshot:
        try:
            async with asyncio.timeout(4.0), self.database.session() as db:
                async with db.begin():
                    await db.execute(
                        text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
                    )
                    await db.execute(text("SET LOCAL statement_timeout='3000ms'"))
                    receipt_row = await self._one(
                        db, "SELECT * FROM prediction_receipts WHERE id=:id", {"id": receipt_id}
                    )
                    if receipt_row is None:
                        raise PredictionError(
                            404, "PREDICTION_RECEIPT_NOT_FOUND", "Prediction receipt was not found"
                        )
                    records: dict[SourceKind, SourceRecordSnapshot] = {}
                    receipt = _row(receipt_row)
                    try:
                        response = PredictionResponse.model_validate(
                            _json_object(receipt["response_body"])
                        )
                    except Exception as error:
                        raise PredictionError(
                            409,
                            "PREDICTION_RECEIPT_SCHEMA_UNSUPPORTED",
                            "Stored prediction receipt schema is unsupported",
                        ) from error
                    self._put(records, SourceKind.PREDICTION_RECEIPT, receipt_id, receipt)
                    if not _receipt_matches_response(receipt, response):
                        return self._not_verifiable(
                            records, response, EvidenceGapCode.PROVENANCE_MISMATCH, failed=True
                        )
                    if not _response_decision_consistent(response):
                        return self._not_verifiable(
                            records, response, EvidenceGapCode.PROVENANCE_MISMATCH, failed=True
                        )

                    binding_row = await self._one(
                        db,
                        "SELECT * FROM prediction_serving_bindings WHERE id=:id",
                        {"id": receipt["binding_id"]},
                    )
                    event_row = await self._one(
                        db,
                        "SELECT * FROM prediction_serving_events WHERE id=:id",
                        {"id": receipt["binding_event_id"]},
                    )
                    if binding_row is None or event_row is None:
                        return self._not_verifiable(
                            records, response, EvidenceGapCode.EVIDENCE_SOURCE_MISSING
                        )
                    binding, event = _row(binding_row), _row(event_row)
                    self._put(
                        records, SourceKind.SERVING_BINDING, cast(UUID, binding["id"]), binding
                    )
                    self._put(records, SourceKind.APPROVAL_EVENT, cast(UUID, event["id"]), event)
                    if not _binding_matches_receipt(binding, event, receipt):
                        return self._not_verifiable(
                            records, response, EvidenceGapCode.PROVENANCE_MISMATCH, failed=True
                        )

                    feature: dict[str, Any] | None = None
                    as_of_modification_ids: list[str] = []
                    if receipt.get("feature_set_id") is not None:
                        feature_row = await self._one(
                            db,
                            "SELECT fs.*,fsv.version AS feature_version,fsv.checksum AS feature_version_checksum,"
                            "p.started_at AS pull_started_at,p.ended_at AS pull_ended_at,p.vehicle_id AS pull_vehicle_id,"
                            "p.configuration_id AS pull_configuration_id,s.vehicle_id AS session_vehicle_id,"
                            "s.configuration_id AS session_configuration_id,s.source_type,s.metadata AS session_metadata "
                            "FROM feature_sets fs JOIN feature_set_versions fsv ON fsv.id=fs.feature_set_version_id "
                            "JOIN pulls p ON p.id=fs.pull_id JOIN driving_sessions s ON s.id=fs.session_id "
                            "WHERE fs.id=:id LIMIT 1",
                            {"id": receipt["feature_set_id"]},
                        )
                        if feature_row is None:
                            return self._not_verifiable(
                                records, response, EvidenceGapCode.NO_FEATURE_SET
                            )
                        feature = _row(feature_row)
                        self._put(
                            records, SourceKind.FEATURE_SET, cast(UUID, feature["id"]), feature
                        )
                        version_row = await self._one(
                            db,
                            "SELECT * FROM feature_set_versions WHERE id=:id",
                            {"id": feature["feature_set_version_id"]},
                        )
                        if version_row is None:
                            return self._not_verifiable(
                                records, response, EvidenceGapCode.EVIDENCE_SOURCE_MISSING
                            )
                        version = _row(version_row)
                        self._put(
                            records, SourceKind.FEATURE_VERSION, cast(UUID, version["id"]), version
                        )
                        if _feature_version_checksum(version) != version.get("checksum"):
                            return self._not_verifiable(
                                records,
                                response,
                                EvidenceGapCode.SOURCE_SCHEMA_MISMATCH,
                                failed=True,
                            )
                        if not _feature_matches_receipt(feature, receipt, binding, response):
                            return self._not_verifiable(
                                records, response, EvidenceGapCode.PROVENANCE_MISMATCH, failed=True
                            )
                        if not _feature_values_match_provenance(feature):
                            return self._not_verifiable(
                                records, response, EvidenceGapCode.PROVENANCE_MISMATCH, failed=True
                            )
                        context_matches, as_of_modification_ids = await self._as_of_context_matches(
                            db, feature, receipt
                        )
                        if not context_matches:
                            return self._not_verifiable(
                                records, response, EvidenceGapCode.CONTEXT_INCOMPATIBLE, failed=True
                            )
                        self._put(
                            records, SourceKind.FEATURE_SET, cast(UUID, feature["id"]), feature
                        )
                    elif response.status.value == "READY_SCORE":
                        return self._not_verifiable(
                            records, response, EvidenceGapCode.NO_FEATURE_SET, failed=True
                        )

                    if response.result_type == "next_pull":
                        model_row = await self._one(
                            db,
                            "SELECT mv.*,m.task,ld.key AS label_key,ld.version AS label_version,"
                            "ld.definition AS label_definition,ld.checksum AS label_checksum "
                            "FROM ml_model_versions mv JOIN ml_models m ON m.id=mv.ml_model_id "
                            "JOIN label_definitions ld ON ld.id=mv.label_definition_id WHERE mv.id=:id",
                            {"id": receipt["model_version_id"]},
                        )
                        if model_row is None:
                            return self._not_verifiable(
                                records, response, EvidenceGapCode.EVIDENCE_SOURCE_MISSING
                            )
                        model = _row(model_row)
                        self._put(records, SourceKind.MODEL_VERSION, cast(UUID, model["id"]), model)
                        if (
                            model["task"] != (response.task.value if response.task else None)
                            or not _model_threshold_matches_response(model, response)
                            or model["artifact_checksum"] != receipt["artifact_checksum"]
                            or not _model_schema_consistent(model)
                            or model["created_at"] > receipt["created_at"]
                        ):
                            return self._not_verifiable(
                                records, response, EvidenceGapCode.PROVENANCE_MISMATCH, failed=True
                            )
                        if (
                            feature is not None
                            and model["feature_set_version_id"] != feature["feature_set_version_id"]
                        ):
                            return self._not_verifiable(
                                records,
                                response,
                                EvidenceGapCode.SOURCE_SCHEMA_MISMATCH,
                                failed=True,
                            )
                    else:
                        detector_row = await self._one(
                            db,
                            "SELECT dv.*,d.key AS definition_key,d.version AS definition_version,d.family,d.method,"
                            "d.definition,d.checksum AS definition_checksum,rd.id AS reference_id,rd.vehicle_id AS reference_vehicle_id,"
                            "rd.configuration_id AS reference_configuration_id,rd.feature_set_version AS reference_feature_version,"
                            "rd.feature_set_version_checksum AS reference_feature_version_checksum,rd.cohort_checksum,"
                            "rd.observation_cutoff AS reference_cutoff,rd.source_role AS reference_source_role,"
                            "rd.source_type AS reference_source_type,rd.policy_version,rd.checksum AS reference_checksum,"
                            "rd.row_count,rd.session_count,rd.manifest->'cohort' AS reference_cohort "
                            "FROM anomaly_detector_versions dv "
                            "JOIN anomaly_detector_definitions d ON d.id=dv.detector_definition_id "
                            "JOIN anomaly_reference_datasets rd ON rd.id=dv.reference_dataset_id WHERE dv.id=:id",
                            {"id": receipt["detector_version_id"]},
                        )
                        if detector_row is None:
                            return self._not_verifiable(
                                records, response, EvidenceGapCode.EVIDENCE_SOURCE_MISSING
                            )
                        detector = _row(detector_row)
                        self._put(
                            records,
                            SourceKind.DETECTOR_VERSION,
                            cast(UUID, detector["id"]),
                            detector,
                        )
                        reference_id = cast(UUID, detector["reference_id"])
                        reference = {
                            key: detector[key]
                            for key in (
                                "reference_id",
                                "reference_vehicle_id",
                                "reference_configuration_id",
                                "reference_feature_version",
                                "reference_feature_version_checksum",
                                "cohort_checksum",
                                "reference_cutoff",
                                "reference_source_role",
                                "reference_source_type",
                                "policy_version",
                                "reference_checksum",
                                "row_count",
                                "session_count",
                            )
                        }
                        reference["id"] = reference_id
                        reference_counts = await db.execute(
                            text(
                                "SELECT count(*)::integer AS row_count,"
                                "count(DISTINCT session_id)::integer AS session_count "
                                "FROM (SELECT session_id FROM anomaly_reference_rows "
                                "WHERE reference_dataset_id=:id LIMIT :limit) bounded_rows"
                            ),
                            {"id": reference_id, "limit": MAX_REFERENCE_ROWS + 1},
                        )
                        observed_counts = reference_counts.mappings().one()
                        reference["observed_row_count"] = int(observed_counts["row_count"])
                        reference["observed_session_count"] = int(observed_counts["session_count"])
                        self._put(records, SourceKind.REFERENCE_DATASET, reference_id, reference)
                        if (
                            reference["observed_row_count"] > MAX_REFERENCE_ROWS
                            or reference["observed_row_count"] != int(detector["row_count"])
                            or reference["observed_session_count"] != int(detector["session_count"])
                        ):
                            return self._not_verifiable(
                                records, response, EvidenceGapCode.PROVENANCE_MISMATCH, failed=True
                            )
                        if (
                            detector["artifact_checksum"] != receipt["artifact_checksum"]
                            or detector["family"] != response.family
                            or detector["threshold"] != response.threshold
                        ):
                            return self._not_verifiable(
                                records, response, EvidenceGapCode.PROVENANCE_MISMATCH, failed=True
                            )
                        if feature is not None and (
                            detector["reference_vehicle_id"] != feature["vehicle_id"]
                            or detector["reference_configuration_id"] != feature["configuration_id"]
                            or detector["reference_source_role"] != receipt["source_role"]
                            or detector["reference_cutoff"]
                            > (response.effective_cutoff or response.requested_cutoff)
                        ):
                            return self._not_verifiable(
                                records, response, EvidenceGapCode.CONTEXT_INCOMPATIBLE, failed=True
                            )
                        if feature is not None:
                            cohort = _json_object(detector.get("reference_cohort"))
                            if (
                                str(cohort.get("vehicle_id")) != str(feature["vehicle_id"])
                                or cohort.get("configuration_id")
                                != _source_configuration_id(feature)
                                or cohort.get("source_role") != receipt["source_role"]
                                or cohort.get("source_type") != feature["source_type"]
                                or sorted(str(item) for item in cohort.get("modification_ids", []))
                                != as_of_modification_ids
                            ):
                                return self._not_verifiable(
                                    records,
                                    response,
                                    EvidenceGapCode.CONTEXT_INCOMPATIBLE,
                                    failed=True,
                                )

                    finding_id, run_id = (
                        receipt.get("anomaly_finding_id"),
                        receipt.get("anomaly_run_id"),
                    )
                    if finding_id is not None and run_id is not None:
                        finding_row = await self._one(
                            db, "SELECT * FROM anomaly_findings WHERE id=:id", {"id": finding_id}
                        )
                        run_row = await self._one(
                            db, "SELECT * FROM anomaly_detection_runs WHERE id=:id", {"id": run_id}
                        )
                        if finding_row is None or run_row is None:
                            return self._not_verifiable(
                                records, response, EvidenceGapCode.EVIDENCE_SOURCE_MISSING
                            )
                        finding, run = _row(finding_row), _row(run_row)
                        self._put(
                            records, SourceKind.ANOMALY_FINDING, cast(UUID, finding["id"]), finding
                        )
                        self._put(records, SourceKind.ANOMALY_RUN, cast(UUID, run["id"]), run)
                        if not _finding_matches_receipt(finding, run, receipt, response):
                            return self._not_verifiable(
                                records, response, EvidenceGapCode.PROVENANCE_MISMATCH, failed=True
                            )
                        detector_record = records.get(SourceKind.DETECTOR_VERSION)
                        reference_record = records.get(SourceKind.REFERENCE_DATASET)
                        if (
                            detector_record is None
                            or reference_record is None
                            or not _finding_reference_matches(
                                finding, detector_record.payload, reference_record.payload
                            )
                        ):
                            return self._not_verifiable(
                                records, response, EvidenceGapCode.PROVENANCE_MISMATCH, failed=True
                            )
                        if feature and (
                            finding["vehicle_id"] != feature["vehicle_id"]
                            or finding["configuration_id"] != feature["configuration_id"]
                            or finding["source_role"] != receipt["source_role"]
                        ):
                            return self._not_verifiable(
                                records, response, EvidenceGapCode.CONTEXT_INCOMPATIBLE, failed=True
                            )
                    elif (
                        response.result_type == "anomaly" and response.status.value == "READY_SCORE"
                    ):
                        return self._not_verifiable(
                            records, response, EvidenceGapCode.EVIDENCE_SOURCE_MISSING, failed=True
                        )

                    artifact = await self._check_artifact_bounded(records, response)
                    if artifact is ArtifactAvailability.CHECKSUM_MISMATCH:
                        return self._not_verifiable(
                            records, response, EvidenceGapCode.PROVENANCE_MISMATCH, failed=True
                        )
                    gaps = (
                        (EvidenceGapCode.MODEL_ARTIFACT_UNAVAILABLE,)
                        if artifact is ArtifactAvailability.UNAVAILABLE
                        else ()
                    )
                    integrity = (
                        EvidenceIntegrity.VERIFIED_SNAPSHOT_ARTIFACT_UNAVAILABLE
                        if artifact is ArtifactAvailability.UNAVAILABLE
                        else EvidenceIntegrity.VERIFIED
                    )
                    return EvidenceSourceSnapshot(
                        receipt=records[SourceKind.PREDICTION_RECEIPT],
                        response=response,
                        records=records,
                        integrity=integrity,
                        gaps=gaps,
                        artifact_availability=artifact,
                    )
        except TimeoutError as error:
            raise PredictionError(
                503,
                "PREDICTION_EVIDENCE_BUDGET_EXCEEDED",
                "Evidence source lookup exceeded its time budget",
            ) from error

    async def _check_artifact_bounded(
        self,
        records: dict[SourceKind, SourceRecordSnapshot],
        response: PredictionResponse,
    ) -> ArtifactAvailability:
        await self._artifact_slots.acquire()
        loop = asyncio.get_running_loop()
        future: Future[ArtifactAvailability] = _ARTIFACT_CHECK_EXECUTOR.submit(
            _artifact_state,
            records,
            response,
            self.model_artifacts,
            self.anomaly_artifacts,
        )

        def release(_: Future[ArtifactAvailability]) -> None:
            try:
                loop.call_soon_threadsafe(self._artifact_slots.release)
            except RuntimeError:
                # Event loop is closing; process shutdown will release executor resources.
                pass

        future.add_done_callback(release)
        return await asyncio.wrap_future(future, loop=loop)

    async def persist(
        self, bundle: PredictionEvidenceBundle
    ) -> tuple[PredictionEvidenceBundle, bool]:
        body = canonical_json(bundle.model_dump(mode="json"))
        try:
            async with asyncio.timeout(4.0), self.database.session() as db:
                async with db.begin():
                    await db.execute(text("SET LOCAL statement_timeout='3000ms'"))
                    await db.execute(
                        text("SELECT pg_advisory_xact_lock(hashtextextended(:key,0))"),
                        {"key": f"phase9e:{bundle.receipt_id}:{bundle.schema_version}"},
                    )
                    existing = await self._one(
                        db,
                        "SELECT bundle_body,logical_fingerprint FROM prediction_evidence_bundles WHERE receipt_id=:receipt AND schema_version=:schema FOR UPDATE",
                        {"receipt": bundle.receipt_id, "schema": bundle.schema_version},
                    )
                    if existing is not None:
                        if existing["logical_fingerprint"] != bundle.logical_fingerprint:
                            raise PredictionError(
                                409,
                                "PREDICTION_EVIDENCE_IMMUTABLE_CONFLICT",
                                "Frozen evidence sources differ from the stored bundle",
                            )
                        stored = _decode_bundle(existing["bundle_body"])
                        if (
                            stored.logical_fingerprint != existing["logical_fingerprint"]
                            or sha256(evidence_content_payload(stored)) != stored.content_checksum
                            or sha256(evidence_identity_payload(stored))
                            != stored.logical_fingerprint
                            or uuid5(EVIDENCE_NAMESPACE, stored.logical_fingerprint)
                            != stored.evidence_id
                        ):
                            raise PredictionError(
                                409,
                                "PREDICTION_EVIDENCE_IMMUTABLE_CONFLICT",
                                "Stored evidence failed its immutable checksum",
                            )
                        return stored, False
                    await db.execute(
                        text(
                            "INSERT INTO prediction_evidence_bundles(id,receipt_id,schema_version,projection_version,verifier_policy_version,logical_fingerprint,content_checksum,provenance_manifest_checksum,result_type,horizon,source_role,effective_cutoff,completeness,integrity,bundle_body) "
                            "VALUES(:id,:receipt,:schema,:projection,:verifier,:logical,:content,:manifest,:kind,:horizon,:role,:cutoff,:complete,:integrity,CAST(:body AS jsonb))"
                        ),
                        {
                            "id": bundle.evidence_id,
                            "receipt": bundle.receipt_id,
                            "schema": bundle.schema_version,
                            "projection": bundle.projection_version,
                            "verifier": bundle.verifier_policy_version,
                            "logical": bundle.logical_fingerprint,
                            "content": bundle.content_checksum,
                            "manifest": bundle.provenance_manifest_checksum,
                            "kind": bundle.result_type.value,
                            "horizon": bundle.horizon.value,
                            "role": bundle.source_role.value,
                            "cutoff": bundle.effective_cutoff,
                            "complete": bundle.completeness.value,
                            "integrity": bundle.integrity.value,
                            "body": body,
                        },
                    )
                    source_refs = {
                        node.source_kind: (
                            node.source_entity_id,
                            node.source_checksum,
                            node.source_schema_checksum,
                        )
                        for node in bundle.nodes
                    }
                    for kind, (entity_id, checksum, schema_checksum) in source_refs.items():
                        await db.execute(
                            text(
                                "INSERT INTO prediction_evidence_sources(evidence_id,source_kind,source_entity_id,source_checksum,source_schema_checksum) VALUES(:evidence,:kind,:id,:checksum,:schema)"
                            ),
                            {
                                "evidence": bundle.evidence_id,
                                "kind": kind.value,
                                "id": entity_id,
                                "checksum": checksum,
                                "schema": schema_checksum,
                            },
                        )
                    for node in bundle.nodes:
                        await db.execute(
                            text(
                                "INSERT INTO prediction_evidence_nodes(evidence_id,node_id,source_kind,source_entity_id,node_type,trust_role,projection_class,valid_from,valid_through) VALUES(:evidence,:node,:kind,:source,:type,:trust,:projection,:from,:through)"
                            ),
                            {
                                "evidence": bundle.evidence_id,
                                "node": node.node_id,
                                "kind": node.source_kind.value,
                                "source": node.source_entity_id,
                                "type": node.node_type.value,
                                "trust": node.trust_role.value,
                                "projection": node.projection_class.value,
                                "from": node.valid_from,
                                "through": node.valid_through,
                            },
                        )
                    for edge in bundle.edges:
                        await db.execute(
                            text(
                                "INSERT INTO prediction_evidence_edges(evidence_id,edge_id,source_node_id,target_node_id,relation) VALUES(:evidence,:id,:source,:target,:relation)"
                            ),
                            {
                                "evidence": bundle.evidence_id,
                                "id": edge.edge_id,
                                "source": edge.source_node_id,
                                "target": edge.target_node_id,
                                "relation": edge.relation.value,
                            },
                        )
                    for fact in bundle.facts:
                        await db.execute(
                            text(
                                "INSERT INTO prediction_evidence_facts(evidence_id,fact_id,source_node_id,fact_type,fact_key,fact_value,fact_unit,cutoff,cutoff_eligible,quality,fact_body) VALUES(:evidence,:id,:source,:type,:key,CAST(:value AS jsonb),:unit,:cutoff,:eligible,:quality,CAST(:body AS jsonb))"
                            ),
                            {
                                "evidence": bundle.evidence_id,
                                "id": fact.fact_id,
                                "source": fact.source_node_id,
                                "type": fact.fact_type.value,
                                "key": fact.key,
                                "value": canonical_json(fact.value)
                                if fact.value is not None
                                else "null",
                                "unit": fact.unit,
                                "cutoff": fact.cutoff,
                                "eligible": fact.cutoff_eligible,
                                "quality": fact.quality.value,
                                "body": canonical_json(fact.model_dump(mode="json")),
                            },
                        )
                    for ordinal, gap in enumerate(bundle.gaps):
                        await db.execute(
                            text(
                                "INSERT INTO prediction_evidence_gaps(evidence_id,ordinal,gap_code,source_node_id,reason_code) VALUES(:evidence,:ordinal,:code,:node,:reason)"
                            ),
                            {
                                "evidence": bundle.evidence_id,
                                "ordinal": ordinal,
                                "code": gap.code.value,
                                "node": gap.source_node_id,
                                "reason": gap.reason_code,
                            },
                        )
            return bundle, True
        except TimeoutError as error:
            raise PredictionError(
                503,
                "PREDICTION_EVIDENCE_BUDGET_EXCEEDED",
                "Evidence persistence exceeded its time budget",
            ) from error
        except IntegrityError as error:
            raise PredictionError(
                409,
                "PREDICTION_EVIDENCE_IMMUTABLE_CONFLICT",
                "Evidence record conflicts with an immutable constraint",
            ) from error

    async def get(self, evidence_id: UUID) -> PredictionEvidenceBundle | None:
        async with asyncio.timeout(3.0), self.database.session() as db:
            row = await self._one(
                db,
                "SELECT bundle_body FROM prediction_evidence_bundles WHERE id=:id",
                {"id": evidence_id},
            )
        return _decode_bundle(row["bundle_body"]) if row else None

    async def get_for_receipt(self, receipt_id: UUID) -> PredictionEvidenceBundle | None:
        async with asyncio.timeout(3.0), self.database.session() as db:
            row = await self._one(
                db,
                "SELECT bundle_body FROM prediction_evidence_bundles WHERE receipt_id=:id AND schema_version='phase9e-prediction-evidence-v1'",
                {"id": receipt_id},
            )
        return _decode_bundle(row["bundle_body"]) if row else None

    async def audit_verification(
        self, evidence: PredictionEvidenceBundle, outcome: VerificationOutcome
    ) -> EvidenceVerificationResult:
        checked = datetime.now(UTC)
        async with asyncio.timeout(3.0), self.database.session() as db, db.begin():
            await db.execute(text("SET LOCAL statement_timeout='2500ms'"))
            await db.execute(
                text("SELECT pg_advisory_xact_lock(hashtextextended(:key,0))"),
                {"key": f"phase9e:audit:{evidence.evidence_id}"},
            )
            count = await db.scalar(
                text(
                    "SELECT count(*) FROM prediction_evidence_verification_audits "
                    "WHERE evidence_id=:id"
                ),
                {"id": evidence.evidence_id},
            )
            if int(count or 0) >= 32:
                raise PredictionError(
                    429,
                    "PREDICTION_EVIDENCE_AUDIT_BUDGET_EXHAUSTED",
                    "Verification audit limit reached for this evidence record",
                )
            await db.execute(
                text(
                    "INSERT INTO prediction_evidence_verification_audits(evidence_id,integrity,reason_codes,source_count,checked_at) VALUES(:id,:integrity,:reasons,:count,:checked)"
                ),
                {
                    "id": evidence.evidence_id,
                    "integrity": outcome.integrity.value,
                    "reasons": list(outcome.reason_codes),
                    "count": outcome.source_count,
                    "checked": checked,
                },
            )
        return EvidenceVerificationResult(
            schema_version="phase9e-verification-result-v1",
            evidence_id=evidence.evidence_id,
            receipt_id=evidence.receipt_id,
            integrity=outcome.integrity,
            checked_at=checked,
            source_count=outcome.source_count,
            reason_codes=list(outcome.reason_codes),
        )

    async def _one(self, db: Any, query: str, params: dict[str, Any]) -> dict[str, Any] | None:
        result = await db.execute(text(query), params)
        row = result.mappings().one_or_none()
        return dict(row) if row is not None else None

    @staticmethod
    def _put(
        records: dict[SourceKind, SourceRecordSnapshot],
        kind: SourceKind,
        entity_id: UUID,
        payload: dict[str, Any],
    ) -> None:
        records[kind] = SourceRecordSnapshot(
            kind=kind,
            entity_id=entity_id,
            checksum=sha256(payload),
            schema_checksum=sha256(_SOURCE_SCHEMA[kind]),
            payload=payload,
        )

    def _not_verifiable(
        self,
        records: dict[SourceKind, SourceRecordSnapshot],
        response: PredictionResponse,
        code: EvidenceGapCode,
        *,
        failed: bool = False,
    ) -> EvidenceSourceSnapshot:
        return EvidenceSourceSnapshot(
            receipt=records[SourceKind.PREDICTION_RECEIPT],
            response=response,
            records=records,
            integrity=EvidenceIntegrity.FAILED_SOURCE_MISMATCH
            if failed
            else EvidenceIntegrity.NOT_VERIFIABLE,
            gaps=(code,),
            artifact_availability=ArtifactAvailability.UNAVAILABLE,
        )

    async def _as_of_context_matches(
        self, db: Any, feature: dict[str, Any], receipt: dict[str, Any]
    ) -> tuple[bool, list[str]]:
        if (
            feature["vehicle_id"] != feature["pull_vehicle_id"]
            or feature["vehicle_id"] != feature["session_vehicle_id"]
        ):
            return False, []
        role = _source_role(
            str(feature["source_type"]), _json_object(feature.get("quality_metadata"))
        )
        if role != receipt["source_role"]:
            return False, []
        provenance = _json_object(feature.get("provenance"))
        context = _json_object(provenance.get("source_context"))
        expected = context.get("active_modification_ids", [])
        rows = (
            (
                await db.execute(
                    text(
                        "SELECT id FROM modifications WHERE vehicle_id=:vehicle AND installed_at<=:at "
                        "AND (removed_at IS NULL OR removed_at>:at) AND created_at<=:cutoff "
                        "AND (configuration_id IS NULL OR configuration_id=CAST(:configuration AS uuid)) ORDER BY installed_at,id LIMIT 1001"
                    ),
                    {
                        "vehicle": feature["vehicle_id"],
                        "at": feature["pull_started_at"],
                        "cutoff": feature["observation_cutoff"],
                        "configuration": feature["configuration_id"],
                    },
                )
            )
            .scalars()
            .all()
        )
        observed = sorted(str(item) for item in rows)
        valid = len(rows) <= 1000 and sorted(str(item) for item in expected) == observed
        return valid, observed if valid else []


def _decode_bundle(value: Any) -> PredictionEvidenceBundle:
    try:
        bundle = PredictionEvidenceBundle.model_validate_json(canonical_json(_json_object(value)))
    except Exception as error:
        raise PredictionError(
            409,
            "PREDICTION_EVIDENCE_IMMUTABLE_CONFLICT",
            "Stored evidence schema is invalid",
        ) from error
    if (
        sha256(evidence_content_payload(bundle)) != bundle.content_checksum
        or sha256(evidence_identity_payload(bundle)) != bundle.logical_fingerprint
        or uuid5(EVIDENCE_NAMESPACE, bundle.logical_fingerprint) != bundle.evidence_id
    ):
        raise PredictionError(
            409,
            "PREDICTION_EVIDENCE_IMMUTABLE_CONFLICT",
            "Stored evidence failed its immutable checksum",
        )
    return bundle


def _row(value: dict[str, Any]) -> dict[str, Any]:
    return {str(key): _json_safe(item) for key, item in value.items()}


def _json_safe(value: Any) -> Any:
    if isinstance(value, (datetime, UUID)):
        return value
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return value
    return value


def _json_object(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            decoded = json.loads(value)
        except json.JSONDecodeError:
            return {}
        return decoded if isinstance(decoded, dict) else {}
    return {}


def _feature_version_checksum(row: dict[str, Any]) -> str:
    return stable_hash(
        {
            "version": row.get("version"),
            "definitions": row.get("feature_definitions"),
            "generator_version": row.get("generator_version"),
            "source_schema_version": row.get("source_schema_version"),
            "selection_policy": row.get("selection_policy"),
            "quality_policy": row.get("quality_policy"),
            "temporal_policy": row.get("temporal_policy"),
        }
    )


def _feature_matches_receipt(
    feature: dict[str, Any],
    receipt: dict[str, Any],
    binding: dict[str, Any],
    response: PredictionResponse,
) -> bool:
    if feature["id"] != receipt.get("feature_set_id") or feature["pull_id"] != receipt["pull_id"]:
        return False
    if feature["source_hash"] != receipt.get("feature_set_checksum") or feature[
        "provenance_hash"
    ] != receipt.get("feature_provenance_checksum"):
        return False
    cutoff = response.effective_cutoff or response.requested_cutoff
    if feature["observation_cutoff"] > cutoff:
        return False
    if feature["generated_at"] > receipt["created_at"]:
        return False
    if (
        feature["feature_version"] != receipt.get("feature_set_version")
        or feature["feature_version"] != binding.get("feature_set_version")
        or feature["feature_version_checksum"] != binding.get("feature_set_checksum")
    ):
        return False
    provenance = _json_object(feature.get("provenance"))
    if provenance.get("source_hash") != feature["source_hash"]:
        return False
    expected = stable_hash(
        {
            "vehicle_id": feature["vehicle_id"],
            "configuration_id": provenance.get("configuration_id"),
            "session_id": feature["session_id"],
            "pull_id": feature["pull_id"],
            "source_hash": feature["source_hash"],
            "feature_set_version": provenance.get("feature_set_version"),
            "generator_version": provenance.get("generator_version"),
        }
    )
    return bool(expected == feature["provenance_hash"])


def _feature_values_match_provenance(feature: dict[str, Any]) -> bool:
    provenance = _json_object(feature.get("provenance"))
    lineage = _json_object(provenance.get("lineage"))
    values = _json_object(feature.get("feature_values"))
    if set(lineage) != set(values):
        return False
    for key, value in values.items():
        line = _json_object(lineage.get(key))
        if any(
            line.get(name) != value.get(name)
            for name in (
                "value",
                "unit",
                "quality",
                "missing_reason",
                "available_at",
                "source_window_start",
                "source_window_end",
            )
        ):
            return False
    return True


def _receipt_matches_response(receipt: dict[str, Any], response: PredictionResponse) -> bool:
    return (
        receipt.get("id") == response.receipt_id
        and receipt.get("schema_version") == response.schema_version
        and receipt.get("result_kind") == response.result_type
        and receipt.get("horizon") == response.horizon
        and receipt.get("status") == response.status.value
        and receipt.get("reason_code") == response.reason_code
        and receipt.get("source_role") == response.source_role.value
        and receipt.get("requested_cutoff") == response.requested_cutoff
        and receipt.get("effective_cutoff") == response.effective_cutoff
        and receipt.get("threshold") == response.threshold
        and receipt.get("decision")
        == (str(response.decision) if response.decision is not None else None)
        and receipt.get("engineering_validation_score") == response.engineering_validation_score
        and receipt.get("anomaly_score") == response.anomaly_score
        and receipt.get("coverage") == response.quality.coverage
        and canonical_json(_json_object(receipt.get("quality_summary")))
        == canonical_json(response.quality.model_dump(mode="json"))
    )


def _response_decision_consistent(response: PredictionResponse) -> bool:
    if response.status.value != "READY_SCORE":
        return (
            response.decision is None
            and response.engineering_validation_score is None
            and response.anomaly_score is None
            and (response.result_type != "next_pull" or response.threshold is None)
        )
    if response.threshold is None or response.decision is None:
        return False
    if response.result_type == "next_pull":
        score = response.engineering_validation_score
        return (
            score is not None
            and 0 <= score <= 1
            and response.decision is (score >= response.threshold)
        )
    score = response.anomaly_score
    expected = "ANOMALOUS" if score is not None and score > response.threshold else "INLIER"
    return score is not None and str(response.decision) == expected


def _model_threshold_matches_response(model: dict[str, Any], response: PredictionResponse) -> bool:
    if response.status.value == "READY_SCORE":
        return model.get("threshold") == response.threshold
    return response.threshold is None


def _model_schema_consistent(model: dict[str, Any]) -> bool:
    try:
        task = MLTask(str(model["task"]))
        spec = get_model_spec(task)
        schema = _json_object(model.get("input_schema"))
        ordered = schema.get("raw_feature_order")
        keys = schema.get("raw_feature_keys")
        label = _json_object(model.get("label_definition"))
        if ordered != list(spec.feature_keys) or keys != list(spec.feature_keys):
            return False
        if schema.get("feature_set_version") != spec.feature_set_version:
            return False
        if (
            label.get("key") != model.get("label_key")
            or label.get("key") != task.value
            or label.get("version") != model.get("label_version")
            or stable_hash(label) != model.get("label_checksum")
        ):
            return False
        return all(DEFAULT_REGISTRY.resolve(key).unit is not None for key in spec.feature_keys)
    except (KeyError, TypeError, ValueError):
        return False


def _source_configuration_id(feature: dict[str, Any]) -> str | None:
    value = _json_object(feature.get("provenance")).get("configuration_id")
    return str(value) if value is not None else None


def _binding_matches_receipt(
    binding: dict[str, Any], event: dict[str, Any], receipt: dict[str, Any]
) -> bool:
    return (
        binding["id"] == receipt["binding_id"]
        and binding["result_kind"] == receipt["result_kind"]
        and binding["source_role"] == receipt["source_role"]
        and binding["subject_key"] == receipt["subject_key"]
        and binding["artifact_checksum"] == receipt["artifact_checksum"]
        and binding.get("model_version_id") == receipt.get("model_version_id")
        and binding.get("detector_version_id") == receipt.get("detector_version_id")
        and event["id"] == receipt["binding_event_id"]
        and event["binding_id"] == binding["id"]
        and event["event_type"] in {"ACTIVATED", "ROLLED_BACK"}
        and event["created_at"] <= receipt["created_at"]
    )


def _finding_matches_receipt(
    finding: dict[str, Any],
    run: dict[str, Any],
    receipt: dict[str, Any],
    response: PredictionResponse,
) -> bool:
    score = response.anomaly_score
    expected_status = (
        "ANOMALOUS"
        if score is not None and response.threshold is not None and score > response.threshold
        else "INLIER"
    )
    return (
        finding["id"] == receipt.get("anomaly_finding_id")
        and finding["run_id"] == receipt.get("anomaly_run_id")
        and finding["run_id"] == run["id"]
        and finding["detector_version_id"] == receipt["detector_version_id"]
        and finding["feature_set_id"] == receipt.get("feature_set_id")
        and finding["source_hash"] == receipt.get("feature_set_checksum")
        and finding["provenance_hash"] == receipt.get("feature_provenance_checksum")
        and finding["family"] == response.family
        and finding["observation_cutoff"] == response.requested_cutoff
        and finding["score"] == score
        and finding["threshold"] == response.threshold
        and run["detector_version_id"] == finding["detector_version_id"]
        and run["reference_dataset_id"] == finding["reference_dataset_id"]
        and finding["status"] == _finding_status_for_response(response, expected_status)
        and (response.status.value != "READY_SCORE" or str(response.decision) == expected_status)
    )


def _finding_status_for_response(response: PredictionResponse, ready_status: str) -> str:
    if response.status.value == "READY_SCORE":
        return ready_status
    return {
        "ABSTAINED_INSUFFICIENT_SIGNAL": "INSUFFICIENT_SIGNAL",
        "ABSTAINED_LOW_QUALITY": "LOW_QUALITY",
        "ABSTAINED_INSUFFICIENT_REFERENCE": "INSUFFICIENT_REFERENCE",
        "ABSTAINED_INCOMPATIBLE_CONTEXT": "INCOMPATIBLE_CONTEXT",
        "ABSTAINED_UNSUPPORTED_SOURCE": "UNSUPPORTED_SOURCE",
        "ABSTAINED_CUTOFF": "NOT_EVALUABLE",
    }.get(response.status.value, "UNSUPPORTED")


def _finding_reference_matches(
    finding: dict[str, Any], detector: dict[str, Any], reference: dict[str, Any]
) -> bool:
    summary = _json_object(finding.get("reference_summary"))
    nested_summary = _json_object(summary.get("reference_summary"))
    if nested_summary:
        summary = nested_summary
    reference_id = detector.get("reference_id")
    return (
        finding.get("reference_dataset_id") == reference_id
        and reference.get("id") == reference_id
        and summary.get("reference_dataset_id") == str(reference_id)
        and summary.get("reference_checksum") == reference.get("reference_checksum")
        and summary.get("cohort_checksum") == reference.get("cohort_checksum")
        and summary.get("row_count") == reference.get("row_count")
        and summary.get("session_count") == reference.get("session_count")
    )


def _source_role(source_type: str, metadata: dict[str, Any]) -> str:
    declared = metadata.get("data_role")
    if source_type == "synthetic":
        return "synthetic"
    if declared in {"synthetic", "real_vehicle", "imported", "imported_fixture"}:
        return str(declared)
    if source_type in {"csv", "replay"}:
        return "imported_fixture" if metadata.get("fixture") is True else "imported"
    if source_type == "obd":
        return "real_vehicle"
    return "mixed"


def _artifact_state(
    records: dict[SourceKind, SourceRecordSnapshot],
    response: PredictionResponse,
    model_artifacts: Any | None,
    anomaly_artifacts: Any | None,
) -> ArtifactAvailability:
    kind = (
        SourceKind.MODEL_VERSION
        if response.result_type == "next_pull"
        else SourceKind.DETECTOR_VERSION
    )
    record = records.get(kind)
    if record is None:
        return ArtifactAvailability.NOT_APPLICABLE
    expected = record.payload.get("artifact_checksum")
    receipt = records[SourceKind.PREDICTION_RECEIPT].payload
    if expected is None:
        return ArtifactAvailability.UNAVAILABLE
    if expected != receipt.get("artifact_checksum"):
        return ArtifactAvailability.CHECKSUM_MISMATCH
    store = model_artifacts if response.result_type == "next_pull" else anomaly_artifacts
    if store is None:
        return ArtifactAvailability.UNAVAILABLE
    payload = record.payload
    try:
        if response.result_type == "next_pull":
            relative = Path(str(payload["task"])) / f"model-{payload['version']}.joblib"
        else:
            relative = (
                Path(str(payload["family"]))
                / str(payload["method"])
                / f"detector-{payload['version']}.joblib"
            )
        if Path(str(payload.get("artifact_path"))) != relative:
            return ArtifactAvailability.CHECKSUM_MISMATCH
        target = store._checked_path(relative)
        if target.is_symlink() or not target.is_file() or target.stat().st_size > 50 * 1024 * 1024:
            return ArtifactAvailability.UNAVAILABLE
        digest = hashlib.sha256()
        with target.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
        return (
            ArtifactAvailability.VERIFIED
            if digest.hexdigest() == expected
            else ArtifactAvailability.CHECKSUM_MISMATCH
        )
    except (OSError, KeyError, ValueError, TypeError):
        return ArtifactAvailability.UNAVAILABLE
