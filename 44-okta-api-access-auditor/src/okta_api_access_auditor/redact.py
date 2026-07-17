from __future__ import annotations

from copy import deepcopy
from typing import Any

SENSITIVE_KEYS = {
    "access_token",
    "api_token",
    "apikey",
    "apiKey",
    "authorization",
    "client_secret",
    "clientSecret",
    "credentials",
    "password",
    "private_key",
    "privateKey",
    "secret",
    "token",
}


def redact_value(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, str):
        if len(value) <= 8:
            return "***REDACTED***"
        return f"{value[:4]}...{value[-4:]}"
    return "***REDACTED***"


def redact(data: Any) -> Any:
    item = deepcopy(data)
    return _redact_in_place(item)


def _redact_in_place(value: Any) -> Any:
    if isinstance(value, dict):
        for key in list(value.keys()):
            if key in SENSITIVE_KEYS or key.lower() in {k.lower() for k in SENSITIVE_KEYS}:
                value[key] = redact_value(value[key])
            else:
                value[key] = _redact_in_place(value[key])
        return value
    if isinstance(value, list):
        return [_redact_in_place(v) for v in value]
    return value
