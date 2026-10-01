import json

from vehicle_platform.core.config import Settings
from vehicle_platform.main import create_app


class OfflineProbe:
    async def check(self) -> None:
        raise RuntimeError("Schema export must not access a database")


app = create_app(
    Settings(
        database_url="postgresql+asyncpg://offline@localhost/offline",
        environment="test",
    ),
    probe=OfflineProbe(),
)
print(json.dumps(app.openapi(), indent=2, sort_keys=True))
app.state.telemetry.shutdown()
