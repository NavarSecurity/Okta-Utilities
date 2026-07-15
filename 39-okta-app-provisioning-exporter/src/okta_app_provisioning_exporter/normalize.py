from __future__ import annotations

from typing import Any

PROVISIONING_FEATURES = {
    "PUSH_NEW_USERS",
    "PUSH_PROFILE_UPDATES",
    "PUSH_PASSWORD_UPDATES",
    "IMPORT_NEW_USERS",
    "IMPORT_PROFILE_UPDATES",
    "IMPORT_USER_SCHEMA",
    "PROFILE_MASTERING",
    "GROUP_PUSH",
}


def app_key(app: dict[str, Any]) -> str:
    return str(app.get("id") or "")


def app_display_name(app: dict[str, Any]) -> str:
    return str(app.get("label") or app.get("name") or app.get("id") or "")


def should_skip_app(app: dict[str, Any], include_inactive: bool, skip_system: bool, excluded_names: list[str]) -> tuple[bool, str]:
    if not include_inactive and str(app.get("status", "")).upper() != "ACTIVE":
        return True, "inactive_app"
    name = str(app.get("name") or "").lower()
    label = str(app.get("label") or "").lower()
    excluded = {x.lower() for x in excluded_names}
    if skip_system and (name in excluded or label in excluded):
        return True, "okta_system_or_internal_app"
    return False, ""


def read_app_file(path: str) -> list[str]:
    values: list[str] = []
    with open(path, "r", encoding="utf-8") as handle:
        for line in handle:
            clean = line.strip()
            if not clean or clean.startswith("#"):
                continue
            values.append(clean)
    return values


def select_apps(apps: list[dict[str, Any]], mode: str, app_ids: list[str], app_names: list[str], app_file: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    if mode == "all":
        return list(apps), []
    wanted = set(app_ids if mode == "ids" else app_names)
    if mode == "file":
        wanted = set(read_app_file(app_file))
    wanted_lower = {x.lower() for x in wanted}
    selected = []
    skipped = []
    for app in apps:
        identifiers = {
            str(app.get("id") or ""),
            str(app.get("name") or ""),
            str(app.get("label") or ""),
        }
        identifiers_lower = {x.lower() for x in identifiers}
        if wanted_lower & identifiers_lower:
            selected.append(app)
        else:
            skipped.append({"id": app.get("id"), "name": app.get("name"), "label": app.get("label"), "reason": "not_selected"})
    return selected, skipped


def summarize_app(app: dict[str, Any]) -> dict[str, Any]:
    features = app.get("features") or []
    if isinstance(features, dict):
        features = list(features.keys())
    links = app.get("_links") or {}
    return {
        "id": app.get("id", ""),
        "name": app.get("name", ""),
        "label": app.get("label", ""),
        "status": app.get("status", ""),
        "signOnMode": app.get("signOnMode", ""),
        "created": app.get("created", ""),
        "lastUpdated": app.get("lastUpdated", ""),
        "features": ";".join(sorted(str(x) for x in features)),
        "hasSettingsApp": "app" in (app.get("settings") or {}),
        "hasCredentials": bool(app.get("credentials")),
        "linkNames": ";".join(sorted(links.keys())),
    }


def connector_details(app: dict[str, Any], feature_payload: Any | None = None) -> dict[str, Any]:
    settings = app.get("settings") or {}
    app_settings = settings.get("app") or {}
    features = extract_feature_names(feature_payload) or [str(x) for x in app.get("features") or []]
    return {
        "appId": app.get("id", ""),
        "appName": app.get("name", ""),
        "appLabel": app.get("label", ""),
        "status": app.get("status", ""),
        "signOnMode": app.get("signOnMode", ""),
        "instanceType": app_settings.get("instanceType", ""),
        "appUrl": app_settings.get("appUrl", app_settings.get("loginUrl", "")),
        "features": ";".join(sorted(features)),
        "provisioningFeatureCount": len([f for f in features if f in PROVISIONING_FEATURES]),
    }


def extract_feature_names(payload: Any) -> list[str]:
    if not payload:
        return []
    if isinstance(payload, list):
        names = []
        for item in payload:
            if isinstance(item, dict):
                names.append(str(item.get("name") or item.get("type") or item.get("id") or "").strip())
            else:
                names.append(str(item).strip())
        return [x for x in names if x]
    if isinstance(payload, dict):
        if "features" in payload:
            return extract_feature_names(payload["features"])
        return [str(k) for k in payload.keys()]
    return []




def is_feature_not_applicable(status_code: int, payload: Any | None, response_text: str | None) -> bool:
    """Return True when Okta reports that the app features endpoint is not applicable.

    Some Okta app integrations do not support provisioning features. Okta commonly
    returns HTTP 400 with a message such as "Provisioning is not supported."
    This should be reported as not applicable, not as a request failure.
    """
    if status_code < 400:
        return False

    searchable_parts: list[str] = []
    if response_text:
        searchable_parts.append(str(response_text))
    if isinstance(payload, dict):
        for key in ("errorSummary", "errorCauses", "message", "error"):
            value = payload.get(key)
            if value:
                searchable_parts.append(str(value))
    elif payload:
        searchable_parts.append(str(payload))

    combined = " ".join(searchable_parts).lower()
    not_applicable_phrases = (
        "provisioning is not supported",
        "provisioning not supported",
        "provisioning is unsupported",
    )
    return any(phrase in combined for phrase in not_applicable_phrases)

def provisioning_feature_rows(app: dict[str, Any], feature_payload: Any | None = None) -> list[dict[str, Any]]:
    feature_names = extract_feature_names(feature_payload) or [str(x) for x in app.get("features") or []]
    rows = []
    for feature in sorted(set(feature_names)):
        rows.append({
            "appId": app.get("id", ""),
            "appName": app.get("name", ""),
            "appLabel": app.get("label", ""),
            "feature": feature,
            "isProvisioningRelated": feature in PROVISIONING_FEATURES,
        })
    return rows


def flatten_schema_attributes(app: dict[str, Any], schema: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    definitions = schema.get("definitions") or {}
    for definition_name, definition in definitions.items():
        properties = (definition or {}).get("properties") or {}
        for attr, meta in properties.items():
            if not isinstance(meta, dict):
                meta = {}
            rows.append({
                "appId": app.get("id", ""),
                "appName": app.get("name", ""),
                "appLabel": app.get("label", ""),
                "definition": definition_name,
                "attribute": attr,
                "title": meta.get("title", ""),
                "type": meta.get("type", ""),
                "required": meta.get("required", False),
                "scope": meta.get("scope", ""),
                "description": meta.get("description", ""),
            })
    return rows


def mapping_involves_app(mapping: dict[str, Any], app_ids: set[str]) -> bool:
    source = mapping.get("source") or {}
    target = mapping.get("target") or {}
    candidates = {str(source.get("id") or ""), str(target.get("id") or "")}
    return bool(candidates & app_ids)


def flatten_mapping_properties(mapping: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    source = mapping.get("source") or {}
    target = mapping.get("target") or {}
    properties = mapping.get("properties") or {}
    for target_attr, detail in properties.items():
        if not isinstance(detail, dict):
            detail = {}
        rows.append({
            "mappingId": mapping.get("id", ""),
            "sourceId": source.get("id", ""),
            "sourceName": source.get("name", ""),
            "sourceType": source.get("type", ""),
            "targetId": target.get("id", ""),
            "targetName": target.get("name", ""),
            "targetType": target.get("type", ""),
            "targetAttribute": target_attr,
            "expression": detail.get("expression", ""),
            "pushStatus": detail.get("pushStatus", ""),
        })
    return rows
