from typing import Literal
from urllib.parse import urlparse

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
    issuer_url: str = "http://127.0.0.1:8001"
    resource_url: str = "http://127.0.0.1:8001/mcp"
    max_active_calls: int = Field(default=8, ge=1, le=32)
    execution_timeout: float = Field(default=10, gt=0, le=30)
    max_result_bytes: int = Field(default=524288, ge=1024, le=1048576)
    allow_docker_internal_host: bool = False

    @model_validator(mode="after")
    def secure_http(self) -> "MCPSettings":
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
        return self
