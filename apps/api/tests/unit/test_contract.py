from vehicle_platform.core.config import Settings
from vehicle_platform.main import create_app


def test_openapi_schema(settings: Settings) -> None:
    app = create_app(settings)
    schema = app.openapi()
    assert schema["openapi"] == "3.1.0"
    assert {
        "/health/live",
        "/health/ready",
        "/version",
        "/api/v1/vehicles",
        "/api/v1/sessions",
        "/api/v1/signals",
        "/api/v1/sessions/{session_id}/telemetry",
    } <= set(schema["paths"])
    assert schema["paths"]["/health/ready"]["get"]["responses"]["503"]["content"][
        "application/json"
    ]["schema"]["$ref"].endswith("ErrorResponse")
    assert schema["components"]["schemas"]["ErrorDetail"]["required"] == [
        "code",
        "message",
        "request_id",
    ]
    app.state.telemetry.shutdown()
