from datetime import UTC, datetime
from typing import Literal
from urllib.parse import parse_qs, urlparse

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", hide_input_in_errors=True)
    environment: Literal["development", "test", "production"] = "development"
    database_url: SecretStr
    app_version: str = Field(default="0.1.0", min_length=1)
    git_sha: str | None = None
    build_timestamp: datetime | None = None
    readiness_timeout: float = Field(default=2.0, gt=0, le=30)
    otel_exporter_otlp_endpoint: str | None = None
    kafka_bootstrap_servers: str = Field(default="broker:9092", min_length=1, max_length=255)
    acquisition_token_ttl_seconds: int = Field(default=3600, ge=60, le=86400)
    acquisition_batch_limit: int = Field(default=500, ge=1, le=5000)

    @field_validator("git_sha", "build_timestamp", mode="before")
    @classmethod
    def optional_metadata(cls, value: object) -> object:
        return None if value == "" else value

    @field_validator("database_url")
    @classmethod
    def postgres_url(cls, value: SecretStr) -> SecretStr:
        parsed = urlparse(value.get_secret_value())
        if (
            parsed.scheme != "postgresql+asyncpg"
            or not parsed.hostname
            or not parsed.path.strip("/")
        ):
            raise ValueError("DATABASE_URL must be a PostgreSQL asyncpg URL with host and database")
        return value

    @field_validator("build_timestamp")
    @classmethod
    def aware_timestamp(cls, value: datetime | None) -> datetime | None:
        if value is not None and value.utcoffset() is None:
            raise ValueError("BUILD_TIMESTAMP must include a timezone")
        return value.astimezone(UTC) if value is not None else None

    @field_validator("otel_exporter_otlp_endpoint")
    @classmethod
    def otlp_url(cls, value: str | None) -> str | None:
        if value is not None:
            url = urlparse(value)
            if (
                url.scheme not in {"http", "https"}
                or not url.hostname
                or url.username
                or url.password
            ):
                raise ValueError("OTLP endpoint must be HTTP(S) with host and no credentials")
        return value

    @model_validator(mode="after")
    def production(self) -> "Settings":
        if self.environment == "production":
            url = urlparse(self.database_url.get_secret_value())
            if not url.password or url.password in {"local-development-only", "changeme"}:
                raise ValueError("Production requires explicit database credentials")
            if parse_qs(url.query).get("ssl") not in [["require"], ["verify-full"]]:
                raise ValueError("Production database requires TLS")
        return self
