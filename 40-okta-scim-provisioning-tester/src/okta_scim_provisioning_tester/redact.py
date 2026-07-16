from __future__ import annotations

from copy import deepcopy
from typing import Any

SENSITIVE_KEYS = {
    "authorization",
    "bearer",
    "token",
    "access_token",
    "password",
    "secret",
    "client_secret",
    "api_key",
    "apikey",
}


def redact_value(value: Any) -> Any:
    if value is None:
        return None
    return "***REDACTED***"


def redact(data: Any) -> Any:
    if isinstance(data, dict):
        result = {}
        for key, value in data.items():
            normalized = str(key).lower()
            if any(sensitive in normalized for sensitive in SENSITIVE_KEYS):
                result[key] = redact_value(value)
            else:
                result[key] = redact(value)
        return result
    if isinstance(data, list):
        return [redact(item) for item in data]
    return data


def redact_copy(data: Any) -> Any:
    return redact(deepcopy(data))
