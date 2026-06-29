from __future__ import annotations

from typing import Any

RESOURCE_FILES = {
    "groups": "groups.json",
    "applications": "applications.json",
    "trusted_origins": "trusted_origins.json",
    "network_zones": "network_zones.json",
    "authorization_servers": "authorization_servers.json",
}

CREATE_ENDPOINTS = {
    "groups": "/api/v1/groups",
    "applications": "/api/v1/apps",
    "trusted_origins": "/api/v1/trustedOrigins",
    "network_zones": "/api/v1/zones",
    "authorization_servers": "/api/v1/authorizationServers",
}

LIST_ENDPOINTS = {
    "groups": "/api/v1/groups",
    "applications": "/api/v1/apps",
    "trusted_origins": "/api/v1/trustedOrigins",
    "network_zones": "/api/v1/zones",
    "authorization_servers": "/api/v1/authorizationServers",
}

DELETE_ENDPOINTS = {
    "groups": "/api/v1/groups/{id}",
    "applications": "/api/v1/apps/{id}",
    "trusted_origins": "/api/v1/trustedOrigins/{id}",
    "network_zones": "/api/v1/zones/{id}",
    "authorization_servers": "/api/v1/authorizationServers/{id}",
}

DISPLAY_FIELDS = {
    "groups": lambda o: (o.get("profile") or {}).get("name") or o.get("id") or "<unknown group>",
    "applications": lambda o: o.get("label") or o.get("name") or o.get("id") or "<unknown app>",
    "trusted_origins": lambda o: o.get("name") or o.get("origin") or o.get("id") or "<unknown trusted origin>",
    "network_zones": lambda o: o.get("name") or o.get("id") or "<unknown network zone>",
    "authorization_servers": lambda o: o.get("name") or o.get("id") or "<unknown authorization server>",
}


def display_name(resource: str, obj: dict[str, Any]) -> str:
    fn = DISPLAY_FIELDS.get(resource)
    if not fn:
        return obj.get("id") or "<unknown>"
    return str(fn(obj))


def natural_key(resource: str, obj: dict[str, Any]) -> str:
    if resource == "groups":
        return str((obj.get("profile") or {}).get("name") or "")
    if resource == "applications":
        return str(obj.get("label") or "")
    if resource == "trusted_origins":
        return str(obj.get("name") or obj.get("origin") or "")
    if resource in {"network_zones", "authorization_servers"}:
        return str(obj.get("name") or "")
    return display_name(resource, obj)
