"""Independent Phase 9A DB acceptance over the canonical synthetic feature fixture."""

import asyncio
import importlib.util
import json
import sys
from collections import Counter
from datetime import timedelta
from pathlib import Path
from typing import Any
from uuid import uuid4

from pydantic import SecretStr
from sqlalchemy import text
from vehicle_platform.acquisition.adapters import PIDS
from vehicle_platform.core.config import Settings
from vehicle_platform.features.capabilities import feature_source_capability_matrix
from vehicle_platform.features.datasets import DatasetBuilder, _valid_serialized_value
from vehicle_platform.features.domain import (
    CutoffPolicy,
    DatasetDefinition,
    EntityScope,
)
from vehicle_platform.features.registry import DEFAULT_REGISTRY
from vehicle_platform.features.service import (
    FeatureGenerationService,
    FeatureLeakageRejected,
)
from vehicle_platform.infrastructure.database import Database
from vehicle_platform.telemetry.domain import SIGNAL_BY_KEY, SYNTHETIC_TELEMETRY_SIGNALS


def _fixture_seed() -> Any:
    path = Path("apps/api/tests/integration/test_zzz_features.py")
    spec = importlib.util.spec_from_file_location("phase9a_integration_fixture", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("could not load the Phase 9A synthetic DB fixture")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module._seed


async def evaluate() -> None:
    import os

    url = os.environ.get("TEST_DATABASE_URL", "")
    if not url.rsplit("/", 1)[-1].startswith("vehicle_test"):
        raise ValueError("acceptance requires the disposable vehicle_test database")
    database = Database(Settings(database_url=SecretStr(url), environment="test"))
    fixture = await _fixture_seed()(database)
    pulls = fixture["pulls"]
    sessions = fixture["sessions"]
    assert isinstance(pulls, dict) and isinstance(sessions, dict)
    service = FeatureGenerationService(database)
    metrics: dict[str, Any] = {
        "feature_definitions": len(DEFAULT_REGISTRY.list()),
        "feature_sets_generated": 0,
        "deterministic_equalities": 0,
        "deterministic_comparisons": 0,
        "leakage_checks_passed": 0,
        "undetected_deliberate_leakage": 0,
        "invalid_persisted_features": 0,
        "cross_vehicle_leaks": 0,
        "cross_configuration_leaks": 0,
        "fabricated_unavailable_values": 0,
        "late_modification_leaks": 0,
    }
    try:
        await service.ensure_version()
        first = await service.generate_pull(pulls["p1"])
        again = await service.generate_pull(pulls["p1"])
        metrics["deterministic_comparisons"] = 1
        metrics["deterministic_equalities"] = int(
            first.id == again.id and first.source_hash == again.source_hash
        )
        if first.values["thermal.iat_start"].value != 300:
            raise AssertionError(
                "thermal starting IAT differs from canonical telemetry"
            )

        same_a, same_b = await asyncio.gather(
            service.generate_pull(pulls["p2"]), service.generate_pull(pulls["p2"])
        )
        if same_a.id != same_b.id or same_a.source_hash != same_b.source_hash:
            raise AssertionError(
                "concurrent generation did not converge on one feature set"
            )
        results = {
            "p1": first,
            "p2": same_a,
            "p3": await service.generate_pull(pulls["p3"]),
            "p4": await service.generate_pull(pulls["p4"]),
            "p5": await service.generate_pull(pulls["p5"]),
            "p6": await service.generate_pull(pulls["p6"]),
        }
        metrics["feature_sets_generated"] = len(results)
        if first.values["temporal_context.prior_pull_count"].value != 0:
            metrics["undetected_deliberate_leakage"] = 1
            raise AssertionError("a future pull entered the first pull's history")
        metrics["leakage_checks_passed"] += 1
        target = results["p3"]
        if target.values["thermal.iat_delta_k"].value != 4:
            raise AssertionError("thermal delta is not derived from observed K values")
        if target.values["performance.pull_duration_s"].value != 4:
            raise AssertionError(
                "pull duration does not match the recorded pull interval"
            )
        normalized_rpm_time = target.values["performance.rpm_3500_4500_s_per_1000rpm"]
        rpm_value = normalized_rpm_time.value
        if (
            isinstance(rpm_value, bool)
            or not isinstance(rpm_value, (int, float))
            or abs(float(rpm_value) - 2.0) > 1e-9
        ):
            raise AssertionError(
                "normalized RPM interval time differs from recorded RPM samples"
            )
        if target.values["thermal.pre_pull_iat_k"].value != 315:
            raise AssertionError(
                "pre-pull IAT did not use the latest observed pre-pull sample"
            )
        if target.values["boost_air.pressure_max"].value != 108_000:
            raise AssertionError("boost peak does not match canonical Pa samples")
        fuel = target.values["fuel.rail_pressure_mean"]
        fuel_unavailable_mismatch = fuel.value is not None or (
            fuel.missing_reason is None
            or fuel.missing_reason.value != "unavailable_signal"
        )
        metrics["fabricated_unavailable_values"] = int(fuel_unavailable_mismatch)
        if metrics["fabricated_unavailable_values"]:
            raise AssertionError("missing fuel signal produced a sensor value")
        if target.values["quality.observation_count"].value != 35:
            metrics["undetected_deliberate_leakage"] = 1
            raise AssertionError("future-ingested sample entered quality counts")
        metrics["leakage_checks_passed"] += 1
        if target.values["history.prior_event_count"].value != 1:
            metrics["undetected_deliberate_leakage"] = 1
            raise AssertionError("future-created event leaked into prior event history")
        metrics["leakage_checks_passed"] += 1
        if target.values["temporal_context.prior_pull_count"].value != 2:
            raise AssertionError(
                "same-vehicle/configuration prior history is incorrect"
            )
        late_modification = str(fixture["late_modification"])
        if (
            late_modification
            in first.provenance["source_context"]["active_modification_ids"]
        ):
            metrics["late_modification_leaks"] = 1
            metrics["undetected_deliberate_leakage"] = 1
            raise AssertionError(
                "a later-recorded modification entered an earlier pull"
            )
        if (
            late_modification
            in target.provenance["source_context"]["active_modification_ids"]
        ):
            metrics["late_modification_leaks"] = 1
            metrics["undetected_deliberate_leakage"] = 1
            raise AssertionError(
                "a later-recorded modification entered a pre-recording cutoff"
            )
        metrics["leakage_checks_passed"] += 1
        if results["p5"].values["temporal_context.prior_pull_count"].value != 0:
            metrics["cross_vehicle_leaks"] = 1
        if results["p4"].values["temporal_context.prior_pull_count"].value != 0:
            metrics["cross_configuration_leaks"] = 1
        if metrics["cross_vehicle_leaks"] or metrics["cross_configuration_leaks"]:
            metrics["undetected_deliberate_leakage"] = 1
            raise AssertionError("history crossed vehicle or configuration boundary")
        metrics["leakage_checks_passed"] += 2

        try:
            await service.generate_pull(
                pulls["p3"], fixture["start"] - timedelta(days=2)
            )
        except FeatureLeakageRejected:
            metrics["leakage_checks_passed"] += 1
        else:
            metrics["undetected_deliberate_leakage"] = 1
            raise AssertionError(
                "future pull was not rejected against observation cutoff"
            )

        alternate = FeatureGenerationService(database)
        alternate.version = type(service.version)(
            version="phase9a-pull-v2-acceptance",
            definitions=service.version.definitions,
            generator_version=service.version.generator_version,
            source_schema_version=service.version.source_schema_version,
            selection_policy=service.version.selection_policy,
            quality_policy=service.version.quality_policy,
            temporal_policy=service.version.temporal_policy,
        )
        alternate_set = await alternate.generate_pull(pulls["p3"])
        if alternate_set.id == target.id:
            raise AssertionError(
                "feature version change reused an incompatible FeatureSet"
            )

        definition = DatasetDefinition(
            name=f"phase9a-acceptance-{uuid4().hex[:12]}",
            version="v1",
            row_scope=EntityScope.PULL,
            feature_set_version=service.version.version,
            selected_features=(
                "raw_context.engine_code",
                "raw_context.configuration_stage",
                "thermal.iat_delta_k",
                "thermal.pre_pull_iat_k",
                "history.prior_event_count",
                "performance.pull_duration_s",
                "performance.rpm_3500_4500_s_per_1000rpm",
                "boost_air.pressure_max",
                "history.prior_boost_mean_pa",
                "fuel.rail_pressure_mean",
                "quality.observation_count",
            ),
            observation_cutoff=fixture["start"] + timedelta(seconds=60),
            cutoff_policy=CutoffPolicy.ROW_END,
            minimum_quality=0.5,
            allow_configuration_mixing=True,
        )
        builder = DatasetBuilder(database, DEFAULT_REGISTRY)
        dataset_a = await builder.build(definition)
        dataset_b = await builder.build(definition)
        if dataset_a.checksum != dataset_b.checksum:
            raise AssertionError("repeat dataset builds have different checksums")
        exclusions = Counter(item["reason"] for item in dataset_a.exclusions)
        if exclusions["minimum_quality_not_met"] != 1:
            raise AssertionError("poor-quality row exclusion lacks an explicit reason")
        if dataset_a.manifest["vehicle_count"] != 2:
            raise AssertionError(
                "acceptance dataset must contain rows for both vehicles"
            )
        if dataset_a.manifest["configuration_count"] != 3:
            raise AssertionError(
                "acceptance dataset must cover all three configurations; "
                f"manifest={dataset_a.manifest['configuration_distribution']}, "
                f"rows={[row['configuration_id'] for row in dataset_a.rows]}, "
                f"exclusions={dataset_a.exclusions}"
            )
        variation: dict[str, list[object]] = {}
        for feature_key in (
            "thermal.iat_delta_k",
            "boost_air.pressure_max",
            "fuel.rail_pressure_mean",
        ):
            variation_values = sorted(
                {
                    row["features"][feature_key]
                    for row in dataset_a.rows
                    if feature_key in row["features"]
                }
            )
            if len(variation_values) < 2:
                raise AssertionError(
                    f"acceptance dataset lacks {feature_key} variation"
                )
            variation[feature_key] = variation_values
        metrics["dataset_rows"] = len(dataset_a.rows)
        metrics["dataset_vehicle_count"] = dataset_a.manifest["vehicle_count"]
        metrics["dataset_configuration_count"] = dataset_a.manifest[
            "configuration_count"
        ]
        metrics["dataset_feature_variation"] = variation
        metrics["dataset_exclusions_by_reason"] = dict(sorted(exclusions.items()))
        metrics["dataset_checksum_stability"] = 1.0
        metrics["dataset_checksum"] = dataset_a.checksum
        categories = Counter(item.category.value for item in DEFAULT_REGISTRY.list())
        availability = Counter(
            item.availability.value for item in DEFAULT_REGISTRY.list()
        )
        metrics["feature_counts_by_category"] = dict(sorted(categories.items()))
        metrics["feature_counts_by_availability"] = dict(sorted(availability.items()))

        async with database.session() as db:
            rows = (
                (
                    await db.execute(
                        text(
                            "SELECT feature_values FROM feature_sets WHERE pull_id=ANY(:ids)"
                        ),
                        {"ids": list(pulls.values())},
                    )
                )
                .scalars()
                .all()
            )
        invalid = 0
        for vector in rows:
            persisted_values = (
                vector if isinstance(vector, dict) else json.loads(vector)
            )
            for key, item in persisted_values.items():
                definition_item = DEFAULT_REGISTRY.resolve(key)
                if item.get("value") is None:
                    valid_missing = item.get(
                        "unit"
                    ) == definition_item.unit and item.get("missing_reason") in {
                        "unavailable_signal",
                        "insufficient_coverage",
                        "invalid_quality",
                        "not_applicable",
                        "not_observed_yet",
                        "computation_error",
                    }
                else:
                    valid_missing = _valid_serialized_value(definition_item, item)
                if not valid_missing:
                    invalid += 1
        metrics["invalid_persisted_features"] = invalid
        if invalid:
            raise AssertionError("persisted feature payload failed registry validation")

        report = {
            "status": "PASS",
            "fixture": {
                "vehicles": 2,
                "configurations": 3,
                "sessions": 4,
                "pulls": 6,
                "event_cases": 2,
                "future_ingestion_sample": True,
                "non_boundary_pre_pull_thermal_sample": True,
                "unavailable_fuel_case": True,
                "poor_quality_case": True,
                "retroactively_recorded_modification": True,
                "feature_dataset_spans_two_vehicles": True,
                "feature_dataset_spans_three_configurations": True,
            },
            "metrics": metrics,
            "baseline_profile_path": ".validation/phase9a/baseline-profile.json",
            "acceptance_assertions": [
                "registry loaded",
                "repeat and concurrent generation deterministic/idempotent",
                "different version persisted separately",
                "thermal, performance and boost values match recorded units/data",
                "normalized RPM interval timing uses bounded monotonic Phase 5 analytics",
                "pre-pull thermal features use latest cutoff-eligible vehicle telemetry",
                "unavailable fuel stays null with unavailable_signal reason",
                "future-ingested sample and future-created event excluded",
                "future pull rejected by observation cutoff",
                "history isolated by vehicle and effective configuration",
                "later-recorded modification excluded before it became observable",
                "model-ready rows span two vehicles and three configurations with thermal, boost and fuel variation",
                "dataset checksum stable and exclusion reason explicit",
                "persisted values satisfy definition type/unit/bounds",
            ],
        }
        target_path = Path(".validation/phase9a/acceptance.json")
        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
        profile = {
            "status": "PROFILED_SYNTHETIC_ACCEPTANCE_FIXTURE",
            "feature_set_version": service.version.version,
            "feature_set_version_checksum": service.version.checksum,
            "feature_count": len(DEFAULT_REGISTRY.list()),
            "feature_availability_matrix": feature_source_capability_matrix(
                DEFAULT_REGISTRY.list(),
                {
                    "synthetic_generator": SYNTHETIC_TELEMETRY_SIGNALS,
                    "csv_replay": frozenset(SIGNAL_BY_KEY),
                    "generic_obd_ii": frozenset(pid.signal for pid in PIDS),
                    "richer_future_source": None,
                },
                conditional_sources=frozenset({"csv_replay"}),
                preflight_sources=frozenset({"generic_obd_ii"}),
            ),
            "acceptance_dataset_profile": dataset_a.profile,
            "manifest": dataset_a.manifest,
        }
        Path(".validation/phase9a/baseline-profile.json").write_text(
            json.dumps(profile, indent=2, sort_keys=True) + "\n"
        )
        print(json.dumps(report, indent=2, sort_keys=True))
    finally:
        await database.close()


if __name__ == "__main__":
    asyncio.run(evaluate())
