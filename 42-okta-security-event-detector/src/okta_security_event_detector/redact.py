from __future__ import annotations

import copy
import re
from typing import Any

SENSITIVE_KEYS = {
    "authorization",
    "cookie",
    "token",
    "access_token",
    "refresh_token",
    "id_token",
    "client_secret",
    "password",
    "secret",
    "apikey",
    "api_key",
}

TOKEN_PATTERNS = [
    re.compile(r"SSWS\s+[A-Za-z0-9._\-]+", re.IGNORECASE),
    re.compile(r"Bearer\s+[A-Za-z0-9._\-]+", re.IGNORECASE),
]


def redact_value(value: Any) -> Any:
    if isinstance(value, str):
        redacted = value
        for pattern in TOKEN_PATTERNS:
            redacted = pattern.sub("[REDACTED]", redacted)
        return redacted
    return value


def redact_obj(value: Any) -> Any:
    copied = copy.deepcopy(value)
    return _redact(copied)


def _redact(value: Any) -> Any:
    if isinstance(value, dict):
        result = {}
        for key, item in value.items():
            normalized_key = key.lower().replace("-", "_")
            if normalized_key in SENSITIVE_KEYS or any(part in normalized_key for part in ["secret", "token", "password"]):
                result[key] = "[REDACTED]"
            else:
                result[key] = _redact(item)
        return result
    if isinstance(value, list):
        return [_redact(item) for item in value]
    return redact_value(value)
