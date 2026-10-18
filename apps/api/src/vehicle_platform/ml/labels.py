from __future__ import annotations

from collections import Counter, defaultdict
from collections.abc import Mapping
from datetime import datetime
from typing import Any

from vehicle_platform.features.datasets import DatasetBuild, DatasetCandidate
from vehicle_platform.features.domain import (
    HorizonKind,
    LabelDefinition,
    PredictionHorizon,
    stable_hash,
)
from vehicle_platform.features.registry import DEFAULT_REGISTRY
from vehicle_platform.ml.domain import (
    CandidateFamily,
    CandidateSpec,
    LabelExclusionReason,
    MLTask,
    ModelSpec,
    SupervisedDataset,
    SupervisedRow,
)

FEATURE_SET_VERSION = "phase9a-pull-v2"
LABEL_QUALITY_MINIMUM = 0.75
MINIMUM_PRIOR_FUEL_PULLS = 2

_COMMON_NOISE_CONTROL = "quality.duplicate_timestamp_count"


def model_specs() -> tuple[ModelSpec, ...]:
    candidates = (
        CandidateSpec(CandidateFamily.DUMMY, {"strategy": "prior"}, 0),
        CandidateSpec(
            CandidateFamily.LOGISTIC_REGRESSION,
            {"C": 0.5, "max_iter": 500, "class_weight": "balanced", "solver": "liblinear"},
            1,
        ),
        CandidateSpec(
            CandidateFamily.RANDOM_FOREST,
            {
                "n_estimators": 64,
                "max_depth": 4,
                "min_samples_leaf": 4,
                "class_weight": "balanced_subsample",
                "n_jobs": 1,
            },
            2,
        ),
    )
    return (
        ModelSpec(
            task=MLTask.THERMAL_DEGRADATION,
            version="1.0.0",
            label_definition=LabelDefinition(
                key=MLTask.THERMAL_DEGRADATION.value,
                version="1.0.0",
                name="Next pull thermal degradation",
                description=(
                    "Whether the next compatible pull starts materially hotter than the current "
                    "pull, measured as a relative within-vehicle/configuration temperature change."
                ),
                dtype="boolean",
                task_type="classification",
                horizon=PredictionHorizon(HorizonKind.NEXT_PULL),
                source_outcome=(
                    "next compatible pull IAT start compared with current pull IAT start"
                ),
                algorithm_id="vehicle-platform.label.next-pull-thermal-progression",
                algorithm_version="1.0.0",
                required_signals=("engine.intake_air_temperature",),
                source_feature_keys=("thermal.iat_start",),
                quality_policy={
                    "minimum_pull_completeness": LABEL_QUALITY_MINIMUM,
                    "required_feature_quality": "valid",
                    "missing_outcome_is_excluded": True,
                },
                compatibility_policy={
                    "same_vehicle": True,
                    "same_configuration": True,
                    "same_active_modifications": True,
                    "same_session_sequence": True,
                    "skip_ineligible_next_pull": False,
                },
                threshold_policy={
                    "positive_when_delta_k_at_least": 3.0,
                    "rationale": "relative measurable progression; not an OEM operating limit",
                },
                provenance_policy={
                    "retain_input_and_target_pull_ids": True,
                    "retain_feature_set_ids_and_source_hashes": True,
                    "retain_source_values_and_quality": True,
                },
            ),
            feature_set_version=FEATURE_SET_VERSION,
            input_dataset_name="phase9b_thermal_inputs",
            outcome_dataset_name="phase9b_thermal_outcomes",
            feature_keys=(
                "thermal.iat_delta_k",
                "thermal.iat_slope_k_per_s",
                "thermal.pre_pull_iat_k",
                "thermal.iat_recovery_delta_k",
                "boost_air.pressure_stddev_pa",
                "performance.rpm_2500_3500_s_per_1000rpm",
                _COMMON_NOISE_CONTROL,
            ),
            outcome_feature_keys=("thermal.iat_start",),
            candidates=candidates,
        ),
        ModelSpec(
            task=MLTask.PERFORMANCE_DEGRADATION,
            version="1.0.0",
            label_definition=LabelDefinition(
                key=MLTask.PERFORMANCE_DEGRADATION.value,
                version="1.0.0",
                name="Next pull performance degradation",
                description=(
                    "Whether the next compatible pull takes materially longer through the "
                    "validated 3500–4500 RPM interval than the current pull."
                ),
                dtype="boolean",
                task_type="classification",
                horizon=PredictionHorizon(HorizonKind.NEXT_PULL),
                source_outcome="Phase 5 normalized 3500–4500 RPM interval time",
                algorithm_id="vehicle-platform.label.next-pull-rpm-interval-degradation",
                algorithm_version="1.0.0",
                required_signals=("engine.rpm",),
                source_feature_keys=("performance.rpm_3500_4500_s_per_1000rpm",),
                quality_policy={
                    "minimum_pull_completeness": LABEL_QUALITY_MINIMUM,
                    "required_feature_quality": "valid",
                    "missing_outcome_is_excluded": True,
                },
                compatibility_policy={
                    "same_vehicle": True,
                    "same_configuration": True,
                    "same_active_modifications": True,
                    "same_session_sequence": True,
                    "skip_ineligible_next_pull": False,
                },
                threshold_policy={
                    "positive_when_relative_interval_increase_at_least": 0.08,
                    "rationale": "relative measured interval change; no horsepower estimate",
                },
                provenance_policy={
                    "retain_input_and_target_pull_ids": True,
                    "retain_feature_set_ids_and_source_hashes": True,
                    "retain_source_values_and_quality": True,
                },
            ),
            feature_set_version=FEATURE_SET_VERSION,
            input_dataset_name="phase9b_performance_inputs",
            outcome_dataset_name="phase9b_performance_outcomes",
            feature_keys=(
                "performance.rpm_2500_3500_s_per_1000rpm",
                "performance.rpm_4500_5500_s_per_1000rpm",
                "history.prior_performance_mean_s",
                "history.prior_performance_variance_s2",
                # This is an eligible current-pull timing input for performance; it is not
                # the irrelevant negative control because it shares the measured RPM timing.
                "quality.sample_interval_stddev_s",
                "boost_air.pressure_max",
                "boost_air.pressure_stddev_pa",
                "thermal.iat_start",
                "thermal.iat_delta_k",
                _COMMON_NOISE_CONTROL,
            ),
            outcome_feature_keys=("performance.rpm_3500_4500_s_per_1000rpm",),
            candidates=candidates,
        ),
        ModelSpec(
            task=MLTask.FUEL_DEVIATION,
            version="1.0.0",
            label_definition=LabelDefinition(
                key=MLTask.FUEL_DEVIATION.value,
                version="1.0.0",
                name="Next pull fuel pressure deviation",
                description=(
                    "Whether the next compatible pull's measured minimum high-pressure fuel value "
                    "is materially below its compatible recorded history."
                ),
                dtype="boolean",
                task_type="classification",
                horizon=PredictionHorizon(HorizonKind.NEXT_PULL),
                source_outcome=(
                    "measured next-pull minimum rail pressure vs compatible history mean"
                ),
                algorithm_id="vehicle-platform.label.next-pull-fuel-relative-deviation",
                algorithm_version="1.0.0",
                required_signals=("fuel.high_pressure",),
                source_feature_keys=(
                    "fuel.rail_pressure_min",
                    "history.prior_fuel_mean_pa",
                    "temporal_context.prior_pull_count",
                ),
                quality_policy={
                    "minimum_pull_completeness": LABEL_QUALITY_MINIMUM,
                    "required_feature_quality": "valid",
                    "minimum_compatible_prior_pulls": MINIMUM_PRIOR_FUEL_PULLS,
                    "missing_outcome_is_excluded": True,
                },
                compatibility_policy={
                    "same_vehicle": True,
                    "same_configuration": True,
                    "same_active_modifications": True,
                    "same_session_sequence": True,
                    "skip_ineligible_next_pull": False,
                },
                threshold_policy={
                    "positive_when_min_pressure_ratio_at_most": 0.88,
                    "rationale": (
                        "relative to recorded compatible history; no universal pressure limit"
                    ),
                },
                provenance_policy={
                    "retain_input_and_target_pull_ids": True,
                    "retain_feature_set_ids_and_source_hashes": True,
                    "retain_source_values_and_quality": True,
                },
            ),
            feature_set_version=FEATURE_SET_VERSION,
            input_dataset_name="phase9b_fuel_inputs",
            outcome_dataset_name="phase9b_fuel_outcomes",
            feature_keys=(
                "fuel.rail_pressure_mean",
                "fuel.rail_pressure_delta_pa",
                "fuel.rail_pressure_stddev_pa",
                "fuel.rail_pressure_drop_rate_pa_per_s",
                "boost_air.pressure_max",
                "boost_air.pressure_stddev_pa",
                "performance.rpm_2500_3500_s_per_1000rpm",
                _COMMON_NOISE_CONTROL,
            ),
            outcome_feature_keys=(
                "fuel.rail_pressure_min",
                "history.prior_fuel_mean_pa",
                "temporal_context.prior_pull_count",
            ),
            candidates=candidates,
        ),
    )


def get_model_spec(task: MLTask | str) -> ModelSpec:
    parsed = task if isinstance(task, MLTask) else MLTask(task)
    for spec in model_specs():
        if spec.task is parsed:
            return spec
    raise KeyError(f"unknown predictive task: {parsed}")


class SupervisedDatasetError(ValueError):
    pass


def validate_model_features(spec: ModelSpec) -> None:
    if set(spec.feature_keys).intersection(spec.label_definition.source_feature_keys):
        raise SupervisedDatasetError("target outcome feature is selected as an input")
    for key in spec.feature_keys:
        if key in {
            "vehicle.id",
            "configuration.id",
            "session.id",
            "pull.id",
            "target.id",
            "timestamp",
        } or key.endswith((".vehicle_id", ".configuration_id", ".session_id", ".pull_id")):
            raise SupervisedDatasetError(f"identity feature is forbidden: {key}")
        if key.startswith("future.") or ".future_" in key:
            raise SupervisedDatasetError(f"future-only feature is forbidden: {key}")
        try:
            definition = DEFAULT_REGISTRY.resolve(key)
        except KeyError as error:
            raise SupervisedDatasetError(f"unregistered model feature: {key}") from error
        if definition.dtype.value not in {"float", "integer"}:
            raise SupervisedDatasetError(
                f"unsupported categorical or identity input feature: {key}"
            )
        if any(tag in {"target-derived", "entity-id", "future-only"} for tag in definition.tags):
            raise SupervisedDatasetError(f"forbidden target or identity feature: {key}")


def pair_compatibility_reason(
    current: DatasetCandidate, target: DatasetCandidate
) -> LabelExclusionReason | None:
    if current.vehicle_id != target.vehicle_id:
        return LabelExclusionReason.CONFIGURATION_BOUNDARY
    if current.session_id != target.session_id:
        return LabelExclusionReason.INCOMPATIBLE_SESSION
    if (
        current.configuration_id is None
        or target.configuration_id is None
        or current.configuration_id != target.configuration_id
    ):
        return LabelExclusionReason.CONFIGURATION_BOUNDARY
    if current.active_modification_ids != target.active_modification_ids:
        return LabelExclusionReason.CONFIGURATION_BOUNDARY
    current_end = datetime.fromisoformat(current.ended_at)
    target_start = datetime.fromisoformat(target.started_at)
    if current_end >= target_start:
        return LabelExclusionReason.FUTURE_DATA
    return None


def build_supervised_dataset(
    input_dataset: DatasetBuild,
    outcome_dataset: DatasetBuild,
    spec: ModelSpec,
    *,
    repository_sha: str,
    scenario_family_by_session: Mapping[str, str] | None = None,
) -> SupervisedDataset:
    validate_model_features(spec)
    if input_dataset.definition.feature_set_version != spec.feature_set_version:
        raise SupervisedDatasetError("input dataset FeatureSetVersion is incompatible")
    if outcome_dataset.definition.feature_set_version != spec.feature_set_version:
        raise SupervisedDatasetError("outcome dataset FeatureSetVersion is incompatible")
    if tuple(input_dataset.definition.selected_features) != spec.feature_keys:
        raise SupervisedDatasetError(
            "input DatasetDefinition does not match ModelSpec feature order"
        )
    if not set(spec.outcome_feature_keys).issubset(outcome_dataset.definition.selected_features):
        raise SupervisedDatasetError("outcome DatasetDefinition is missing label source features")
    if input_dataset.definition.source != outcome_dataset.definition.source:
        raise SupervisedDatasetError("input and outcome dataset source roles differ")
    if input_dataset.definition.observation_cutoff != outcome_dataset.definition.observation_cutoff:
        raise SupervisedDatasetError("input and outcome datasets must share an observation cutoff")
    source_role = input_dataset.definition.source
    scenario_family_by_session = scenario_family_by_session or {}

    outcome_by_pull = {row["pull_id"]: row for row in outcome_dataset.rows}
    candidates_by_session: dict[tuple[str, str], list[DatasetCandidate]] = defaultdict(list)
    candidate_by_pull: dict[str, DatasetCandidate] = {}
    for candidate in outcome_dataset.candidates:
        candidates_by_session[(candidate.vehicle_id, candidate.session_id)].append(candidate)
        candidate_by_pull[candidate.pull_id] = candidate
    for items in candidates_by_session.values():
        items.sort(key=lambda item: (item.started_at, item.pull_id))

    exclusion_by_pull = {item.pull_id: item.exclusion_reason for item in outcome_dataset.candidates}
    exclusions: list[dict[str, Any]] = []
    rows: list[SupervisedRow] = []

    def reject(
        input_pull_id: str, target_pull_id: str | None, reason: LabelExclusionReason
    ) -> None:
        exclusions.append(
            {
                "input_pull_id": input_pull_id,
                "target_pull_id": target_pull_id,
                "reason": reason.value,
            }
        )

    for input_row in input_dataset.rows:
        input_pull_id = str(input_row["pull_id"])
        current = candidate_by_pull.get(input_pull_id)
        if current is None:
            reject(input_pull_id, None, LabelExclusionReason.NO_COMPATIBLE_PRIOR)
            continue
        sequence = candidates_by_session[(current.vehicle_id, current.session_id)]
        position = next(
            (
                index
                for index, candidate in enumerate(sequence)
                if candidate.pull_id == input_pull_id
            ),
            None,
        )
        if position is None:
            reject(input_pull_id, None, LabelExclusionReason.NO_COMPATIBLE_PRIOR)
            continue
        if position + 1 >= len(sequence):
            reject(input_pull_id, None, LabelExclusionReason.NO_COMPATIBLE_NEXT_PULL)
            continue
        target = sequence[position + 1]
        reason = pair_compatibility_reason(current, target)
        if reason is not None:
            reject(input_pull_id, target.pull_id, reason)
            continue
        # The current pull itself is the label baseline; it must have eligible outcome data.
        prior_outcome = outcome_by_pull.get(input_pull_id)
        if prior_outcome is None:
            exclusion_reason = exclusion_by_pull.get(input_pull_id)
            reason = (
                LabelExclusionReason.INSUFFICIENT_OUTCOME_QUALITY
                if exclusion_reason == "minimum_quality_not_met"
                else LabelExclusionReason.MISSING_OUTCOME_SIGNAL
                if exclusion_reason and exclusion_reason.startswith("required_feature_unavailable:")
                else LabelExclusionReason.NO_COMPATIBLE_PRIOR
            )
            reject(input_pull_id, target.pull_id, reason)
            continue
        target_outcome = outcome_by_pull.get(target.pull_id)
        if target_outcome is None:
            exclusion_reason = exclusion_by_pull.get(target.pull_id)
            reason = (
                LabelExclusionReason.INSUFFICIENT_OUTCOME_QUALITY
                if exclusion_reason == "minimum_quality_not_met"
                else LabelExclusionReason.MISSING_OUTCOME_SIGNAL
                if exclusion_reason == "feature_set_missing_or_after_cutoff"
                or (
                    exclusion_reason is not None
                    and exclusion_reason.startswith("required_feature_unavailable:")
                )
                else LabelExclusionReason.INSUFFICIENT_OUTCOME_QUALITY
            )
            reject(input_pull_id, target.pull_id, reason)
            continue
        input_cutoff = datetime.fromisoformat(str(input_row["observation_cutoff"]))
        target_start = datetime.fromisoformat(target.started_at)
        if input_cutoff >= target_start:
            reject(input_pull_id, target.pull_id, LabelExclusionReason.FUTURE_DATA)
            continue
        if float(target_outcome["quality"].get("pull_completeness") or 0.0) < float(
            spec.label_definition.quality_policy.get(
                "minimum_pull_completeness", LABEL_QUALITY_MINIMUM
            )
        ):
            reject(input_pull_id, target.pull_id, LabelExclusionReason.INSUFFICIENT_OUTCOME_QUALITY)
            continue
        value, provenance, reason = _make_target(prior_outcome, target_outcome, spec)
        if reason is not None:
            reject(input_pull_id, target.pull_id, reason)
            continue
        if value is None:
            reject(input_pull_id, target.pull_id, LabelExclusionReason.LABEL_NOT_APPLICABLE)
            continue
        x, missing, feature_quality = _input_vector(input_row, spec)
        row_id = stable_hash(
            {
                "task": spec.task.value,
                "label_checksum": spec.label_definition.checksum,
                "input_row_id": input_row["row_id"],
                "target_row_id": target_outcome["row_id"],
                "input_source_hash": input_row["feature_set_source_hash"],
                "target_source_hash": target_outcome["feature_set_source_hash"],
            }
        )
        current_start = datetime.fromisoformat(str(input_row["started_at"]))
        quality_class = (
            "high_quality"
            if float(input_row["quality"].get("pull_completeness") or 0.0) >= 0.9
            and float(target_outcome["quality"].get("pull_completeness") or 0.0) >= 0.9
            else "degraded_but_eligible"
        )
        rows.append(
            SupervisedRow(
                row_id=row_id,
                group_id=current.session_id,
                vehicle_id=current.vehicle_id,
                configuration_id=current.configuration_id or "unknown",
                session_id=current.session_id,
                input_pull_id=input_pull_id,
                target_pull_id=target.pull_id,
                input_started_at=current_start,
                input_available_at=input_cutoff,
                target_started_at=target_start,
                input_feature_set_id=str(input_row["feature_set_id"]),
                target_feature_set_id=str(target_outcome["feature_set_id"]),
                input_source_hash=str(input_row["feature_set_source_hash"]),
                target_source_hash=str(target_outcome["feature_set_source_hash"]),
                features=x,
                missing=missing,
                feature_quality=feature_quality,
                target=value,
                scenario_family=scenario_family_by_session.get(current.session_id),
                quality_class=quality_class,
                label_provenance=provenance,
            )
        )

    rows.sort(key=lambda row: (row.target_started_at, row.row_id))
    exclusions.sort(
        key=lambda item: (
            str(item["input_pull_id"]),
            str(item["target_pull_id"] or ""),
            str(item["reason"]),
        )
    )
    class_counts = Counter("positive" if row.target else "negative" for row in rows)
    source_fingerprint = stable_hash(
        {
            "input_source_hashes": sorted(row.input_source_hash for row in rows),
            "target_source_hashes": sorted(row.target_source_hash for row in rows),
            "source_role": source_role,
        }
    )
    checksum_payload = {
        "model_spec_checksum": spec.checksum,
        "label_checksum": spec.label_definition.checksum,
        "feature_set_version": spec.feature_set_version,
        "input_dataset_checksum": input_dataset.checksum,
        "outcome_dataset_checksum": outcome_dataset.checksum,
        "repository_sha": repository_sha,
        "source_fingerprint": source_fingerprint,
        "rows": [
            {
                "row_id": row.row_id,
                "features": row.features,
                "missing": row.missing,
                "feature_quality": row.feature_quality,
                "target": row.target,
                "vehicle_id": row.vehicle_id,
                "configuration_id": row.configuration_id,
                "session_id": row.session_id,
                "scenario_family": row.scenario_family,
                "label_provenance": row.label_provenance,
            }
            for row in rows
        ],
        "exclusions": exclusions,
    }
    checksum = stable_hash(checksum_payload)
    time_range = {
        "start": min(row.input_started_at for row in rows).isoformat() if rows else "",
        "end": max(row.target_started_at for row in rows).isoformat() if rows else "",
    }
    scenario_counts = Counter(row.scenario_family or "unspecified" for row in rows)
    manifest = {
        "task": spec.task.value,
        "validation_type": (
            "ENGINEERING_VALIDATION"
            if source_role in {"synthetic", "imported_fixture"}
            else "REAL_WORLD_VALIDATION"
        ),
        "source_role": source_role,
        "feature_set_version": spec.feature_set_version,
        "input_dataset": {
            "name": input_dataset.definition.name,
            "version": input_dataset.definition.version,
            "checksum": input_dataset.checksum,
        },
        "outcome_dataset": {
            "name": outcome_dataset.definition.name,
            "version": outcome_dataset.definition.version,
            "checksum": outcome_dataset.checksum,
        },
        "label_definition": spec.label_definition.manifest(),
        "label_definition_checksum": spec.label_definition.checksum,
        "model_spec": spec.manifest(),
        "model_spec_checksum": spec.checksum,
        "repository_sha": repository_sha,
        "source_fingerprint": source_fingerprint,
        "dataset_checksum": checksum,
        "time_range": time_range,
        "row_count": len(rows),
        "positive_count": class_counts["positive"],
        "negative_count": class_counts["negative"],
        "vehicle_count": len({row.vehicle_id for row in rows}),
        "configuration_count": len({row.configuration_id for row in rows}),
        "session_count": len({row.session_id for row in rows}),
        "scenario_family_counts": dict(sorted(scenario_counts.items())),
        "row_ids": [row.row_id for row in rows],
        "excluded_row_count": len(exclusions),
        "excluded_by_reason": dict(sorted(Counter(item["reason"] for item in exclusions).items())),
        "input_feature_keys": list(spec.feature_keys),
        "outcome_feature_keys": list(spec.outcome_feature_keys),
        "target_identity_is_separate_from_features": True,
    }
    return SupervisedDataset(
        spec.task,
        spec,
        input_dataset.checksum,
        outcome_dataset.checksum,
        checksum,
        source_fingerprint,
        tuple(rows),
        tuple(exclusions),
        manifest,
    )


def _make_target(
    prior: dict[str, Any], target: dict[str, Any], spec: ModelSpec
) -> tuple[bool | None, dict[str, Any], LabelExclusionReason | None]:
    key = spec.task
    source_values: dict[str, Any] = {}
    if key in {MLTask.THERMAL_DEGRADATION, MLTask.PERFORMANCE_DEGRADATION}:
        source_keys = spec.outcome_feature_keys[:1]
        source_rows: tuple[dict[str, Any], ...] = (prior, target)
    else:
        source_keys = spec.outcome_feature_keys
        source_rows = (target,)
    for feature_key in source_keys:
        for row in source_rows:
            value = row["features"].get(feature_key)
            if value is None:
                reason = row["missing"].get(feature_key)
                if reason == "unavailable_signal":
                    return None, {}, LabelExclusionReason.MISSING_OUTCOME_SIGNAL
                if reason == "not_applicable":
                    return None, {}, LabelExclusionReason.LABEL_NOT_APPLICABLE
                return None, {}, LabelExclusionReason.INSUFFICIENT_OUTCOME_QUALITY
            if row["feature_quality"].get(feature_key) != "valid":
                return None, {}, LabelExclusionReason.INSUFFICIENT_OUTCOME_QUALITY
        if key is MLTask.FUEL_DEVIATION:
            source_values.setdefault(feature_key, {})["target"] = target["features"][feature_key]
        else:
            source_values.setdefault(feature_key, {})["prior"] = prior["features"][feature_key]
            source_values.setdefault(feature_key, {})["target"] = target["features"][feature_key]

    if key is MLTask.THERMAL_DEGRADATION:
        old = float(prior["features"]["thermal.iat_start"])
        new = float(target["features"]["thermal.iat_start"])
        observed = new - old
        threshold = float(spec.label_definition.threshold_policy["positive_when_delta_k_at_least"])
        result = observed >= threshold
        source_values["measured_delta_k"] = observed
    elif key is MLTask.PERFORMANCE_DEGRADATION:
        old = float(prior["features"]["performance.rpm_3500_4500_s_per_1000rpm"])
        new = float(target["features"]["performance.rpm_3500_4500_s_per_1000rpm"])
        if old <= 0:
            return None, {}, LabelExclusionReason.LABEL_NOT_APPLICABLE
        observed = new / old - 1.0
        threshold = float(
            spec.label_definition.threshold_policy[
                "positive_when_relative_interval_increase_at_least"
            ]
        )
        result = observed >= threshold
        source_values["relative_interval_change"] = observed
    elif key is MLTask.FUEL_DEVIATION:
        target_min = float(target["features"]["fuel.rail_pressure_min"])
        historical_mean = float(target["features"]["history.prior_fuel_mean_pa"])
        prior_count = int(target["features"]["temporal_context.prior_pull_count"])
        if historical_mean <= 0:
            return None, {}, LabelExclusionReason.LABEL_NOT_APPLICABLE
        if prior_count < MINIMUM_PRIOR_FUEL_PULLS:
            return None, {}, LabelExclusionReason.NO_COMPATIBLE_PRIOR
        ratio = target_min / historical_mean
        threshold = float(
            spec.label_definition.threshold_policy["positive_when_min_pressure_ratio_at_most"]
        )
        result = ratio <= threshold
        source_values.update(
            {
                "target_min_pressure_pa": target_min,
                "compatible_history_mean_pa": historical_mean,
                "compatible_prior_pull_count": prior_count,
                "min_to_history_ratio": ratio,
            }
        )
    else:
        return None, {}, LabelExclusionReason.LABEL_NOT_APPLICABLE

    provenance = {
        "label_key": spec.label_definition.key,
        "label_version": spec.label_definition.version,
        "algorithm_id": spec.label_definition.algorithm_id,
        "algorithm_version": spec.label_definition.algorithm_version,
        "outcome_pull_id": target["pull_id"],
        "outcome_vehicle_id": target["vehicle_id"],
        "outcome_configuration_id": target["configuration_id"],
        "outcome_session_id": target["session_id"],
        "outcome_started_at": target["started_at"],
        "outcome_ended_at": target["ended_at"],
        "outcome_feature_set_id": target["feature_set_id"],
        "outcome_source_hash": target["feature_set_source_hash"],
        "baseline_pull_id": prior["pull_id"],
        "baseline_feature_set_id": prior["feature_set_id"],
        "baseline_source_hash": prior["feature_set_source_hash"],
        "source_values": source_values,
        "quality_status": "accepted",
        "outcome_pull_completeness": target["quality"].get("pull_completeness"),
        "outcome_feature_quality": {
            feature_key: target["feature_quality"].get(feature_key)
            for feature_key in spec.label_definition.source_feature_keys
        },
        "threshold_policy": spec.label_definition.threshold_policy,
    }
    return result, provenance, None


def _input_vector(
    row: dict[str, Any], spec: ModelSpec
) -> tuple[dict[str, float | None], dict[str, str], dict[str, str]]:
    values: dict[str, float | None] = {}
    missing: dict[str, str] = {}
    qualities: dict[str, str] = {}
    for key in spec.feature_keys:
        value = row["features"].get(key)
        quality = str(row["feature_quality"].get(key, "unavailable"))
        qualities[key] = quality
        if value is None:
            reason = str(row["missing"].get(key, "not_observed_yet"))
            missing[key] = reason
            values[key] = None
            continue
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise SupervisedDatasetError(f"numeric input feature {key} contains a nonnumeric value")
        numeric = float(value)
        if numeric != numeric or numeric in {float("inf"), float("-inf")}:
            raise SupervisedDatasetError(f"numeric input feature {key} is not finite")
        values[key] = numeric
    return values, missing, qualities
