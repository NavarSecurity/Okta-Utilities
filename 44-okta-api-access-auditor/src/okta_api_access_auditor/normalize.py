from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def parse_time(value: Any) -> datetime | None:
    if not value or not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def days_since(value: Any, now: datetime | None = None) -> int | None:
    parsed = parse_time(value)
    if parsed is None:
        return None
    now = now or datetime.now(timezone.utc)
    return int((now - parsed).total_seconds() // 86400)


def get_nested(data: dict[str, Any], path: list[str], default: Any = None) -> Any:
    value: Any = data
    for key in path:
        if not isinstance(value, dict) or key not in value:
            return default
        value = value[key]
    return value


def app_client_id(app: dict[str, Any]) -> str:
    return str(get_nested(app, ["credentials", "oauthClient", "client_id"], "") or "")


def app_type(app: dict[str, Any]) -> str:
    return str(get_nested(app, ["settings", "oauthClient", "application_type"], "") or "")


def grant_types(app: dict[str, Any]) -> list[str]:
    values = get_nested(app, ["settings", "oauthClient", "grant_types"], []) or []
    return values if isinstance(values, list) else []


def token_auth_method(app: dict[str, Any]) -> str:
    return str(get_nested(app, ["settings", "oauthClient", "token_endpoint_auth_method"], "") or "")


def is_oidc_app(app: dict[str, Any]) -> bool:
    return app.get("name") == "oidc_client" or app.get("signOnMode") == "OPENID_CONNECT"


def is_service_app(app: dict[str, Any]) -> bool:
    app_type_value = app_type(app).lower()
    grants = {g.lower() for g in grant_types(app)}
    return is_oidc_app(app) and (app_type_value == "service" or "client_credentials" in grants)


def normalize_app(app: dict[str, Any]) -> dict[str, Any]:
    return {
        "appId": app.get("id", ""),
        "label": app.get("label", ""),
        "name": app.get("name", ""),
        "status": app.get("status", ""),
        "signOnMode": app.get("signOnMode", ""),
        "clientId": app_client_id(app),
        "applicationType": app_type(app),
        "grantTypes": ";".join(grant_types(app)),
        "tokenEndpointAuthMethod": token_auth_method(app),
        "created": app.get("created", ""),
        "lastUpdated": app.get("lastUpdated", ""),
        "isServiceApp": is_service_app(app),
    }


def normalize_grant(app: dict[str, Any], grant: dict[str, Any]) -> dict[str, Any]:
    scope = grant.get("scopeId") or grant.get("scope") or grant.get("name") or ""
    return {
        "appId": app.get("id", ""),
        "appLabel": app.get("label", ""),
        "clientId": app_client_id(app),
        "grantId": grant.get("id", ""),
        "scope": scope,
        "issuer": grant.get("issuer", ""),
        "created": grant.get("created", ""),
        "lastUpdated": grant.get("lastUpdated", ""),
    }


def normalize_client_role(app: dict[str, Any], role: dict[str, Any]) -> dict[str, Any]:
    return {
        "appId": app.get("id", ""),
        "appLabel": app.get("label", ""),
        "clientId": app_client_id(app),
        "roleAssignmentId": role.get("id", ""),
        "roleType": role.get("type") or role.get("role") or "",
        "roleLabel": role.get("label") or role.get("displayName") or role.get("type") or "",
        "assignmentType": role.get("assignmentType", ""),
        "status": role.get("status", ""),
        "created": role.get("created", ""),
        "lastUpdated": role.get("lastUpdated", ""),
    }


def normalize_api_token(token: dict[str, Any]) -> dict[str, Any]:
    created_by = token.get("createdBy") or token.get("owner") or {}
    network = token.get("network") or token.get("networkCondition") or {}
    return {
        "tokenId": token.get("id", ""),
        "name": token.get("name") or token.get("clientName") or token.get("label") or "",
        "status": token.get("status", ""),
        "tokenType": token.get("tokenType") or token.get("type") or "",
        "created": token.get("created", ""),
        "lastUpdated": token.get("lastUpdated", ""),
        "lastUsed": token.get("lastUsed", ""),
        "expiresAt": token.get("expiresAt", ""),
        "createdById": created_by.get("id", "") if isinstance(created_by, dict) else "",
        "createdByLogin": created_by.get("login", "") if isinstance(created_by, dict) else "",
        "createdByDisplayName": created_by.get("displayName", "") if isinstance(created_by, dict) else "",
        "networkConnection": network.get("connection", "") if isinstance(network, dict) else "",
        "networkZones": ";".join(str(z) for z in network.get("zones", []) if isinstance(network, dict)),
    }


def value_list(values: list[dict[str, Any]], key: str) -> list[str]:
    return sorted({str(item.get(key, "")) for item in values if item.get(key)})
