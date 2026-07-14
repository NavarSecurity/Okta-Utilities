from __future__ import annotations

from copy import deepcopy
from typing import Any

SENSITIVE_KEYS = {
    "apiToken",
    "api_token",
    "token",
    "accessToken",
    "client_secret",
    "clientSecret",
    "password",
    "secret",
    "privateKey",
    "authorization",
    "Authorization",
}


def redact_value(value: Any) -> Any:
    if isinstance(value, dict):
        return redact_object(value)
    if isinstance(value, list):
        return [redact_value(item) for item in value]
    return value


def redact_object(obj: dict[str, Any]) -> dict[str, Any]:
    copied = deepcopy(obj)
    for key, value in list(copied.items()):
        if key in SENSITIVE_KEYS or any(token in key.lower() for token in ["secret", "token", "password", "privatekey"]):
            copied[key] = "REDACTED"
        else:
            copied[key] = redact_value(value)
    return copied
