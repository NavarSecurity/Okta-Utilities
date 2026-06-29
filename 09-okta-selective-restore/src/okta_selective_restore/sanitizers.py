from __future__ import annotations

import copy
from typing import Any

SENSITIVE_KEYS = {
    "access_token",
    "api_token",
    "apiToken",
    "authorization",
    "client_secret",
    "clientSecret",
    "hookKey",
    "password",
    "privateKey",
    "refresh_token",
    "secret",
    "sharedSecret",
    "token",
}

READ_ONLY_KEYS = {
    "id",
    "_links",
    "created",
    "lastUpdated",
    "lastMembershipUpdated",
    "activated",
    "published",
    "objectClass",
}

REDACTION_MARKERS = {"[REDACTED]", "***REDACTED***", "REDACTED", "<redacted>"}


def _strip_keys(obj: Any, keys_to_strip: set[str]) -> Any:
    if isinstance(obj, dict):
        result: dict[str, Any] = {}
        for key, value in obj.items():
            if key in keys_to_strip:
                continue
            result[key] = _strip_keys(value, keys_to_strip)
        return result
    if isinstance(obj, list):
        return [_strip_keys(item, keys_to_strip) for item in obj]
    return obj


def _strip_sensitive(obj: Any) -> Any:
    if isinstance(obj, dict):
        result: dict[str, Any] = {}
        for key, value in obj.items():
            if key in SENSITIVE_KEYS:
                continue
            result[key] = _strip_sensitive(value)
        return result
    if isinstance(obj, list):
        return [_strip_sensitive(item) for item in obj]
    if isinstance(obj, str) and obj.strip() in REDACTION_MARKERS:
        return None
    return obj


def sanitize_group(source: dict[str, Any]) -> dict[str, Any]:
    profile = copy.deepcopy(source.get("profile") or {})
    return {
        "profile": {
            "name": profile.get("name"),
            "description": profile.get("description", "Restored by okta-selective-restore"),
        }
    }


def sanitize_application(source: dict[str, Any]) -> dict[str, Any]:
    payload = copy.deepcopy(source)
    payload = _strip_keys(payload, READ_ONLY_KEYS)
    payload = _strip_sensitive(payload)
    payload.pop("status", None)
    # OAuth client secrets, signing credentials, and hook-style sensitive values are not restored.
    credentials = payload.get("credentials")
    if isinstance(credentials, dict):
        oauth_client = credentials.get("oauthClient")
        if isinstance(oauth_client, dict):
            oauth_client.pop("client_secret", None)
            oauth_client.pop("clientSecret", None)
        signing = credentials.get("signing")
        if isinstance(signing, dict):
            signing.pop("kid", None)
            signing.pop("cert", None)
            signing.pop("key", None)
    return payload


def sanitize_trusted_origin(source: dict[str, Any]) -> dict[str, Any]:
    payload = copy.deepcopy(source)
    payload = _strip_keys(payload, READ_ONLY_KEYS)
    payload = _strip_sensitive(payload)
    payload.pop("status", None)
    return payload


def sanitize_network_zone(source: dict[str, Any]) -> dict[str, Any]:
    payload = copy.deepcopy(source)
    payload = _strip_keys(payload, READ_ONLY_KEYS | {"system"})
    payload = _strip_sensitive(payload)
    payload.pop("status", None)
    return payload


def sanitize_authorization_server(source: dict[str, Any]) -> dict[str, Any]:
    payload = copy.deepcopy(source)
    payload = _strip_keys(payload, READ_ONLY_KEYS | {"issuer", "issuerMode"})
    payload = _strip_sensitive(payload)
    payload.pop("status", None)
    # Backup exporters may later attach child resources. Those are not valid in the base create payload.
    payload.pop("scopes", None)
    payload.pop("claims", None)
    payload.pop("policies", None)
    payload.pop("_scopes", None)
    payload.pop("_claims", None)
    payload.pop("_policies", None)
    return payload


SANITIZERS = {
    "groups": sanitize_group,
    "applications": sanitize_application,
    "trusted_origins": sanitize_trusted_origin,
    "network_zones": sanitize_network_zone,
    "authorization_servers": sanitize_authorization_server,
}


def contains_redaction_marker(obj: Any) -> bool:
    if isinstance(obj, dict):
        return any(contains_redaction_marker(v) for v in obj.values())
    if isinstance(obj, list):
        return any(contains_redaction_marker(v) for v in obj)
    if isinstance(obj, str):
        return obj.strip() in REDACTION_MARKERS
    return False
