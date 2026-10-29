from __future__ import annotations

from typing import cast

import pytest

from vehicle_platform.infrastructure.database import Database
from vehicle_platform.ml.synthetic import seed_predictive_fixture


@pytest.mark.asyncio
@pytest.mark.parametrize("vehicle_count", (3, 9))
async def test_predictive_fixture_rejects_unbounded_vehicle_cohorts(
    vehicle_count: int,
) -> None:
    with pytest.raises(ValueError, match="between four and eight"):
        await seed_predictive_fixture(cast(Database, None), vehicle_count=vehicle_count)
