import math
import re
from typing import Any, Literal, cast
from uuid import UUID

from vehicle_platform.acquisition.service import AcquisitionService
from vehicle_platform.analysis.service import SessionAnalysisService
from vehicle_platform.analytics.domain import AnalyticsConfig
from vehicle_platform.analytics.service import AnalyticsService
from vehicle_platform.anomalies.artifacts import ArtifactStore as AnomalyArtifactStore
from vehicle_platform.api.domain_contracts import AnalyticsResultResponse
from vehicle_platform.core.config import Settings
from vehicle_platform.events.service import EventAnalysisService
from vehicle_platform.features.registry import DEFAULT_REGISTRY
from vehicle_platform.infrastructure.database import Database
from vehicle_platform.mcp.catalog import Catalog, Entity
from vehicle_platform.mcp.errors import ErrorCode, PlatformError
from vehicle_platform.mcp.schemas import (
    Envelope,
    PredictionEvidenceFact,
    PredictionEvidenceMCPProjection,
    Warning,
    Window,
)
from vehicle_platform.ml.artifacts import ArtifactStore as ModelArtifactStore
from vehicle_platform.observability.telemetry import Telemetry
from vehicle_platform.prediction_evidence.domain import (
    EvidenceFactType,
    SourceKind,
)
from vehicle_platform.prediction_evidence.service import PredictionEvidenceService
from vehicle_platform.predictions.domain import PredictionError
from vehicle_platform.telemetry.domain import SIGNALS
from vehicle_platform.telemetry.service import QueryService


class Adapter:
    def __init__(self, database: Database, settings: Settings, telemetry: Telemetry) -> None:
        self.settings = settings
        self.database = database
        self.catalog = Catalog(database)
        self.analysis = SessionAnalysisService(database, telemetry)
        self.events = EventAnalysisService(database, telemetry)
        self.analytics = AnalyticsService(database, telemetry, read_only=True)
        self.acquisition = AcquisitionService(database, settings, telemetry)
        self.telemetry = QueryService(database, telemetry)
        self.config = AnalyticsConfig()
        self.prediction_evidence = (
            PredictionEvidenceService(
                database,
                model_artifacts=ModelArtifactStore(),
                anomaly_artifacts=AnomalyArtifactStore(),
                telemetry=telemetry,
                timeout_seconds=min(settings.prediction_request_timeout_seconds, 6.0),
            )
            if settings.prediction_service_enabled
            else None
        )

    async def prediction_evidence_summary(
        self,
        vehicle_id: UUID,
        evidence_id: UUID,
        session_id: UUID | None = None,
        pull_id: UUID | None = None,
    ) -> PredictionEvidenceMCPProjection:
        reader = self.prediction_evidence
        if (
            reader is None
            or not self.settings.prediction_service_enabled
            or self.settings.environment not in {"development", "test"}
        ):
            raise PlatformError(ErrorCode.UNSUPPORTED_CAPABILITY)
        try:
            verified = await reader.read_verified(evidence_id, vehicle_id=vehicle_id)
            original_pull_id = UUID(str(verified.source.receipt.payload["pull_id"]))
            pull = await self.analysis.pull(original_pull_id)
        except PredictionError as exc:
            if exc.status_code == 404:
                raise PlatformError(ErrorCode.NOT_FOUND) from None
            if exc.status_code == 503:
                raise PlatformError(ErrorCode.BACKEND_UNAVAILABLE) from None
            if exc.code.endswith("SCHEMA_UNSUPPORTED"):
                raise PlatformError(ErrorCode.UNSUPPORTED_CAPABILITY) from None
            raise PlatformError(ErrorCode.FORBIDDEN) from None
        except Exception as exc:
            # Preserve only the fixed platform error vocabulary at the MCP boundary.
            if isinstance(exc, PlatformError):
                raise
            raise PlatformError(ErrorCode.NOT_FOUND) from None
        if verified.integrity.value not in {
            "VERIFIED",
            "VERIFIED_SNAPSHOT_ARTIFACT_UNAVAILABLE",
        }:
            raise PlatformError(ErrorCode.EVIDENCE_NOT_VERIFIED)
        if (
            pull is None
            or pull.vehicle_id != vehicle_id
            or (pull_id is not None and pull_id != pull.id)
            or (session_id is not None and session_id != pull.session_id)
        ):
            raise PlatformError(ErrorCode.NOT_FOUND)
        feature = verified.source.records.get(SourceKind.FEATURE_SET)
        if feature is not None:
            payload = feature.payload
            if (
                str(payload.get("vehicle_id")) != str(vehicle_id)
                or str(payload.get("pull_vehicle_id")) != str(vehicle_id)
                or str(payload.get("session_vehicle_id")) != str(vehicle_id)
                or str(payload.get("pull_id")) != str(pull.id)
                or str(payload.get("session_id")) != str(pull.session_id)
                or str(payload.get("pull_configuration_id")) != str(pull.configuration_id)
            ):
                raise PlatformError(ErrorCode.NOT_FOUND)
        elif verified.bundle.prediction.status == "READY_SCORE":
            raise PlatformError(ErrorCode.NOT_FOUND)

        bundle, source = verified.bundle, verified.source
        summary = bundle.source_summary
        model = source.records.get(SourceKind.MODEL_VERSION)
        detector = source.records.get(SourceKind.DETECTOR_VERSION)
        safe_facts: list[PredictionEvidenceFact] = []
        allowed_types = {
            EvidenceFactType.SOURCE_MEASUREMENT,
            EvidenceFactType.COMPUTED_FEATURE,
            EvidenceFactType.QUALITY_INDICATOR,
        }
        for fact in bundle.facts:
            if (
                fact.fact_type not in allowed_types
                or not fact.cutoff_eligible
                or fact.cutoff > bundle.effective_cutoff
            ):
                continue
            try:
                DEFAULT_REGISTRY.resolve(fact.key)
            except KeyError:
                continue
            if not (fact.value is None or type(fact.value) in {str, bool, int, float}):
                continue
            if isinstance(fact.value, float) and not math.isfinite(fact.value):
                continue
            if isinstance(fact.value, str) and (
                len(fact.value) > 160
                or not fact.value.isascii()
                or not fact.value.isprintable()
                or any(character in "<>" for character in fact.value)
            ):
                continue
            safe_facts.append(
                PredictionEvidenceFact(
                    key=fact.key,
                    fact_type=cast(
                        Literal[
                            "SOURCE_MEASUREMENT",
                            "COMPUTED_FEATURE",
                            "QUALITY_INDICATOR",
                        ],
                        fact.fact_type.value,
                    ),
                    value=fact.value,
                    unit=fact.unit,
                    quality=fact.quality,
                    cutoff=fact.cutoff,
                    observed_at=fact.observed_at,
                    available_at=fact.available_at,
                )
            )
            if len(safe_facts) == 32:
                break

        eligible_integrity = verified.integrity.value in {
            "VERIFIED",
            "VERIFIED_SNAPSHOT_ARTIFACT_UNAVAILABLE",
        }
        available_signal_keys = {signal.key for signal in SIGNALS}
        return PredictionEvidenceMCPProjection(
            schema_version="prediction-agent-summary-v1",
            evidence_id=bundle.evidence_id,
            receipt_id=bundle.receipt_id,
            source_vehicle_id=pull.vehicle_id,
            source_session_id=pull.session_id,
            source_pull_id=pull.id,
            source_configuration_id=pull.configuration_id,
            source_feature_set_id=feature.entity_id if feature is not None else None,
            result_type=bundle.result_type,
            horizon=bundle.horizon,
            task=bundle.task,
            family=bundle.family,
            source_role=bundle.source_role,
            requested_cutoff=bundle.requested_cutoff,
            effective_cutoff=bundle.effective_cutoff,
            status=bundle.prediction.status,
            reason_code=bundle.prediction.reason_code,
            model_version=self._text(model.payload.get("version")) if model else None,
            model_algorithm=self._text(model.payload.get("algorithm")) if model else None,
            detector_version=self._text(detector.payload.get("version")) if detector else None,
            detector_algorithm_version=(
                self._text(detector.payload.get("algorithm_version")) if detector else None
            ),
            detector_method=self._text(detector.payload.get("method")) if detector else None,
            decision=bundle.prediction.decision if eligible_integrity else None,
            score=bundle.prediction.score if eligible_integrity else None,
            threshold=bundle.prediction.threshold if eligible_integrity else None,
            completeness=bundle.completeness,
            integrity=verified.integrity,
            verification_reasons=list(verified.reason_codes),
            quality_class=summary.quality_class,
            coverage=summary.receipt_coverage,
            feature_coverage=summary.feature_coverage,
            observed_feature_count=summary.observed_feature_count,
            expected_feature_count=summary.expected_feature_count,
            source_type=summary.source_type,
            missing_reason_counts=summary.missing_reason_counts,
            available_signals=[
                signal for signal in summary.available_signals if signal in available_signal_keys
            ],
            invalid_observation_count=summary.invalid_observation_count,
            duplicate_timestamp_count=summary.duplicate_timestamp_count,
            pull_completeness=summary.pull_completeness,
            artifact_availability=source.artifact_availability,
            reference_row_count=summary.reference_row_count,
            reference_session_count=summary.reference_session_count,
            facts=safe_facts,
            gaps=[gap.code.value for gap in bundle.gaps],
            omitted_count=bundle.omitted_count + max(0, len(bundle.facts) - len(safe_facts)),
        )

    @staticmethod
    def _text(value: Any) -> str | None:
        if isinstance(value, str) and re.fullmatch(r"[A-Za-z0-9_.-]{1,80}", value) is not None:
            return value
        return None

    async def entity(self, kind: Entity, identifier: UUID, vehicle_id: UUID) -> dict[str, Any]:
        data = await self.catalog.get(kind, identifier)
        actual = data["id"] if kind == "vehicle" else data["vehicle_id"]
        if str(actual) != str(vehicle_id):
            raise PlatformError(ErrorCode.INCOMPATIBLE_CONTEXT)
        return data

    async def pull(self, vehicle_id: UUID, pull_id: UUID) -> dict[str, Any]:
        data = await self.analysis.pull(pull_id)
        if data is None:
            raise PlatformError(ErrorCode.NOT_FOUND)
        if data.vehicle_id != vehicle_id:
            raise PlatformError(ErrorCode.INCOMPATIBLE_CONTEXT)
        return data.model_dump(mode="json")

    async def selected_pulls(
        self, vehicle_id: UUID, ids: list[UUID], *, same_configuration: bool = True
    ) -> list[dict[str, Any]]:
        if len(set(ids)) != len(ids) or not 1 <= len(ids) <= 20:
            raise PlatformError(ErrorCode.INVALID_ARGUMENT)
        pulls = [await self.pull(vehicle_id, item) for item in ids]
        if same_configuration and len({p["configuration_id"] for p in pulls}) != 1:
            raise PlatformError(ErrorCode.INCOMPATIBLE_CONTEXT)
        return pulls

    def envelope(
        self,
        data: dict[str, Any] | list[dict[str, Any]],
        context: dict[str, UUID | list[UUID] | None],
        *,
        limit: int | None = None,
    ) -> Envelope:
        truncated = isinstance(data, list) and limit is not None and len(data) > limit
        if isinstance(data, list) and limit is not None:
            data = data[:limit]
        return Envelope(
            data=data,
            context=context,
            provenance={"source": "canonical-platform-records", "snapshot": True},
            truncated=truncated,
            returned=len(data) if isinstance(data, list) else 1,
            warnings=[Warning(code="truncated_result")] if truncated else [],
        )

    async def analytical(
        self, result: AnalyticsResultResponse, context: dict[str, UUID | list[UUID] | None]
    ) -> Envelope:
        data = result.model_dump(mode="json")
        data["calculation_id"] = data.pop("id")
        response = self.envelope(data, context)
        response.provenance.update(
            {
                "analysis_run_id": None,
                "persistence": "transient",
                "source_fingerprint": result.source_fingerprint,
                "algorithm_version": result.algorithm_version,
                "configuration_hash": result.configuration_hash,
            }
        )
        if result.analytics_type in {"session", "vehicle_baseline", "trend", "cross_session"}:
            session_id = context.get("session_id")
            session_ids = context.get("session_ids")
            truncated = await self.catalog.history_truncated(
                result.vehicle_id,
                result.configuration_id if result.analytics_type == "vehicle_baseline" else None,
                session_id if isinstance(session_id, UUID) else None,
                session_ids if isinstance(session_ids, list) else None,
            )
            response.truncated = truncated
            response.provenance["maximum_selected_pulls"] = 20
            if truncated:
                response.warnings.append(Warning(code="truncated_result"))
        response.warnings.extend(Warning(code=code) for code in result.warnings)
        if result.status == "insufficient":
            response.warnings.append(Warning(code="insufficient_history"))
        return response

    async def window(
        self, vehicle_id: UUID, session_id: UUID, signals: list[str], window: Window, limit: int
    ) -> Envelope:
        session = await self.entity("session", session_id, vehicle_id)
        if len(set(signals)) != len(signals):
            raise PlatformError(ErrorCode.INVALID_ARGUMENT)
        if any(signal not in {item.key for item in SIGNALS} for signal in signals):
            raise PlatformError(ErrorCode.UNSUPPORTED_CAPABILITY)
        result = await self.telemetry.query(session_id, signals, window.start, window.end, limit)
        response = self.envelope(
            result.model_dump(mode="json"),
            {
                "vehicle_id": vehicle_id,
                "session_id": session_id,
                "configuration_id": UUID(session["configuration_id"])
                if session["configuration_id"]
                else None,
            },
        )
        response.truncated = result.truncated
        response.returned = result.returned
        if result.truncated:
            response.warnings.append(Warning(code="truncated_result"))
        missing = sorted(set(signals) - {p.signal for p in result.points})
        if missing:
            response.warnings.append(
                Warning(
                    code="partial_window", details={"signals_without_returned_samples": missing}
                )
                if result.truncated
                else Warning(code="missing_signal", details={"signals": missing})
            )
        response.provenance.update(
            {"source": "canonical-telemetry", "requested_window": window.model_dump(mode="json")}
        )
        return response
