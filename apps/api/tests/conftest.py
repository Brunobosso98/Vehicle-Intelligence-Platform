import pytest

from vehicle_platform.core.config import Settings


@pytest.fixture
def settings() -> Settings:
    return Settings(
        database_url="postgresql+asyncpg://test:test@127.0.0.1:1/test", environment="test"
    )
