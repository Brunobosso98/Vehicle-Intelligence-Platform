"""Assert real Phase 9A feature and dataset telemetry is rendered without entity labels."""

import asyncio
import importlib.util
import json
import os
import sys
from datetime import timedelta
from pathlib import Path
from typing import Any

from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from pydantic import SecretStr
from vehicle_platform.core.config import Settings
from vehicle_platform.features.datasets import DatasetBuilder
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
from vehicle_platform.observability.telemetry import Telemetry


def _fixture_seed() -> Any:
    path = Path("apps/api/tests/integration/test_zzz_features.py")
    spec = importlib.util.spec_from_file_location("phase9a_observability_fixture", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("could not load Phase 9A fixture")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module._seed


async def main() -> None:
    url = os.environ.get("TEST_DATABASE_URL", "")
    if not url.rsplit("/", 1)[-1].startswith("vehicle_test"):
        raise ValueError(
            "observability validation requires a disposable vehicle_test database"
        )
    settings = Settings(database_url=SecretStr(url), environment="test")
    database, telemetry = Database(settings), Telemetry(settings)
    span_exporter = InMemorySpanExporter()
    telemetry.traces.add_span_processor(SimpleSpanProcessor(span_exporter))
    fixture = await _fixture_seed()(database)
    pulls = fixture["pulls"]
    assert isinstance(pulls, dict)
    try:
        service = FeatureGenerationService(database, telemetry)
        await service.ensure_version()
        await service.generate_pull(pulls["p1"])
        try:
            await service.generate_pull(
                pulls["p1"], fixture["start"] - timedelta(days=2)
            )
        except FeatureLeakageRejected:
            pass
        else:
            raise AssertionError("expected a counted cutoff rejection")
        definition = DatasetDefinition(
            name="phase9a-observability",
            version="v1",
            row_scope=EntityScope.PULL,
            feature_set_version=service.version.version,
            selected_features=("raw_context.engine_code", "quality.observation_count"),
            observation_cutoff=fixture["start"] + timedelta(seconds=60),
            cutoff_policy=CutoffPolicy.ROW_END,
            allow_configuration_mixing=True,
        )
        result = await DatasetBuilder(database, DEFAULT_REGISTRY, telemetry).build(
            definition
        )
        rendered = telemetry.render_metrics().decode("utf-8")
        telemetry.traces.force_flush()
        spans = span_exporter.get_finished_spans()
        span_names = {span.name for span in spans}
        expected_spans = {
            "features.generate",
            "features.configuration_resolve",
            "features.telemetry_read",
            "features.compute",
            "features.dataset.build",
        }
        if not expected_spans <= span_names:
            raise AssertionError(
                f"Phase 9A trace spans missing: {expected_spans - span_names}"
            )
        expected = (
            "features_generation_runs",
            "features_sets",
            "features_generation_failures",
            "features_generation_duration",
            "features_values_null",
            "features_leakage_rejections",
            "features_dataset_builds",
            "features_dataset_rows",
            "features_dataset_exclusions",
            "features_dataset_build_duration",
        )
        missing = [name for name in expected if name not in rendered]
        if missing:
            raise AssertionError(
                f"Phase 9A metrics missing after real operations: {missing}"
            )
        for identifier in (str(pulls["p1"]), str(fixture["vehicles"]["a"])):
            if identifier in rendered:
                raise AssertionError("entity identifier appeared in metric exposition")
            if any(identifier in repr(span.attributes) for span in spans):
                raise AssertionError("entity identifier appeared in feature spans")
        report = {
            "status": "PASS",
            "feature_set_rows": 1,
            "dataset_rows": len(result.rows),
            "metrics_verified": list(expected),
            "spans_verified": sorted(expected_spans),
            "entity_labels": "none",
            "metric_excerpt": "\n".join(
                line
                for line in rendered.splitlines()
                if any(key in line for key in expected)
            ),
        }
        target = Path(".validation/phase9a/observability.json")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
        print(json.dumps(report, indent=2, sort_keys=True))
    finally:
        await database.close()
        telemetry.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
