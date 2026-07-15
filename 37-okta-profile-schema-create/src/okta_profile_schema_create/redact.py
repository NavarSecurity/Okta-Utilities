from __future__ import annotations

from copy import deepcopy
from typing import Any

SENSITIVE_KEYS = {
    "token",
    "apiToken",
    "api_token",
    "client_secret",
    "clientSecret",
    "password",
    "secret",
    "authorization",
    "privateKey",
    "private_key",
}


def redact(value: Any) -> Any:
    if isinstance(value, dict):
        result: dict[str, Any] = {}
        for key, item in value.items():
            if key in SENSITIVE_KEYS or key.lower() in {k.lower() for k in SENSITIVE_KEYS}:
                result[key] = "REDACTED"
            else:
                result[key] = redact(item)
        return result
    if isinstance(value, list):
        return [redact(item) for item in value]
    return deepcopy(value)
