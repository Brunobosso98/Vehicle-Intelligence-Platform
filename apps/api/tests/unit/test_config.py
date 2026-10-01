import pytest
from pydantic import ValidationError

from vehicle_platform.core.config import Settings


@pytest.mark.parametrize(
    "url", ["", "sqlite://test", "postgresql+asyncpg://localhost", "postgresql+asyncpg:///db"]
)
def test_malformed_database_config(url: str) -> None:
    with pytest.raises(ValidationError):
        Settings(database_url=url)


def test_required_database(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    with pytest.raises(ValidationError):
        Settings(_env_file=None)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"database_url": "postgresql+asyncpg://user@localhost/db", "environment": "production"},
        {
            "database_url": "postgresql+asyncpg://u:local-development-only@localhost/db?ssl=require",
            "environment": "production",
        },
        {
            "database_url": "postgresql+asyncpg://u:explicit-production-value@localhost/db",
            "environment": "production",
        },
        {"build_timestamp": "2026-10-01T12:00:00"},
        {"readiness_timeout": 0},
        {"otel_exporter_otlp_endpoint": "ftp://localhost"},
    ],
)
def test_invalid_settings(kwargs: dict[str, object]) -> None:
    base = {"database_url": "postgresql+asyncpg://u:p@localhost/db"}
    with pytest.raises(ValidationError):
        Settings(**(base | kwargs))


def test_safe_metadata() -> None:
    settings = Settings(
        database_url="postgresql+asyncpg://u:explicit-production-value@localhost/db?ssl=require",
        environment="production",
        build_timestamp="2026-10-01T12:00:00Z",
        otel_exporter_otlp_endpoint="http://localhost:4318",
    )
    assert "explicit-production-value" not in repr(settings)
    assert settings.build_timestamp is not None and settings.build_timestamp.utcoffset() is not None


def test_empty_optional_container_metadata() -> None:
    settings = Settings(
        database_url="postgresql+asyncpg://u:p@localhost/db", git_sha="", build_timestamp=""
    )
    assert settings.git_sha is None and settings.build_timestamp is None


@pytest.mark.parametrize("endpoint", ["http://", "https://u:secret@localhost"])
def test_unsafe_export_endpoint(endpoint: str) -> None:
    with pytest.raises(ValidationError):
        Settings(
            database_url="postgresql+asyncpg://u:p@localhost/db",
            otel_exporter_otlp_endpoint=endpoint,
        )


def test_tls_mode_must_match_exactly() -> None:
    with pytest.raises(ValidationError):
        Settings(
            database_url="postgresql+asyncpg://u:p@localhost/db?ssl=require-insecure",
            environment="production",
        )


def test_build_timestamp_normalized_to_utc() -> None:
    settings = Settings(
        database_url="postgresql+asyncpg://u:p@localhost/db",
        build_timestamp="2026-10-01T09:00:00-03:00",
    )
    assert settings.build_timestamp is not None and settings.build_timestamp.hour == 12
