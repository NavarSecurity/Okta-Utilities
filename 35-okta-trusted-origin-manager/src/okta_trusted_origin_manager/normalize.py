from __future__ import annotations

from typing import Any
from urllib.parse import urlsplit, urlunsplit

ALLOWED_SCOPE_TYPES = {"CORS", "REDIRECT", "IFRAME_EMBED"}
EXPORT_CONTAINER_KEYS = ("trustedOrigins", "trusted_origins", "origins", "items")


def extract_trusted_origins(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if isinstance(payload, dict):
        for key in EXPORT_CONTAINER_KEYS:
            value = payload.get(key)
            if isinstance(value, list):
                return [item for item in value if isinstance(item, dict)]
    return []


def scope_types(origin: dict[str, Any]) -> list[str]:
    scopes = origin.get("scopes") or []
    values: list[str] = []
    if isinstance(scopes, list):
        for item in scopes:
            if isinstance(item, dict):
                scope_type = item.get("type")
            else:
                scope_type = item
            if scope_type:
                values.append(str(scope_type).upper())
    return sorted(set(values))


def canonical_origin_url(value: str | None) -> str:
    if not value:
        return ""
    raw = str(value).strip()
    try:
        split = urlsplit(raw)
    except ValueError:
        return raw.lower()
    if not split.scheme or not split.netloc:
        return raw.lower()
    host = split.hostname.lower() if split.hostname else ""
    if split.port:
        netloc = f"{host}:{split.port}"
    else:
        netloc = host
    return urlunsplit((split.scheme.lower(), netloc, "", "", ""))


def normalize_trusted_origin(origin: dict[str, Any], include_metadata: bool = False) -> dict[str, Any]:
    normalized = {
        "id": origin.get("id"),
        "name": origin.get("name") or "",
        "origin": origin.get("origin") or "",
        "canonicalOrigin": canonical_origin_url(origin.get("origin")),
        "status": origin.get("status") or "",
        "scopes": scope_types(origin),
    }
    if include_metadata:
        normalized.update(
            {
                "created": origin.get("created"),
                "createdBy": origin.get("createdBy"),
                "lastUpdated": origin.get("lastUpdated"),
                "lastUpdatedBy": origin.get("lastUpdatedBy"),
            }
        )
    return normalized


def comparison_view(origin: dict[str, Any], include_status: bool = True) -> dict[str, Any]:
    normalized = normalize_trusted_origin(origin)
    view = {
        "name": normalized["name"],
        "origin": normalized["canonicalOrigin"],
        "scopes": normalized["scopes"],
    }
    if include_status:
        view["status"] = normalized["status"]
    return view


def key_for_origin(origin: dict[str, Any], match_by: str = "origin") -> str:
    normalized = normalize_trusted_origin(origin)
    if match_by == "name":
        return normalized["name"].strip().lower()
    if match_by == "id":
        return str(normalized["id"] or "").strip()
    return normalized["canonicalOrigin"] or normalized["origin"].strip().lower()


def to_okta_payload(origin: dict[str, Any]) -> dict[str, Any]:
    scopes = []
    for scope in scope_types(origin):
        scopes.append({"type": scope})
    return {
        "name": origin.get("name") or origin.get("origin") or "Imported Trusted Origin",
        "origin": origin.get("origin"),
        "scopes": scopes,
    }
