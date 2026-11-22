"""Redact sensitive run output before it is written to evaluation receipts."""

from typing import Any

from vehicle_platform.agent_evaluation.contracts import AttemptStatus, CaseAttempt


def redact_runtime_secrets(value: str, environment: dict[str, str]) -> str:
    """Remove configured credentials and the disposable database URL from logs."""
    secrets = {
        secret
        for key, secret in environment.items()
        if secret and (key.endswith(("TOKEN", "KEY", "PASSWORD")) or key == "DATABASE_URL")
    }
    for secret in sorted(secrets, key=len, reverse=True):
        value = value.replace(secret, "[redacted]")
    return value


def _contains_secret(value: Any, secrets: tuple[str, ...]) -> bool:
    if isinstance(value, str):
        return any(secret in value for secret in secrets)
    if isinstance(value, dict):
        return any(_contains_secret(item, secrets) for item in value.values())
    if isinstance(value, (list, tuple)):
        return any(_contains_secret(item, secrets) for item in value)
    return False


def sanitize_attempt(attempt: CaseAttempt, secrets: tuple[str, ...]) -> CaseAttempt:
    """Drop captured model/source payloads if they contain a configured secret."""
    configured = tuple(secret for secret in secrets if len(secret) >= 8)
    captured = (attempt.answer_text, attempt.findings, attempt.evidence)
    if not configured or not _contains_secret(captured, configured):
        return attempt
    return attempt.model_copy(
        update={
            "status": AttemptStatus.ASSERTION_FAIL,
            "answer_text": "",
            "findings": (),
            "evidence": (),
            "reasons": tuple(dict.fromkeys((*attempt.reasons, "secret_disclosure_detected"))),
            "error_category": "sensitive_output_redacted",
        }
    )
