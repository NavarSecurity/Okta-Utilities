from __future__ import annotations

from typing import Any

SENSITIVE_KEYS = {
    "authorization",
    "api_token",
    "apiToken",
    "client_secret",
    "clientSecret",
    "password",
    "secret",
    "token",
    "access_token",
    "refresh_token",
    "id_token",
    "assertion",
    "private_key",
    "privateKey",
}


def redact_value(value: Any) -> Any:
    if value in (None, ""):
        return value
    return "[REDACTED]"


def redact(data: Any) -> Any:
    if isinstance(data, dict):
        redacted: dict[str, Any] = {}
        for key, value in data.items():
            if key in SENSITIVE_KEYS or any(part in key.lower() for part in ["secret", "token", "password", "authorization"]):
                redacted[key] = redact_value(value)
            else:
                redacted[key] = redact(value)
        return redacted
    if isinstance(data, list):
        return [redact(item) for item in data]
    return data
