from __future__ import annotations

from datetime import UTC, datetime
from typing import cast
from uuid import UUID

import pytest

from vehicle_platform.features.datasets import DatasetBuilder, DatasetValidationError
from vehicle_platform.features.domain import DatasetDefinition, EntityScope
from vehicle_platform.features.registry import DEFAULT_REGISTRY
from vehicle_platform.infrastructure.database import Database


@pytest.mark.asyncio
async def test_dataset_builder_rejects_duplicate_candidate_pull_ids_before_database_io() -> None:
    builder = DatasetBuilder(cast(Database, None), DEFAULT_REGISTRY)
    definition = DatasetDefinition(
        "candidate_scope",
        "v1",
        EntityScope.PULL,
        "phase9a-pull-v1",
        ("thermal.iat_delta_k",),
        datetime(2026, 1, 1, tzinfo=UTC),
    )
    pull_id = UUID("00000000-0000-0000-0000-000000000001")

    with pytest.raises(DatasetValidationError, match="contains duplicates"):
        await builder.build(definition, candidate_pull_ids=(pull_id, pull_id))
