import hmac
from time import time

from mcp.server.auth.provider import AccessToken

from vehicle_platform.mcp.config import MCPSettings
from vehicle_platform.observability.telemetry import Telemetry


class ReadTokenVerifier:
    """Verify an operator-provisioned opaque token; never issue or forward tokens."""

    def __init__(self, settings: MCPSettings, telemetry: Telemetry) -> None:
        self.settings = settings
        self.failures = telemetry.metrics.get_meter("vehicle_platform.mcp").create_counter(
            "mcp.auth.failures"
        )

    async def verify_token(self, token: str) -> AccessToken | None:
        secret = self.settings.token
        expires = self.settings.token_expires_at
        if (
            secret is None
            or not hmac.compare_digest(token.encode(), secret.get_secret_value().encode())
            or (expires is not None and expires <= time())
        ):
            self.failures.add(1, {"reason": "invalid_or_expired"})
            return None
        scopes = self.settings.token_scope.split()
        if "mcp:read" not in scopes:
            self.failures.add(1, {"reason": "insufficient_scope"})
        return AccessToken(
            token=token,
            client_id="provisioned-reader",
            scopes=scopes,
            expires_at=expires,
            resource=self.settings.resource_url,
        )
