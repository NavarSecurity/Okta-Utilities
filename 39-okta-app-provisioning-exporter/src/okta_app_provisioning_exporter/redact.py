from __future__ import annotations

from typing import Any

SENSITIVE_KEY_PARTS = [
    "token", "secret", "password", "privatekey", "private_key", "clientsecret",
    "client_secret", "authorization", "authheader", "auth_header", "apikey", "api_key",
    "bearer", "credential"
]


def is_sensitive_key(key: str) -> bool:
    normalized = key.replace("-", "_").replace(" ", "_").lower()
    return any(part in normalized for part in SENSITIVE_KEY_PARTS)


def redact_value(value: Any) -> str:
    if value in (None, ""):
        return ""
    return "[REDACTED]"


def redact_object(obj: Any) -> Any:
    if isinstance(obj, dict):
        result = {}
        for key, value in obj.items():
            if is_sensitive_key(str(key)):
                result[key] = redact_value(value)
            else:
                result[key] = redact_object(value)
        return result
    if isinstance(obj, list):
        return [redact_object(item) for item in obj]
    return obj
