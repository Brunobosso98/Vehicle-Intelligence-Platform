from typing import Any, Literal
from urllib.parse import urlparse

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class AgentSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="VIP_AGENT_", hide_input_in_errors=True)
    enabled: bool = False
    provider: Literal["openai", "deterministic"] = "openai"
    model: str = Field(default="", max_length=100)
    api_key: SecretStr | None = None
    mcp_url: str = "http://127.0.0.1:8001/mcp"
    mcp_token: SecretStr | None = None
    investigation_token: SecretStr | None = None
    max_steps: int = Field(default=16, ge=2, le=32)
    max_tool_calls: int = Field(default=32, ge=4, le=32)
    max_telemetry_calls: int = Field(default=1, ge=0, le=2)
    max_comparisons: int = Field(default=3, ge=0, le=5)
    run_timeout: float = Field(default=90, gt=0, le=180)
    model_timeout: float = Field(default=30, gt=0, le=60)
    tool_timeout: float = Field(default=12, gt=0, le=30)
    max_concurrent_runs: int = Field(default=4, ge=1, le=8)
    max_result_bytes: int = Field(default=131072, ge=1024, le=262144)
    max_input_bytes: int = Field(default=262144, ge=4096, le=524288)
    max_output_bytes: int = Field(default=32768, ge=1024, le=65536)
    max_evidence: int = Field(default=80, ge=4, le=100)
    max_provider_retries: int = Field(default=1, ge=0, le=2)
    max_grounding_retries: int = Field(default=1, ge=0, le=2)
    agent_version: str = "phase7a-v1"
    prompt_version: str = "grounded-v1"

    @model_validator(mode="after")
    def valid_runtime(self) -> "AgentSettings":
        parsed = urlparse(self.mcp_url)
        if (
            parsed.scheme not in {"http", "https"}
            or not parsed.hostname
            or parsed.username
            or parsed.password
            or parsed.query
            or parsed.fragment
            or (
                parsed.scheme == "http"
                and parsed.hostname not in {"localhost", "127.0.0.1", "::1", "mcp"}
            )
        ):
            raise ValueError("MCP requires a fixed operator URL with TLS or a local endpoint")
        if self.enabled and self.provider == "openai" and (not self.api_key or not self.model):
            raise ValueError("Enabled OpenAI agent requires VIP_AGENT_API_KEY and VIP_AGENT_MODEL")
        if self.enabled and not self.mcp_token:
            raise ValueError("Enabled agent requires VIP_AGENT_MCP_TOKEN")
        return self


def redact_data(value: Any, settings: AgentSettings) -> Any:
    """Redact only strings, preserving numeric facts and JSON structure."""
    if isinstance(value, str):
        for secret in (settings.api_key, settings.mcp_token, settings.investigation_token):
            if secret and secret.get_secret_value():
                value = value.replace(secret.get_secret_value(), "[redacted]")
        return value
    if isinstance(value, list):
        return [redact_data(item, settings) for item in value]
    if isinstance(value, dict):
        return {
            redact_data(key, settings): redact_data(item, settings) for key, item in value.items()
        }
    return value
