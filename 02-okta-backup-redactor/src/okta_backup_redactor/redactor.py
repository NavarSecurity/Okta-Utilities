from __future__ import annotations

import math
import re
from copy import deepcopy
from typing import Any

from .config import RedactorConfig
from .models import RedactionFinding

REDACTED_VALUES = {"[REDACTED]", "REDACTED", "<REDACTED>", "***", ""}

# Normalized exact key names only. Avoid substring matching so normal Okta
# structural keys like authorizationServers and passwordChange are preserved.
SECRET_KEYS_EXACT = {
    "apitoken",
    "apikey",
    "apikeyvalue",
    "token",
    "accesstoken",
    "refreshtoken",
    "idtoken",
    "bearertoken",
    "clientsecret",
    "sharedsecret",
    "privatekey",
    "privatekeypem",
    "publicprivatekeypair",
    "signingkey",
    "encryptionkey",
    "secret",
    "password",
    "passwd",
    "pwd",
    "authorization",
    "xapikey",
    "apikeyheader",
}

# These exact keys contain words like token/password/authorization but are normal
# Okta config structures or non-secret settings.
SAFE_KEYS_EXACT = {
    "authorizationservers",
    "detailsbyauthorizationserverid",
    "passwordchange",
    "selfservicepasswordreset",
    "recoverytoken",
    "tokenlifetimeminutes",
    "oktapassword",
    "policytypes",
}

PRIVATE_KEY_RE = re.compile(
    r"-----BEGIN (?:RSA |EC |OPENSSH |DSA |ENCRYPTED )?PRIVATE KEY-----.*?-----END (?:RSA |EC |OPENSSH |DSA |ENCRYPTED )?PRIVATE KEY-----",
    re.DOTALL,
)
BEARER_RE = re.compile(r"^\s*Bearer\s+\S+", re.IGNORECASE)
SSWS_RE = re.compile(r"^\s*SSWS\s+\S+", re.IGNORECASE)
BASIC_RE = re.compile(r"^\s*Basic\s+[A-Za-z0-9+/=]+", re.IGNORECASE)
JWT_RE = re.compile(r"^[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{10,}$")


def normalize_key(key: str | None) -> str:
    if key is None:
        return ""
    return re.sub(r"[^a-z0-9]", "", str(key).lower())


def format_path(parts: list[str | int]) -> str:
    out = "$"
    for p in parts:
        if isinstance(p, int):
            out += f"[{p}]"
        else:
            # Use bracket notation for keys that contain punctuation.
            if re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", p):
                out += f".{p}"
            else:
                out += "[" + repr(p) + "]"
    return out


def preview_value(value: Any, max_chars: int = 160) -> str:
    if value is None:
        return "null"
    if isinstance(value, (dict, list)):
        text = f"<{type(value).__name__} length={len(value)}>"
    else:
        text = str(value)
    if len(text) > max_chars:
        return text[: max_chars - 3] + "..."
    return text


def is_already_redacted(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str) and value.strip().upper() in {v.upper() for v in REDACTED_VALUES}:
        return True
    return False


def is_safe_password_policy_path(parts: list[str | int]) -> bool:
    """Preserve Okta password policy structures and configuration blocks.

    Okta password policy settings commonly appear under a path like:
    $.policyTypes.PASSWORD.policies[0].settings.password
    That key is named "password" but contains password policy configuration,
    not an actual user/app secret. Redacting the whole block breaks backup
    completeness, validation, diff, and migration planning.
    """
    string_parts = [p for p in parts if isinstance(p, str)]
    if len(string_parts) >= 2 and string_parts[-2:] == ["policyTypes", "PASSWORD"]:
        return True
    return (
        "policyTypes" in string_parts
        and "PASSWORD" in string_parts
        and "settings" in string_parts
        and string_parts[-1] == "password"
    )


def looks_high_entropy(value: str) -> bool:
    if len(value) < 32:
        return False
    charset = set(value)
    if len(charset) < 12:
        return False
    counts = {c: value.count(c) for c in charset}
    entropy = -sum((n / len(value)) * math.log2(n / len(value)) for n in counts.values())
    return entropy >= 4.2


def should_redact_value(key: str | None, value: Any, parts: list[str | int], cfg: RedactorConfig) -> tuple[bool, str | None]:
    if is_already_redacted(value):
        return False, None

    key_norm = normalize_key(key)
    path = format_path(parts)

    if key_norm in SAFE_KEYS_EXACT:
        return False, None

    if is_safe_password_policy_path(parts):
        return False, None

    if cfg.redact_known_secret_keys and key_norm in SECRET_KEYS_EXACT:
        # Do not redact empty booleans/numbers for accidentally named keys.
        if isinstance(value, (dict, list)) or isinstance(value, str) or value is not None:
            return True, f"Sensitive key name: {key}"

    if isinstance(value, str):
        if cfg.redact_private_key_blocks and PRIVATE_KEY_RE.search(value):
            return True, "Private key block"
        if cfg.redact_bearer_values and (BEARER_RE.match(value) or SSWS_RE.match(value) or BASIC_RE.match(value)):
            return True, "Authorization credential value"
        if cfg.redact_known_secret_keys and JWT_RE.match(value) and key_norm in {"token", "accesstoken", "refreshtoken", "idtoken", "assertion"}:
            return True, "JWT-like token value"
        if cfg.redact_high_entropy_values and looks_high_entropy(value):
            # Skip URLs and Okta resource identifiers in high entropy mode.
            if value.startswith(("http://", "https://")):
                return False, None
            if re.match(r"^(00|0o|0p|0g|0pr|aus|bnd|uis|rul)[A-Za-z0-9_-]{8,}$", value):
                return False, None
            return True, "High-entropy value"

    return False, None


def redact_json(data: Any, *, file_name: str, cfg: RedactorConfig) -> tuple[Any, list[RedactionFinding]]:
    findings: list[RedactionFinding] = []
    redacted = deepcopy(data)

    def walk(node: Any, parts: list[str | int], key: str | None = None) -> Any:
        should, reason = should_redact_value(key, node, parts, cfg)
        if should:
            findings.append(
                RedactionFinding(
                    file=file_name,
                    path=format_path(parts),
                    key=key,
                    reason=reason or "Sensitive value",
                    value_preview=preview_value(node, cfg.max_value_preview_chars),
                    value_type=type(node).__name__,
                )
            )
            return cfg.replacement

        if isinstance(node, dict):
            out: dict[str, Any] = {}
            for child_key, child_value in node.items():
                out[child_key] = walk(child_value, [*parts, str(child_key)], str(child_key))
            return out
        if isinstance(node, list):
            return [walk(item, [*parts, idx], None) for idx, item in enumerate(node)]
        return node

    return walk(redacted, []), findings
