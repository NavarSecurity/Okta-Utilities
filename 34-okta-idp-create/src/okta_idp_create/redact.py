from __future__ import annotations

from copy import deepcopy
from typing import Any

SENSITIVE_KEY_PARTS = {
    "token",
    "secret",
    "password",
    "privatekey",
    "private_key",
    "apikey",
    "api_key",
    "authorization",
    "access_token",
    "refresh_token",
    "assertion",
}

SENSITIVE_EXACT_KEYS = {
    "client_secret",
    "clientSecret",
    "privateKey",
    "private_key",
    "apiToken",
    "api_token",
}

REDACTION = "***REDACTED***"


def _is_sensitive_key(key: str) -> bool:
    normalized = key.replace("-", "_").lower()
    if key in SENSITIVE_EXACT_KEYS or normalized in SENSITIVE_EXACT_KEYS:
        return True
    return any(part in normalized for part in SENSITIVE_KEY_PARTS)


def redact_value(value: Any, parent_key: str = "") -> Any:
    if isinstance(value, dict):
        redacted: dict[str, Any] = {}
        for key, item in value.items():
            if _is_sensitive_key(str(key)):
                redacted[key] = REDACTION
            else:
                redacted[key] = redact_value(item, str(key))
        return redacted
    if isinstance(value, list):
        return [redact_value(item, parent_key) for item in value]
    if parent_key and _is_sensitive_key(parent_key):
        return REDACTION
    return value


def redact_object(data: Any) -> Any:
    return redact_value(deepcopy(data))
