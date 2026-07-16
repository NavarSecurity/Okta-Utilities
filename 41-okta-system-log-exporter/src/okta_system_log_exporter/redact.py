from __future__ import annotations

from copy import deepcopy
from typing import Any

SENSITIVE_KEYWORDS = (
    "authorization",
    "access_token",
    "refresh_token",
    "id_token",
    "token",
    "secret",
    "password",
    "credential",
    "privatekey",
    "private_key",
    "cookie",
    "set-cookie",
    "apikey",
    "api_key",
    "client_secret",
    "bearer",
)

REDACTED = "***REDACTED***"


def is_sensitive_key(key: str) -> bool:
    lowered = key.lower().replace("-", "_")
    return any(keyword in lowered for keyword in SENSITIVE_KEYWORDS)


def redact_value(value: Any) -> Any:
    if isinstance(value, dict):
        result = {}
        for key, item in value.items():
            if is_sensitive_key(str(key)):
                result[key] = REDACTED
            else:
                result[key] = redact_value(item)
        return result
    if isinstance(value, list):
        return [redact_value(item) for item in value]
    return value


def redact_event(event: dict[str, Any]) -> dict[str, Any]:
    return redact_value(deepcopy(event))
