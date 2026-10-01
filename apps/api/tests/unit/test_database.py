from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.exc import OperationalError

from vehicle_platform.core.config import Settings
from vehicle_platform.infrastructure.database import Database, DependencyUnavailable
from vehicle_platform.main import create_app


async def test_real_database_unreachable(settings: Settings) -> None:
    database = Database(settings)
    with pytest.raises(DependencyUnavailable):
        await database.check()
    await database.close()


@pytest.mark.parametrize("enabled", [True, False])
async def test_extension_required(settings: Settings, enabled: bool) -> None:
    database = Database(settings)
    connection = AsyncMock()
    connection.scalar.return_value = enabled
    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=connection)
    cm.__aexit__ = AsyncMock(return_value=False)
    with patch.object(type(database.engine), "connect", return_value=cm):
        if enabled:
            await database.check()
        else:
            with pytest.raises(DependencyUnavailable):
                await database.check()
    await database.close()


async def test_sqlalchemy_failure(settings: Settings) -> None:
    database = Database(settings)
    with patch.object(
        type(database.engine),
        "connect",
        side_effect=OperationalError("sql", {}, Exception("secret")),
    ):
        with pytest.raises(DependencyUnavailable):
            await database.check()
    await database.close()


async def test_real_app_lifespan(settings: Settings) -> None:
    app = create_app(settings)
    async with app.router.lifespan_context(app):
        assert app.openapi()["info"]["title"] == "Vehicle Intelligence Platform"


def test_otlp_configured(settings: Settings) -> None:
    from vehicle_platform.observability.telemetry import Telemetry

    signals = Telemetry(
        settings.model_copy(update={"otel_exporter_otlp_endpoint": "http://localhost:1"})
    )
    signals.shutdown()
