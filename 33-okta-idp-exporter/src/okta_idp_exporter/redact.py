from __future__ import annotations

from copy import deepcopy
from typing import Any

from .config import RedactionConfig


EXPLICIT_SECRET_PATH_KEYWORDS = {
    "client_secret",
    "clientsecret",
    "sharedsecret",
    "shared_secret",
    "privatekey",
    "private_key",
    "passphrase",
    "password",
    "token",
    "authorization",
    "assertion",
}


def key_is_sensitive(key: str, config: RedactionConfig) -> bool:
    normalized = key.replace("-", "_").replace(" ", "_").lower()
    compact = normalized.replace("_", "")
    if normalized in EXPLICIT_SECRET_PATH_KEYWORDS or compact in EXPLICIT_SECRET_PATH_KEYWORDS:
        return True
    return any(fragment in normalized for fragment in config.redact_key_names_containing)


def redact_value(value: Any, redaction_config: RedactionConfig) -> Any:
    if isinstance(value, dict):
        redacted: dict[str, Any] = {}
        for key, child in value.items():
            if key_is_sensitive(str(key), redaction_config):
                if child in (None, ""):
                    redacted[key] = child
                else:
                    redacted[key] = redaction_config.replacement
            else:
                redacted[key] = redact_value(child, redaction_config)
        return redacted
    if isinstance(value, list):
        return [redact_value(item, redaction_config) for item in value]
    return value


def strip_links(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: strip_links(child) for key, child in value.items() if key != "_links"}
    if isinstance(value, list):
        return [strip_links(item) for item in value]
    return value


def prepare_export_object(value: Any, *, include_links: bool, redact_sensitive: bool, redaction_config: RedactionConfig) -> Any:
    prepared = deepcopy(value)
    if not include_links:
        prepared = strip_links(prepared)
    if redact_sensitive:
        prepared = redact_value(prepared, redaction_config)
    return prepared
