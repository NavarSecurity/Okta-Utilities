from __future__ import annotations

import copy
import re
from typing import Any

SENSITIVE_KEYS = {
    "phoneNumber",
    "phone_number",
    "passCode",
    "passcode",
    "sharedSecret",
    "secret",
    "token",
    "credentialId",
    "deviceToken",
}

PHONE_RE = re.compile(r"\+?\d[\d\s().-]{6,}\d")


def redact_value(key: str, value: Any) -> Any:
    if value is None:
        return None
    if key in SENSITIVE_KEYS:
        return "[REDACTED]"
    if isinstance(value, str) and PHONE_RE.fullmatch(value.strip()):
        return "[REDACTED]"
    return value


def redact_object(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {key: redact_value(key, redact_object(value)) for key, value in obj.items()}
    if isinstance(obj, list):
        return [redact_object(item) for item in obj]
    return obj


def maybe_redact(obj: Any, enabled: bool) -> Any:
    if not enabled:
        return obj
    return redact_object(copy.deepcopy(obj))
