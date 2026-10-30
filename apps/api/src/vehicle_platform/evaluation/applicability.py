from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from vehicle_platform.evaluation.contracts import (
    AllowedClaimCategory,
    ApplicabilityAssessment,
    ApplicabilityStatus,
    SourceRole,
)
from vehicle_platform.features.domain import stable_hash


def assess_source_applicability(
    *,
    subject_kind: str,
    subject_key: str,
    subject_version: str,
    source_role: SourceRole,
    source_fingerprint: str,
    evaluation_rows: int,
    labeled_outcomes: int,
    required_signals: Sequence[str],
    observed_signals: Sequence[str],
    same_configuration_history: bool,
    calibration_available: bool,
    out_of_domain: bool = False,
) -> ApplicabilityAssessment:
    reasons: tuple[str, ...]
    claims: tuple[AllowedClaimCategory, ...]
    unlabeled_external_source = (
        source_role in {SourceRole.REAL_VEHICLE, SourceRole.IMPORTED} and labeled_outcomes == 0
    )
    eligible_calibration = (
        calibration_available and source_role is SourceRole.SYNTHETIC and labeled_outcomes > 0
    )
    if unlabeled_external_source:
        status = ApplicabilityStatus.REAL_DATA_UNLABELED
        reasons = ("REAL_LABELS_NOT_AVAILABLE", "DISTRIBUTION_ONLY")
        claims = (
            AllowedClaimCategory.UNLABELED_DISTRIBUTION_METRIC,
            AllowedClaimCategory.SCIENTIFIC_LIMITATION,
        )
    elif out_of_domain:
        status = ApplicabilityStatus.OOD_WARNING
        reasons = ("OUT_OF_TRAIN_REFERENCE", "CALIBRATION_NOT_TRANSFERABLE")
        claims = (
            AllowedClaimCategory.SYNTHETIC_FIXTURE_METRIC,
            AllowedClaimCategory.SCIENTIFIC_LIMITATION,
        )
    elif subject_kind == "9C_FAMILY" and not same_configuration_history:
        status = ApplicabilityStatus.NO_REFERENCE
        reasons = ("SAME_CONFIGURATION_REFERENCE_REQUIRED", "CROSS_VEHICLE_FALLBACK_PROHIBITED")
        claims = (AllowedClaimCategory.SCIENTIFIC_LIMITATION,)
    elif evaluation_rows < 10 or labeled_outcomes < 10:
        status = ApplicabilityStatus.EVALUATION_INSUFFICIENT
        reasons = ("INDEPENDENT_SUPPORT_BELOW_PROTOCOL_FLOOR",)
        claims = (AllowedClaimCategory.SCIENTIFIC_LIMITATION,)
    elif eligible_calibration:
        status = ApplicabilityStatus.SYNTHETIC_ONLY
        reasons = ("CALIBRATION_CONDITIONAL_ON_SYNTHETIC_POPULATION",)
        claims = (
            AllowedClaimCategory.SYNTHETIC_FIXTURE_METRIC,
            AllowedClaimCategory.UNCALIBRATED_SCORE,
        )
    else:
        status = ApplicabilityStatus.NOT_CALIBRATED
        reasons = ("NO_ELIGIBLE_CALIBRATION_EVIDENCE",)
        claims = (
            AllowedClaimCategory.UNCALIBRATED_SCORE,
            AllowedClaimCategory.SCIENTIFIC_LIMITATION,
        )
    observed = set(observed_signals)
    required = tuple(sorted(set(required_signals)))
    if evaluation_rows > 0 and not set(required).issubset(observed):
        if not unlabeled_external_source:
            status = ApplicabilityStatus.INCOMPATIBLE
        reasons = (*reasons, "REQUIRED_SIGNAL_UNAVAILABLE")
        claims = tuple(dict.fromkeys((*claims, AllowedClaimCategory.MEASURED_SOURCE_COVERAGE)))
    elif evaluation_rows == 0 and not set(required).issubset(observed):
        reasons = (*reasons, "SOURCE_SIGNAL_AVAILABILITY_NOT_OBSERVED")
    elif not required:
        reasons = (*reasons, "NO_REQUIRED_SIGNAL_CONTRACT")
    return ApplicabilityAssessment(
        subject_kind=subject_kind,
        subject_key=subject_key,
        subject_version=subject_version,
        source_role=source_role,
        status=status,
        reason_codes=tuple(dict.fromkeys(reasons)),
        required_signals=required,
        observed_signal_count=len(observed),
        required_signal_count=len(required),
        labeled_outcomes=labeled_outcomes,
        evaluation_rows=evaluation_rows,
        operational_scope=(
            "offline engineering evaluation only; no serving, diagnosis or maintenance decision"
        ),
        allowed_claims=claims,
        source_fingerprint=source_fingerprint,
        calibration_available=eligible_calibration,
        diagnostic_claim_allowed=False,
    )


def source_fingerprint(source_role: SourceRole, identities: Sequence[str], manifest: Any) -> str:
    return stable_hash(
        {
            "source_role": source_role.value,
            "entity_fingerprints": sorted(stable_hash(item) for item in identities),
            "manifest": manifest,
        }
    )
