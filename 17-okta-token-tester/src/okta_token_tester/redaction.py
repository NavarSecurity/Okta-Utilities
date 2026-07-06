from __future__ import annotations

import hashlib
from typing import Any


def fingerprint(value: str | None) -> str:
    if not value:
        return ""
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]


def redact_value(value: Any) -> Any:
    if isinstance(value, str):
        if not value:
            return value
        if len(value) <= 8:
            return "[REDACTED]"
        return f"[REDACTED:{fingerprint(value)}]"
    if isinstance(value, list):
        return [redact_value(item) for item in value]
    if isinstance(value, dict):
        return redact_dict(value)
    return value


def redact_dict(data: dict[str, Any]) -> dict[str, Any]:
    sensitive_markers = {"token", "secret", "authorization", "assertion", "code_verifier", "client_secret", "access_token", "id_token", "refresh_token"}
    result: dict[str, Any] = {}
    for key, value in data.items():
        lower = key.lower()
        if any(marker in lower for marker in sensitive_markers):
            result[key] = redact_value(value)
        elif isinstance(value, dict):
            result[key] = redact_dict(value)
        elif isinstance(value, list):
            result[key] = [redact_dict(item) if isinstance(item, dict) else item for item in value]
        else:
            result[key] = value
    return result
