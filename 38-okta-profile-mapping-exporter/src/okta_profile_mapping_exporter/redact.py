from __future__ import annotations

from typing import Any

SENSITIVE_KEYS = {
    "authorization",
    "api_token",
    "apikey",
    "apiKey",
    "client_secret",
    "clientSecret",
    "credential",
    "credentials",
    "key",
    "password",
    "privateKey",
    "secret",
    "token",
}


def redact_value(value: Any) -> Any:
    if isinstance(value, dict):
        redacted: dict[str, Any] = {}
        for key, item in value.items():
            if key in SENSITIVE_KEYS or any(term in key.lower() for term in ["secret", "token", "password", "private"]):
                redacted[key] = "[REDACTED]"
            else:
                redacted[key] = redact_value(item)
        return redacted
    if isinstance(value, list):
        return [redact_value(item) for item in value]
    return value
