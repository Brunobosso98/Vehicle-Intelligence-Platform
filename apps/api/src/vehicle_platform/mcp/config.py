from typing import Literal
from urllib.parse import urlparse
from uuid import UUID

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class MCPSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="VIP_MCP_", hide_input_in_errors=True)
    host: str = "127.0.0.1"
    port: int = Field(default=8001, ge=1, le=65535)
    transport: Literal["stdio", "streamable-http"] = "stdio"
    token: SecretStr | None = None
    token_scope: str = "mcp:read"  # noqa: S105 - scope, not a credential
    token_expires_at: int | None = None
    prediction_evidence_enabled: bool = False
    prediction_token: SecretStr | None = None
    prediction_token_expires_at: int | None = None
    prediction_vehicle_ids: list[UUID] = Field(default_factory=list, max_length=64)
    issuer_url: str = "http://127.0.0.1:8001"
    resource_url: str = "http://127.0.0.1:8001/mcp"
    max_active_calls: int = Field(default=8, ge=1, le=32)
    execution_timeout: float = Field(default=10, gt=0, le=30)
    max_result_bytes: int = Field(default=524288, ge=1024, le=1048576)
    allow_docker_internal_host: bool = False

    @model_validator(mode="after")
    def secure_http(self) -> "MCPSettings":
        if "mcp:prediction-evidence:read" in self.token_scope.split():
            raise ValueError("Ordinary MCP read tokens cannot include prediction evidence scope")
        if self.transport == "streamable-http":
            if self.token is None or len(self.token.get_secret_value()) < 32:
                raise ValueError("HTTP requires an explicit token of at least 32 characters")
            if self.host not in {"localhost", "127.0.0.1", "::1", "0.0.0.0"}:  # noqa: S104
                raise ValueError("unsupported bind address")
            for address in (self.issuer_url, self.resource_url):
                parsed = urlparse(address)
                if parsed.scheme != "https" and parsed.hostname not in {
                    "localhost",
                    "127.0.0.1",
                    "::1",
                }:
                    raise ValueError("non-loopback public URLs require HTTPS")
        if self.prediction_evidence_enabled:
            if self.transport != "streamable-http":
                raise ValueError("Prediction evidence requires authenticated Streamable HTTP")
            if self.token is None or self.prediction_token is None:
                raise ValueError("Prediction evidence requires distinct ordinary and scoped tokens")
            ordinary = self.token.get_secret_value()
            predictive = self.prediction_token.get_secret_value()
            if len(predictive) < 43 or any(character.isspace() for character in predictive):
                raise ValueError("Prediction MCP token must be a high-entropy value")
            if ordinary == predictive:
                raise ValueError("Prediction MCP token must be distinct from ordinary MCP read")
            if not self.prediction_vehicle_ids:
                raise ValueError("Prediction MCP requires a selected-vehicle allowlist")
            if len(set(self.prediction_vehicle_ids)) != len(self.prediction_vehicle_ids):
                raise ValueError("Prediction vehicle allowlist must not contain duplicates")
        return self
