from __future__ import annotations

import re
from typing import Any

REDACTED = "[REDACTED]"

SENSITIVE_KEY_RE = re.compile(
    r"^(client[_-]?secret|api[_-]?token|access[_-]?token|refresh[_-]?token|id[_-]?token|"
    r"password|passcode|private[_-]?key|shared[_-]?secret|assertion[_-]?secret|"
    r"webhook[_-]?secret|authorization|bearer|secret|token)$",
    re.IGNORECASE,
)

SENSITIVE_QUERY_RE = re.compile(
    r"(?i)(client_secret|api_token|access_token|refresh_token|id_token|password|secret|token)=([^&\s]+)"
)

SENSITIVE_HEADER_NAMES = {
    "authorization",
    "proxy-authorization",
    "x-api-key",
    "api-key",
    "apikey",
    "x-okta-token",
}

OKTA_POLICY_TYPE_KEYS = {
    "OKTA_SIGN_ON",
    "PASSWORD",
    "MFA_ENROLL",
    "IDP_DISCOVERY",
    "PROFILE_ENROLLMENT",
}


def redact_sensitive_values(value: Any) -> Any:
    """Recursively redact common secret-bearing values before writing backup output.

    The redactor is path-aware so Okta structural enum keys are preserved. For example,
    policies.json stores password policies under policyTypes.PASSWORD. That key is an
    Okta policy type, not a password secret, so the policy section must remain intact.
    """
    return _redact_sensitive_values(value, path=())


def _redact_sensitive_values(value: Any, path: tuple[str, ...]) -> Any:
    if isinstance(value, list):
        return [_redact_sensitive_values(item, path=path) for item in value]

    if isinstance(value, dict):
        redacted: dict[str, Any] = {}
        header_key = str(value.get("key", "")).lower() if "key" in value else None

        for key, item in value.items():
            key_text = str(key)
            lower_key = key_text.lower()

            if _is_okta_policy_type_container_key(key_text, item, path):
                redacted[key] = _redact_sensitive_values(item, path=path + (key_text,))
                continue

            if SENSITIVE_KEY_RE.search(key_text):
                redacted[key] = REDACTED
                continue

            # Okta hooks may store authorization headers as {"key": "Authorization", "value": "Bearer ..."}.
            if lower_key == "value" and header_key in SENSITIVE_HEADER_NAMES:
                redacted[key] = REDACTED
                continue

            redacted[key] = _redact_sensitive_values(item, path=path + (key_text,))
        return redacted

    if isinstance(value, str):
        return redact_string(value)

    return value


def _is_okta_policy_type_container_key(key_text: str, item: Any, path: tuple[str, ...]) -> bool:
    """Return True when a key named PASSWORD is an Okta policy type, not a secret.

    The backup shape for policies is:

        {"policyTypes": {"PASSWORD": {"policies": [...], "rulesByPolicyId": {...}}}}

    The old redactor treated the key PASSWORD as a sensitive password field and replaced
    the entire section with [REDACTED]. That made policy backups incomplete and caused
    validator count mismatches. This allow-list only applies to the exact policyTypes
    container and only when the value has the expected policy-record shape.
    """
    if not path or path[-1] != "policyTypes":
        return False
    if key_text not in OKTA_POLICY_TYPE_KEYS:
        return False
    if not isinstance(item, dict):
        return False
    return any(field in item for field in ("policies", "rulesByPolicyId", "errors"))


def redact_string(value: str) -> str:
    if not value:
        return value
    return SENSITIVE_QUERY_RE.sub(lambda match: f"{match.group(1)}={REDACTED}", value)
