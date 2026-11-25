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
        return any(
            _contains_secret(key, secrets) or _contains_secret(item, secrets)
            for key, item in value.items()
        )
    if isinstance(value, (list, tuple)):
        return any(_contains_secret(item, secrets) for item in value)
    return False


def _redact(value: Any, secrets: tuple[str, ...]) -> Any:
    if isinstance(value, str):
        for secret in sorted(secrets, key=len, reverse=True):
            value = value.replace(secret, "[redacted]")
        return value
    if isinstance(value, dict):
        return {_redact(key, secrets): _redact(item, secrets) for key, item in value.items()}
    if isinstance(value, tuple):
        return tuple(_redact(item, secrets) for item in value)
    if isinstance(value, list):
        return [_redact(item, secrets) for item in value]
    return value


def sanitize_attempt(attempt: CaseAttempt, secrets: tuple[str, ...]) -> CaseAttempt:
    """Redact configured secrets from every attempt field before receipt persistence."""
    configured = tuple(secret for secret in secrets if len(secret) >= 8)
    if not configured:
        return attempt
    payload = attempt.model_dump(mode="python")
    if not _contains_secret(payload, configured):
        return attempt

    redacted = _redact(payload, configured)
    redacted.update(
        {
            "status": AttemptStatus.ASSERTION_FAIL,
            "answer_text": "",
            "findings": (),
            "evidence": (),
            "reasons": tuple(dict.fromkeys((*redacted["reasons"], "secret_disclosure_detected"))),
            "error_category": "sensitive_output_redacted",
        }
    )
    return CaseAttempt.model_validate(redacted)
