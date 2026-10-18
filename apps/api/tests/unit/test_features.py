from dataclasses import replace
from datetime import UTC, datetime, timedelta

import pytest

from vehicle_platform.features.context import FeatureContext, HistoricalPull, TelemetryFeatureSample
from vehicle_platform.features.datasets import (
    _atomic_write,
    _eligible,
    _lineage_is_safe,
    _valid_serialized_value,
    chronological_split,
    profile_dataset,
    walk_forward_windows,
)
from vehicle_platform.features.domain import (
    CutoffPolicy,
    DatasetDefinition,
    EntityScope,
    FeatureCategory,
    FeatureDefinition,
    FeatureDType,
    FeatureQuality,
    FeatureSetVersion,
    FeatureValue,
    HorizonKind,
    LabelDefinition,
    MissingReason,
    PredictionHorizon,
    TemporalAvailability,
    stable_hash,
)
from vehicle_platform.features.registry import DEFAULT_REGISTRY, FeatureRegistry, validate_value
from vehicle_platform.features.service import default_feature_version
from vehicle_platform.telemetry.domain import SIGNAL_BY_KEY

START = datetime(2026, 1, 1, tzinfo=UTC)


def sample(identifier: str, signal: str, value: float, at: datetime) -> TelemetryFeatureSample:
    return TelemetryFeatureSample(
        sample_id=identifier,
        observed_at=at,
        ingested_at=at,
        signal=signal,
        value=value,
        unit="K" if "temperature" in signal else "Pa",
        quality="valid",
        content_hash=identifier,
    )


def context(
    samples: tuple[TelemetryFeatureSample, ...],
    *,
    prior: tuple[HistoricalPull, ...] = (),
    events: tuple[dict[str, object], ...] = (),
) -> FeatureContext:
    pull = {
        "id": "pull-current",
        "session_id": "session-a",
        "vehicle_id": "vehicle-a",
        "started_at": START,
        "ended_at": START + timedelta(seconds=4),
        "created_at": START,
        "data_completeness": 1.0,
    }
    return FeatureContext(
        pull=pull,
        session={
            "id": "session-a",
            "created_at": START,
            "source_type": "synthetic",
            "metadata": {},
        },
        vehicle={"id": "vehicle-a", "engine_code": "N55", "created_at": START},
        configuration={
            "id": "configuration-a",
            "description": "Stage 1",
            "metadata": {"stage": "stage1", "fuel_type": "93 AKI"},
            "effective_at": START - timedelta(days=1),
        },
        modifications=(),
        raw_samples=samples,
        valid_samples=samples,
        prior_pulls=prior,
        prior_pull_count=len(prior),
        repeated_pull_index=1,
        events=events,
        observation_cutoff=START + timedelta(seconds=4),
        effective_configuration_id="configuration-a",
        context_available_at=START,
        configuration_available_at=START,
        signal_coverage={signal: 1.0 for signal in {item.signal for item in samples}},
        frame_count=len({item.observed_at for item in samples}),
        quality_metadata={
            "duplicate_timestamp_count": 0,
            "pull_completeness": 1.0,
            "data_role": "synthetic",
        },
    )


def definition(
    key: str,
    unit: str | None,
    availability: TemporalAvailability = TemporalAvailability.DURING_WINDOW,
    bounds: tuple[float | None, float | None] | None = None,
) -> FeatureDefinition:
    return FeatureDefinition(
        key=key,
        name=key,
        description="test feature",
        category=FeatureCategory.QUALITY,
        unit=unit,
        dtype=FeatureDType.FLOAT if unit else FeatureDType.BOOLEAN,
        scope=EntityScope.PULL,
        availability=availability,
        bounds=bounds,
    )


def test_feature_definition_enforces_key_unit_and_quality() -> None:
    with pytest.raises(ValueError, match="canonical dotted"):
        definition("Bad-Key", "K")
    with pytest.raises(ValueError, match="numeric features require"):
        FeatureDefinition(
            "quality.ratio",
            "ratio",
            "quality ratio",
            FeatureCategory.QUALITY,
            None,
            FeatureDType.FLOAT,
            EntityScope.PULL,
        )
    with pytest.raises(ValueError, match="minimum_quality"):
        FeatureDefinition(
            "quality.ratio",
            "ratio",
            "quality ratio",
            FeatureCategory.QUALITY,
            "ratio",
            FeatureDType.FLOAT,
            EntityScope.PULL,
            minimum_quality=1.1,
        )


def test_default_registry_is_complete_and_versioned_deterministically() -> None:
    version_a = default_feature_version()
    version_b = default_feature_version()
    assert len(DEFAULT_REGISTRY.list()) == 76
    assert version_a.checksum == version_b.checksum
    assert version_a.manifest() == version_b.manifest()
    assert {item.category for item in DEFAULT_REGISTRY.list()} >= {
        FeatureCategory.RAW_CONTEXT,
        FeatureCategory.THERMAL,
        FeatureCategory.PERFORMANCE,
        FeatureCategory.BOOST_AIR,
        FeatureCategory.FUEL,
        FeatureCategory.QUALITY,
        FeatureCategory.HISTORY,
        FeatureCategory.TEMPORAL_CONTEXT,
    }


def test_feature_version_rejects_duplicate_keys_and_naive_timestamp() -> None:
    item = DEFAULT_REGISTRY.resolve("thermal.iat_delta_k")
    with pytest.raises(ValueError, match="unique definitions"):
        FeatureSetVersion("version-a", (item, item), "g1", "s1", {}, {}, {})
    with pytest.raises(ValueError, match="timezone"):
        FeatureSetVersion("version-b", (item,), "g1", "s1", {}, {}, {}, datetime(2026, 1, 1))


def test_registry_calculates_thermal_quality_and_configuration_features() -> None:
    rows = tuple(
        sample(
            f"iat-{index}",
            "engine.intake_air_temperature",
            300 + index * 2,
            START + timedelta(seconds=index * 2),
        )
        for index in range(3)
    )
    result = DEFAULT_REGISTRY.compute(
        context(rows),
        (
            "thermal.iat_delta_k",
            "thermal.iat_slope_k_per_s",
            "raw_context.configuration_stage",
            "raw_context.engine_code",
            "quality.observation_count",
        ),
    )
    assert result["thermal.iat_delta_k"].value == 4
    assert result["thermal.iat_slope_k_per_s"].value == 1
    assert result["raw_context.configuration_stage"].value == "stage1"
    assert result["raw_context.engine_code"].value == "N55"
    assert result["quality.observation_count"].value == 3


def test_registry_computes_all_feature_families_from_rich_history() -> None:
    signals = (
        "engine.rpm",
        "vehicle.speed",
        "engine.throttle_position",
        "engine.boost_pressure",
        "engine.intake_air_temperature",
        "engine.oil_temperature",
        "engine.coolant_temperature",
        "fuel.high_pressure",
    )

    def build_samples(prefix: str, origin: datetime, temperature_offset: float):
        return tuple(
            TelemetryFeatureSample(
                sample_id=f"{prefix}-{signal}-{index}",
                observed_at=origin + timedelta(milliseconds=index * 500),
                ingested_at=origin + timedelta(milliseconds=index * 500),
                signal=signal,
                value={
                    "engine.rpm": 3000 + index * 250,
                    "vehicle.speed": 15 + index * 1.75,
                    "engine.throttle_position": 92 - index,
                    "engine.boost_pressure": 90_000 + index * 5_000,
                    "engine.intake_air_temperature": 300 + temperature_offset + index,
                    "engine.oil_temperature": 330 + temperature_offset + index,
                    "engine.coolant_temperature": 335 + temperature_offset + index,
                    "fuel.high_pressure": 15_000_000 - index * 100_000,
                }[signal],
                unit=SIGNAL_BY_KEY[signal].unit,
                quality="valid",
                content_hash=f"{prefix}-{signal}-{index}",
            )
            for index in range(9)
            for signal in signals
        )

    prior_pulls = tuple(
        HistoricalPull(
            {
                "id": f"pull-prior-{index}",
                "session_id": "session-a",
                "vehicle_id": "vehicle-a",
                "started_at": START - timedelta(minutes=index),
                "ended_at": START - timedelta(minutes=index) + timedelta(seconds=4),
                "created_at": START - timedelta(minutes=index),
                "data_completeness": 1.0,
            },
            build_samples(f"prior-{index}", START - timedelta(minutes=index), index * 2),
            "configuration-a",
        )
        for index in (1, 2)
    )
    current_samples = build_samples("current", START, 5)
    rich_context = context(
        current_samples,
        prior=prior_pulls,
        events=(
            {
                "id": "event-prior",
                "event_type": "sensor_dropout",
                "started_at": START - timedelta(seconds=10),
                "ended_at": START - timedelta(seconds=9),
                "created_at": START - timedelta(seconds=8),
            },
        ),
    )
    rich_context = FeatureContext(
        **{
            **rich_context.__dict__,
            "quality_metadata": {
                **rich_context.quality_metadata,
                "expected_coverage_ratio": 0.9,
            },
            "session": {**rich_context.session, "metadata": {"truncated": True}},
        }
    )
    values = DEFAULT_REGISTRY.compute(rich_context)
    assert set(values) == {item.key for item in DEFAULT_REGISTRY.list()}
    assert values["fuel.rail_pressure_mean"].value is not None
    assert values["thermal.recovery_elapsed_s"].value == 56
    assert values["history.prior_event_count"].value == 1
    assert values["quality.dropout_event_count"].value == 1
    assert values["quality.expected_coverage_ratio"].value == 0.9
    assert values["quality.truncated"].value is True


def test_missing_fuel_signal_is_never_fabricated() -> None:
    rows = tuple(
        sample(
            f"iat-{index}",
            "engine.intake_air_temperature",
            300 + index,
            START + timedelta(seconds=index),
        )
        for index in range(3)
    )
    value = DEFAULT_REGISTRY.compute(context(rows), ("fuel.rail_pressure_mean",))[
        "fuel.rail_pressure_mean"
    ]
    assert value.value is None
    assert value.missing_reason is MissingReason.UNAVAILABLE_SIGNAL
    assert value.quality is FeatureQuality.UNAVAILABLE


def test_history_uses_only_prior_samples_and_source_ids() -> None:
    prior_at = START - timedelta(minutes=1)
    prior_row = {
        "id": "pull-prior",
        "session_id": "session-a",
        "vehicle_id": "vehicle-a",
        "started_at": prior_at,
        "ended_at": prior_at + timedelta(seconds=4),
        "created_at": prior_at,
    }
    prior = HistoricalPull(
        prior_row,
        (
            sample("fuel-1", "fuel.high_pressure", 10_000_000, prior_at),
            sample("fuel-2", "fuel.high_pressure", 12_000_000, prior_at + timedelta(seconds=1)),
        ),
        "configuration-a",
    )
    result = DEFAULT_REGISTRY.compute(
        context((), prior=(prior,)),
        ("history.prior_fuel_mean_pa", "temporal_context.prior_pull_count"),
    )
    assert result["history.prior_fuel_mean_pa"].value == 11_000_000
    assert result["history.prior_fuel_mean_pa"].source_entities == ("pull-prior",)
    assert result["temporal_context.prior_pull_count"].value == 1


def test_unavailable_calculation_becomes_explicit_computation_error() -> None:
    broken = definition("quality.broken", "ratio")
    from vehicle_platform.features.registry import FeatureRegistry

    registry = FeatureRegistry((broken,), {broken.key: lambda *_: 5})
    value = registry.compute(context(()))[broken.key]
    assert value.value is None
    assert value.missing_reason is MissingReason.COMPUTATION_ERROR


def test_value_validation_enforces_bounds_and_units() -> None:
    bounded = definition("quality.ratio", "ratio", bounds=(0, 1))
    value = FeatureValue(1.2, "ratio", FeatureQuality.VALID, None, START, None, None)
    with pytest.raises(ValueError, match="bounds"):
        validate_value(bounded, value)
    serialized = {
        "value": 1.2,
        "unit": "ratio",
        "quality": FeatureQuality.VALID.value,
    }
    assert not _valid_serialized_value(bounded, serialized)
    assert not _valid_serialized_value(bounded, {**serialized, "unit": "percent", "value": 0.5})


def test_temporal_eligibility_filters_post_window_and_future_values() -> None:
    pull = {"started_at": START, "ended_at": START + timedelta(seconds=4)}
    dataset = DatasetDefinition(
        "cutoff",
        "v1",
        EntityScope.PULL,
        "phase9a-pull-v1",
        ("performance.pull_duration_s",),
        START + timedelta(seconds=2),
        cutoff_policy=CutoffPolicy.GLOBAL,
        horizon=PredictionHorizon(HorizonKind.END_OF_CURRENT_PULL),
    )
    post_window = DEFAULT_REGISTRY.resolve("performance.pull_duration_s")
    item = {
        "value": 4,
        "available_at": (START + timedelta(seconds=4)).isoformat(),
        "source_window_end": (START + timedelta(seconds=4)).isoformat(),
    }
    assert not _eligible(post_window, item, dataset.observation_cutoff, pull, dataset)
    assert not _eligible(
        post_window,
        {**item, "available_at": (START + timedelta(seconds=1)).isoformat()},
        START,
        pull,
        dataset,
    )


def test_lineage_guard_rejects_cross_vehicle_and_future_sources() -> None:
    feature = DEFAULT_REGISTRY.resolve("raw_context.engine_code")
    pull = {
        "id": "pull-current",
        "vehicle_id": "vehicle-a",
        "session_id": "session-a",
        "started_at": START,
        "ended_at": START + timedelta(seconds=4),
        "active_modification_ids": [],
    }
    feature_set = {"configuration_id": None}
    item = {
        "value": "N55",
        "unit": None,
        "quality": FeatureQuality.VALID.value,
        "available_at": START.isoformat(),
        "source_window_end": START.isoformat(),
        "source_entities": ["vehicle-b"],
    }
    dataset = DatasetDefinition(
        "lineage",
        "v1",
        EntityScope.PULL,
        "phase9a-pull-v1",
        (feature.key,),
        START + timedelta(seconds=5),
        cutoff_policy=CutoffPolicy.GLOBAL,
    )
    provenance = {"source_context": {"active_modification_ids": []}}
    assert not _lineage_is_safe(
        (feature,),
        {feature.key: item},
        provenance,
        {"pull_rows": {"pull-current": {"active_modification_ids": []}}},
        pull,
        feature_set,
        START + timedelta(seconds=5),
        dataset,
    )


def test_lineage_allows_observed_zero_prior_pull_count() -> None:
    feature = DEFAULT_REGISTRY.resolve("temporal_context.prior_pull_count")
    pull = {
        "id": "pull-current",
        "vehicle_id": "vehicle-a",
        "session_id": "session-a",
        "started_at": START,
        "ended_at": START + timedelta(seconds=4),
        "active_modification_ids": [],
    }
    item = {
        "value": 0,
        "unit": "count",
        "quality": FeatureQuality.VALID.value,
        "available_at": START.isoformat(),
        "source_window_end": None,
        "source_entities": [],
    }
    dataset = DatasetDefinition(
        "zero-history",
        "v1",
        EntityScope.PULL,
        "phase9a-pull-v1",
        (feature.key,),
        START + timedelta(seconds=5),
        cutoff_policy=CutoffPolicy.GLOBAL,
    )
    assert _lineage_is_safe(
        (feature,),
        {feature.key: item},
        {"source_context": {"active_modification_ids": [], "prior_candidates": []}},
        {"pull_rows": {"pull-current": {"active_modification_ids": []}}},
        pull,
        {"configuration_id": None},
        START + timedelta(seconds=5),
        dataset,
    )


def test_dataset_splits_profiles_and_checksums_are_stable() -> None:
    rows = tuple(
        {
            "row_id": f"row-{index}",
            "observation_cutoff": (START + timedelta(days=index)).isoformat(),
            "vehicle_id": f"vehicle-{index % 2}",
            "configuration_id": "configuration-a",
            "features": {"quality.ratio": index / 10},
            "missing": {},
            "quality": {"pull_completeness": 1.0, "data_role": "synthetic"},
        }
        for index in range(6)
    )
    splits = chronological_split(rows, START + timedelta(days=1), START + timedelta(days=3))
    assert [len(splits[key]) for key in ("train", "validation", "test")] == [2, 2, 2]
    windows = walk_forward_windows(
        rows,
        train_span=timedelta(days=2),
        validation_span=timedelta(days=1),
        test_span=timedelta(days=1),
        step=timedelta(days=1),
    )
    assert windows
    feature = definition("quality.ratio", "ratio", bounds=(0, 1))
    dataset = DatasetDefinition(
        "profile", "v1", EntityScope.PULL, "phase9a-pull-v1", (feature.key,), START
    )
    first = profile_dataset(rows, (feature,), dataset)
    second = profile_dataset(rows, (feature,), dataset)
    assert first == second
    assert first["vehicle_distribution"] == {"vehicle-0": 3, "vehicle-1": 3}
    assert stable_hash(first) == stable_hash(second)


def test_export_write_is_atomic_and_rejects_path_traversal(tmp_path) -> None:
    _atomic_write(tmp_path, "safe.jsonl", b'{"ok":true}\n')
    target = tmp_path / "safe.jsonl"
    assert target.read_bytes() == b'{"ok":true}\n'
    with pytest.raises(ValueError, match="filename"):
        _atomic_write(tmp_path, "../outside.jsonl", b"bad")


def test_dataset_definition_rejects_label_conflicts_and_bad_horizon() -> None:
    with pytest.raises(ValueError, match="1..1440"):
        PredictionHorizon(HorizonKind.MINUTES_AHEAD, 0)
    horizon = PredictionHorizon(HorizonKind.MINUTES_AHEAD, 30)
    assert horizon.duration == timedelta(minutes=30)
    with pytest.raises(ValueError, match="conflicts"):
        DatasetDefinition(
            "label-conflict",
            "v1",
            EntityScope.PULL,
            "phase9a-pull-v1",
            ("thermal.iat_delta_k",),
            START,
            label_definition=LabelDefinition(
                "future_label", (), source_feature_keys=("thermal.iat_delta_k",)
            ),
        )


def test_feature_domain_contract_validation_edges() -> None:
    valid_feature = DEFAULT_REGISTRY.resolve("thermal.iat_delta_k")
    with pytest.raises(ValueError, match="invalid feature set version"):
        FeatureSetVersion("bad version", (valid_feature,), "g1", "s1", {}, {}, {})
    with pytest.raises(ValueError, match="unique definitions"):
        FeatureSetVersion("empty", (), "g1", "s1", {}, {}, {})
    with pytest.raises(ValueError, match="name and description"):
        FeatureDefinition(
            "quality.ratio",
            " ",
            "description",
            FeatureCategory.QUALITY,
            "ratio",
            FeatureDType.FLOAT,
            EntityScope.PULL,
        )
    with pytest.raises(ValueError, match="algorithm identity"):
        FeatureDefinition(
            "quality.ratio",
            "ratio",
            "description",
            FeatureCategory.QUALITY,
            "ratio",
            FeatureDType.FLOAT,
            EntityScope.PULL,
            algorithm_id="",
        )
    with pytest.raises(ValueError, match="increasing"):
        FeatureDefinition(
            "quality.ratio",
            "ratio",
            "description",
            FeatureCategory.QUALITY,
            "ratio",
            FeatureDType.FLOAT,
            EntityScope.PULL,
            bounds=(2, 1),
        )
    with pytest.raises(ValueError, match="minutes_ahead"):
        PredictionHorizon(HorizonKind.MINUTES_AHEAD)
    with pytest.raises(ValueError, match="only for minutes_ahead"):
        PredictionHorizon(HorizonKind.NEXT_PULL, 5)
    with pytest.raises(ValueError, match="timezone"):
        FeatureValue(1.0, "K", FeatureQuality.VALID, None, datetime(2026, 1, 1), None, None)
    with pytest.raises(ValueError, match="inverted"):
        FeatureValue(
            1.0,
            "K",
            FeatureQuality.VALID,
            None,
            START,
            START + timedelta(seconds=1),
            START,
        )
    with pytest.raises(ValueError, match="explicit reason"):
        FeatureValue(None, "K", FeatureQuality.UNAVAILABLE, None, None, None, None)
    with pytest.raises(ValueError, match="cannot have a missing reason"):
        FeatureValue(
            1.0,
            "K",
            FeatureQuality.VALID,
            MissingReason.NOT_APPLICABLE,
            None,
            None,
            None,
        )
    with pytest.raises(ValueError, match="finite"):
        FeatureValue(float("nan"), "K", FeatureQuality.VALID, None, None, None, None)
    with pytest.raises(ValueError, match="categorical list"):
        FeatureValue(["valid", 2], None, FeatureQuality.VALID, None, None, None, None)
    with pytest.raises(ValueError, match="pull-scoped"):
        DatasetDefinition(
            "scope",
            "v1",
            EntityScope.SESSION,
            "phase9a-pull-v1",
            (valid_feature.key,),
            START,
        )
    with pytest.raises(ValueError, match="name and version"):
        DatasetDefinition(
            " ", "v1", EntityScope.PULL, "phase9a-pull-v1", (valid_feature.key,), START
        )
    with pytest.raises(ValueError, match="unique"):
        DatasetDefinition(
            "duplicate",
            "v1",
            EntityScope.PULL,
            "phase9a-pull-v1",
            (valid_feature.key, valid_feature.key),
            START,
        )
    with pytest.raises(ValueError, match="required features"):
        DatasetDefinition(
            "required",
            "v1",
            EntityScope.PULL,
            "phase9a-pull-v1",
            (valid_feature.key,),
            START,
            required_features=("quality.observation_count",),
        )
    with pytest.raises(ValueError, match="1..64"):
        DatasetDefinition(
            "too-many-features",
            "v1",
            EntityScope.PULL,
            "phase9a-pull-v1",
            tuple(f"quality.feature_{index}" for index in range(65)),
            START,
        )
    with pytest.raises(ValueError, match="history or quality"):
        DatasetDefinition(
            "minimum",
            "v1",
            EntityScope.PULL,
            "phase9a-pull-v1",
            (valid_feature.key,),
            START,
            minimum_history=-1,
        )
    with pytest.raises(ValueError, match="label key"):
        DatasetDefinition(
            "label",
            "v1",
            EntityScope.PULL,
            "phase9a-pull-v1",
            (valid_feature.key,),
            START,
            label_definition=LabelDefinition(valid_feature.key, ()),
        )


def test_registry_validation_and_unavailable_context_paths() -> None:
    feature = DEFAULT_REGISTRY.resolve("thermal.iat_delta_k")
    with pytest.raises(ValueError, match="already registered"):
        DEFAULT_REGISTRY.register(feature, DEFAULT_REGISTRY.calculators[feature.key])
    with pytest.raises(ValueError, match="exactly one"):
        FeatureRegistry((feature,), {})
    added = definition("quality.extra", "ratio")
    extended = DEFAULT_REGISTRY.register(
        added, lambda ctx, item: ctx.missing(item, MissingReason.NOT_APPLICABLE)
    )
    assert extended.resolve(added.key) == added
    unknown_signal = FeatureDefinition(
        "quality.unknown_signal",
        "unknown signal",
        "unknown signal dependency",
        FeatureCategory.QUALITY,
        "ratio",
        FeatureDType.FLOAT,
        EntityScope.PULL,
        required_signals=("vehicle.telepathy",),
    )
    with pytest.raises(ValueError, match="unknown telemetry signals"):
        FeatureRegistry(
            (unknown_signal,),
            {unknown_signal.key: lambda ctx, item: ctx.missing(item, MissingReason.NOT_APPLICABLE)},
        )
    retired = replace(feature, active=False)
    retired_registry = FeatureRegistry(
        (retired,), {retired.key: DEFAULT_REGISTRY.calculators[feature.key]}
    )
    assert retired_registry.list() == ()
    assert retired_registry.list(active_only=False) == (retired,)
    with pytest.raises(KeyError, match="unknown active"):
        retired_registry.resolve(retired.key)

    invalid_values = (
        (definition("quality.float", "ratio"), True, "finite"),
        (
            FeatureDefinition(
                "quality.integer",
                "integer",
                "integer",
                FeatureCategory.QUALITY,
                "count",
                FeatureDType.INTEGER,
                EntityScope.PULL,
            ),
            True,
            "integer",
        ),
        (
            FeatureDefinition(
                "quality.boolean",
                "boolean",
                "boolean",
                FeatureCategory.QUALITY,
                None,
                FeatureDType.BOOLEAN,
                EntityScope.PULL,
            ),
            1,
            "boolean",
        ),
        (
            FeatureDefinition(
                "quality.category",
                "category",
                "category",
                FeatureCategory.QUALITY,
                None,
                FeatureDType.CATEGORICAL,
                EntityScope.PULL,
            ),
            1,
            "categorical",
        ),
        (
            FeatureDefinition(
                "quality.categories",
                "categories",
                "categories",
                FeatureCategory.QUALITY,
                None,
                FeatureDType.CATEGORICAL_LIST,
                EntityScope.PULL,
            ),
            ("tuple",),
            "wrong type",
        ),
    )
    for item, value, message in invalid_values:
        with pytest.raises(ValueError, match=message):
            validate_value(
                item,
                FeatureValue(value, item.unit, FeatureQuality.VALID, None, START, None, None),
            )
    with pytest.raises(ValueError, match="unit"):
        validate_value(
            feature, FeatureValue(1.0, "percent", FeatureQuality.VALID, None, START, None, None)
        )
    with pytest.raises(ValueError, match="non-nullable"):
        validate_value(
            replace(feature, nullable=False),
            FeatureValue(
                None,
                "K",
                FeatureQuality.UNAVAILABLE,
                MissingReason.NOT_APPLICABLE,
                None,
                None,
                None,
            ),
        )
    with pytest.raises(ValueError, match="outside deterministic bounds"):
        validate_value(
            definition("quality.bounded", "ratio", bounds=(0, 1)),
            FeatureValue(2.0, "ratio", FeatureQuality.VALID, None, START, None, None),
        )

    empty = context(())
    quality = DEFAULT_REGISTRY.compute(
        empty,
        (
            "quality.signal_coverage_ratio",
            "quality.median_sample_interval_s",
            "quality.sample_interval_stddev_s",
            "quality.stuck_signal_count",
            "quality.dropout_event_count",
            "quality.truncated",
            "quality.expected_coverage_ratio",
            "quality.max_gap_s",
            "quality.available_signals",
            "boost_air.throttle_closure_fraction",
            "boost_air.history_deviation_pa",
            "fuel.history_deviation_pa",
            "history.prior_boost_mean_pa",
            "history.prior_performance_mean_s",
            "performance.speed_60_100_kmh_s",
        ),
    )
    assert (
        quality["quality.signal_coverage_ratio"].missing_reason
        is MissingReason.INSUFFICIENT_COVERAGE
    )
    assert (
        quality["quality.median_sample_interval_s"].missing_reason
        is MissingReason.INSUFFICIENT_COVERAGE
    )
    assert quality["quality.sample_interval_stddev_s"].value is None
    assert quality["quality.stuck_signal_count"].value == 0
    assert quality["quality.dropout_event_count"].value == 0
    assert quality["quality.truncated"].missing_reason is MissingReason.NOT_APPLICABLE
    assert quality["quality.expected_coverage_ratio"].missing_reason is MissingReason.NOT_APPLICABLE
    assert quality["quality.max_gap_s"].value == 0
    assert quality["quality.available_signals"].value == []
    assert (
        quality["boost_air.throttle_closure_fraction"].missing_reason
        is MissingReason.UNAVAILABLE_SIGNAL
    )
    assert quality["history.prior_boost_mean_pa"].missing_reason is MissingReason.UNAVAILABLE_SIGNAL
    assert (
        quality["history.prior_performance_mean_s"].missing_reason is MissingReason.NOT_APPLICABLE
    )
    assert (
        quality["performance.speed_60_100_kmh_s"].missing_reason
        is MissingReason.INSUFFICIENT_COVERAGE
    )

    single_sample = sample("single", "engine.intake_air_temperature", 300, START)
    single = context((single_sample,))
    computed = DEFAULT_REGISTRY.compute(
        single,
        (
            "thermal.iat_slope_k_per_s",
            "performance.pull_duration_s",
            "thermal.pre_pull_iat_k",
            "raw_context.configuration_stage",
        ),
    )
    assert (
        computed["thermal.iat_slope_k_per_s"].missing_reason is MissingReason.INSUFFICIENT_COVERAGE
    )
    cutoff = replace(single, observation_cutoff=START + timedelta(seconds=2))
    duration = DEFAULT_REGISTRY.compute(cutoff, ("performance.pull_duration_s",))
    assert duration["performance.pull_duration_s"].missing_reason is MissingReason.NOT_OBSERVED_YET
    no_configuration = replace(empty, configuration=None)
    config_value = DEFAULT_REGISTRY.compute(no_configuration, ("raw_context.configuration_stage",))
    assert (
        config_value["raw_context.configuration_stage"].missing_reason
        is MissingReason.NOT_APPLICABLE
    )

    no_engine = replace(empty, vehicle={**empty.vehicle, "engine_code": None})
    missing_engine = DEFAULT_REGISTRY.compute(no_engine, ("raw_context.engine_code",))
    assert (
        missing_engine["raw_context.engine_code"].missing_reason is MissingReason.UNAVAILABLE_SIGNAL
    )

    blank_metadata = replace(
        empty,
        configuration={**empty.configuration, "metadata": {"stage": "  ", "fuel_type": None}},
    )
    missing_config = DEFAULT_REGISTRY.compute(
        blank_metadata,
        ("raw_context.configuration_stage", "raw_context.fuel_type"),
    )
    assert all(
        item.missing_reason is MissingReason.UNAVAILABLE_SIGNAL for item in missing_config.values()
    )

    low_coverage = replace(
        context((single_sample,)), signal_coverage={"engine.intake_air_temperature": 0.1}
    )
    low_quality = DEFAULT_REGISTRY.compute(low_coverage, ("thermal.iat_mean",))
    assert low_quality["thermal.iat_mean"].missing_reason is MissingReason.INSUFFICIENT_COVERAGE

    prior_row = {
        "id": "pull-prior",
        "session_id": "session-prior",
        "vehicle_id": "vehicle-a",
        "started_at": START - timedelta(minutes=5),
        "ended_at": START - timedelta(minutes=4),
        "created_at": START - timedelta(minutes=4),
        "data_completeness": 1.0,
    }
    prior = HistoricalPull(prior_row, (), "configuration-a")
    current_after_start = sample(
        "iat-after-start", "engine.intake_air_temperature", 305, START + timedelta(seconds=1)
    )
    historical = context((current_after_start,), prior=(prior,))
    historical_values = DEFAULT_REGISTRY.compute(
        historical,
        (
            "thermal.pre_pull_iat_k",
            "thermal.recovery_elapsed_s",
            "thermal.iat_recovery_delta_k",
            "thermal.pull_to_pull_iat_delta_k",
        ),
    )
    assert (
        historical_values["thermal.pre_pull_iat_k"].missing_reason
        is MissingReason.UNAVAILABLE_SIGNAL
    )
    assert historical_values["thermal.recovery_elapsed_s"].value == 240
    assert (
        historical_values["thermal.iat_recovery_delta_k"].missing_reason
        is MissingReason.UNAVAILABLE_SIGNAL
    )
    assert (
        historical_values["thermal.pull_to_pull_iat_delta_k"].missing_reason
        is MissingReason.UNAVAILABLE_SIGNAL
    )

    prior_iat = sample(
        "prior-iat",
        "engine.intake_air_temperature",
        320,
        START - timedelta(minutes=4),
    )
    prior_with_iat = HistoricalPull(prior_row, (prior_iat,), "configuration-a")
    at_start = sample("current-iat-at-start", "engine.intake_air_temperature", 305, START)
    recovery = DEFAULT_REGISTRY.compute(
        context((at_start,), prior=(prior_with_iat,)),
        ("thermal.iat_recovery_delta_k", "thermal.pull_to_pull_iat_delta_k"),
    )
    assert recovery["thermal.iat_recovery_delta_k"].value == 15
    assert recovery["thermal.pull_to_pull_iat_delta_k"].value == -15

    no_history_values = DEFAULT_REGISTRY.compute(
        empty,
        (
            "thermal.recovery_elapsed_s",
            "thermal.iat_recovery_delta_k",
            "thermal.pull_to_pull_iat_delta_k",
        ),
    )
    assert all(
        item.missing_reason is MissingReason.NOT_APPLICABLE for item in no_history_values.values()
    )
