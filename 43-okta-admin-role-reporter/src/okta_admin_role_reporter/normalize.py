from __future__ import annotations

import re
from typing import Any


def get_profile_value(entity: dict[str, Any], key: str, default: str = "") -> str:
    profile = entity.get("profile", {}) if isinstance(entity, dict) else {}
    value = profile.get(key, default) if isinstance(profile, dict) else default
    return "" if value is None else str(value)


def entity_display_name(entity: dict[str, Any], entity_type: str) -> str:
    if entity_type == "user":
        first = get_profile_value(entity, "firstName")
        last = get_profile_value(entity, "lastName")
        name = " ".join([x for x in [first, last] if x]).strip()
        return name or get_profile_value(entity, "login") or entity.get("id", "")
    if entity_type == "group":
        return get_profile_value(entity, "name") or entity.get("id", "")
    if entity_type == "client":
        return str(entity.get("client_name") or entity.get("name") or entity.get("label") or entity.get("id") or entity.get("client_id") or "")
    return str(entity.get("name") or entity.get("label") or entity.get("id") or "")


def role_type(role: dict[str, Any]) -> str:
    for key in ["type", "role", "id", "label"]:
        value = role.get(key)
        if isinstance(value, str) and value:
            return value
    return "UNKNOWN"


def role_label(role: dict[str, Any]) -> str:
    for key in ["label", "displayName", "description", "type", "id"]:
        value = role.get(key)
        if isinstance(value, str) and value:
            return value
    return ""


def role_assignment_id(role: dict[str, Any]) -> str:
    return str(role.get("id") or role.get("assignmentId") or role.get("roleAssignmentId") or "")


def is_high_privilege(role: dict[str, Any], high_privilege_roles: list[str]) -> bool:
    role_values = {role_type(role).upper(), role_label(role).upper()}
    normalized_high = {item.upper() for item in high_privilege_roles}
    if role_values & normalized_high:
        return True
    if role.get("type") == "CUSTOM" or role.get("roleType") == "CUSTOM":
        return "CUSTOM" in normalized_high
    return False


def flatten_target(target: dict[str, Any]) -> dict[str, str]:
    return {
        "targetId": str(target.get("id") or ""),
        "targetName": str(target.get("name") or target.get("label") or target.get("displayName") or ""),
        "targetType": str(target.get("type") or target.get("objectType") or target.get("resourceType") or ""),
        "targetHref": _link_href(target, "self"),
    }


def _link_href(obj: dict[str, Any], link_name: str) -> str:
    links = obj.get("_links", {}) if isinstance(obj, dict) else {}
    link = links.get(link_name) if isinstance(links, dict) else None
    if isinstance(link, dict):
        return str(link.get("href") or "")
    return ""


def member_type_from_href(href: str) -> str:
    if "/api/v1/users/" in href:
        return "user"
    if "/api/v1/groups/" in href:
        return "group"
    if "/oauth2/v1/clients/" in href:
        return "client"
    return "unknown"


def id_from_href(href: str) -> str:
    match = re.search(r"/(users|groups|clients)/([^/?#]+)", href)
    return match.group(2) if match else ""
