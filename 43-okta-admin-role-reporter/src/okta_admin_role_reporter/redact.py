from __future__ import annotations

from typing import Any

SENSITIVE_KEYS = {
    "token",
    "apiToken",
    "accessToken",
    "refreshToken",
    "client_secret",
    "clientSecret",
    "secret",
    "password",
    "credentials",
    "authorization",
    "Authorization",
    "privateKey",
    "key",
}


def redact_value(value: Any) -> Any:
    if isinstance(value, dict):
        result: dict[str, Any] = {}
        for key, child in value.items():
            if key in SENSITIVE_KEYS or any(term in key.lower() for term in ["secret", "token", "password", "authorization"]):
                result[key] = "***REDACTED***"
            else:
                result[key] = redact_value(child)
        return result
    if isinstance(value, list):
        return [redact_value(item) for item in value]
    return value
