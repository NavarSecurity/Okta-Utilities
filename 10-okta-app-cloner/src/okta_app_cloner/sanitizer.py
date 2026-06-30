from __future__ import annotations

import copy
from typing import Any

READ_ONLY_KEYS = {
    "id",
    "_links",
    "_embedded",
    "created",
    "lastUpdated",
    "lastMembershipUpdated",
    "activated",
    "credentialsExpireAt",
}

SENSITIVE_KEYS = {
    "client_secret",
    "clientSecret",
    "secret",
    "sharedSecret",
    "apiToken",
    "access_token",
    "refresh_token",
    "id_token",
    "privateKey",
    "private_key",
    "authorization",
    "authorizationHeader",
    "password",
}

# Fields that are often present in GET responses but should not be posted back when cloning.
RESPONSE_ONLY_KEYS = {
    "client_id",
    "clientId",
}

# Source-org-specific references that can cause target-org creation failures.
# Example: credentials.signing.kid can reference an AppInstanceKeyMapping that only exists
# in the source org. Sending that value to the target org causes Okta to return 404.
SOURCE_ORG_REFERENCE_KEYS = {
    "orn",
    "kid",
    "keyId",
    "key_id",
    "keyMappingId",
    "appInstanceKeyMappingId",
}

# Entire nested sections that should not be blindly cloned from a source app GET response.
# The target org should create/use its own signing credentials and provisioning credentials.
SOURCE_ORG_REFERENCE_PATHS = {
    ("credentials", "signing"),
    ("credentials", "oauthClient"),
    ("credentials", "userNameTemplate"),
}

PROVISIONING_FEATURES = {"PROVISIONING", "IMPORT_NEW_USERS", "PUSH_NEW_USERS"}


def _redacted(value: Any) -> bool:
    return isinstance(value, str) and value.strip().upper() in {"[REDACTED]", "REDACTED", "<REDACTED>", "***"}


def _is_source_reference_path(path: tuple[str, ...]) -> bool:
    return path in SOURCE_ORG_REFERENCE_PATHS


def _clean(value: Any, *, path: tuple[str, ...] = ()) -> Any:
    if _redacted(value):
        return None

    if isinstance(value, dict):
        if _is_source_reference_path(path):
            return None

        cleaned: dict[str, Any] = {}
        for key, child in value.items():
            child_path = path + (str(key),)
            if key in READ_ONLY_KEYS:
                continue
            if key in SENSITIVE_KEYS or key in RESPONSE_ONLY_KEYS or key in SOURCE_ORG_REFERENCE_KEYS:
                continue
            if _is_source_reference_path(child_path):
                continue
            cleaned_child = _clean(child, path=child_path)
            if cleaned_child is not None:
                cleaned[key] = cleaned_child
        return cleaned

    if isinstance(value, list):
        cleaned_items = []
        for index, item in enumerate(value):
            cleaned_item = _clean(item, path=path + (str(index),))
            if cleaned_item is not None:
                cleaned_items.append(cleaned_item)
        return cleaned_items

    return value


def _drop_empty_source_credential_sections(payload: dict[str, Any]) -> None:
    credentials = payload.get("credentials")
    if not isinstance(credentials, dict):
        return

    # Remove known source-generated credential blocks even if partially preserved.
    credentials.pop("signing", None)
    credentials.pop("oauthClient", None)

    if not credentials:
        payload.pop("credentials", None)


def sanitize_app_for_clone(app: dict[str, Any], *, activate: bool = False, include_provisioning: bool = False) -> dict[str, Any]:
    """Return an app create payload that is safe to send to a target Okta org.

    Okta app GET responses can include source-org-only values such as object IDs,
    links, ORNs, generated OAuth credentials, and signing key mappings. Those values
    should not be sent back to `/api/v1/apps` when creating an app in another org.
    """

    payload = copy.deepcopy(app)
    payload = _clean(payload)

    if not isinstance(payload, dict):
        return {}

    # Defensive cleanup for source-org-only generated app credentials.
    _drop_empty_source_credential_sections(payload)

    if not include_provisioning:
        features = payload.get("features")
        if isinstance(features, list):
            payload["features"] = [feature for feature in features if feature not in PROVISIONING_FEATURES]
        settings = payload.get("settings")
        if isinstance(settings, dict):
            # App provisioning settings are tenant- and connector-specific and should not be blindly cloned.
            settings.pop("provisioning", None)
            settings.pop("appProvisioning", None)

    if activate:
        payload["status"] = "ACTIVE"
    else:
        payload.pop("status", None)

    return payload


def app_natural_key(app: dict[str, Any]) -> str:
    return str(app.get("label") or app.get("name") or app.get("id") or "").strip()


def app_display_name(app: dict[str, Any]) -> str:
    return str(app.get("label") or app.get("name") or app.get("id") or "<unnamed app>")


def app_type(app: dict[str, Any]) -> str:
    return str(app.get("signOnMode") or app.get("name") or "UNKNOWN")
