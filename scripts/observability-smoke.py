"""Verify live HTTP correlation and request metrics; OTLP/log proof has separate tests/runbook."""

import urllib.request

base = "http://127.0.0.1:8000"
request = urllib.request.Request(
    base + "/health/live", headers={"X-Request-ID": "observability-smoke"}
)
with urllib.request.urlopen(request, timeout=3) as response:
    assert response.headers["X-Request-ID"] == "observability-smoke"
with urllib.request.urlopen(base + "/metrics", timeout=3) as response:
    assert b"http_server_requests_total" in response.read()
print("Real HTTP response correlation and OTel request metric verified.")
print(
    "OTLP delivery and JSON log correlation: use runbook or unit exporter capture; see completion report."
)
