from __future__ import annotations

from typing import Any

from .payloads import (
    build_deactivate_payload,
    build_group_membership_payload,
    build_patch_payload,
    ensure_group_payload,
    ensure_user_payload,
)


def build_plan(config_operations: dict[str, bool], plan: dict[str, Any]) -> list[dict[str, Any]]:
    operations: list[dict[str, Any]] = []

    if config_operations.get("serviceProviderConfig"):
        operations.append({"name": "serviceProviderConfig", "method": "GET", "path": "/ServiceProviderConfig", "mutates": False})
    if config_operations.get("schemas"):
        operations.append({"name": "schemas", "method": "GET", "path": "/Schemas", "mutates": False})
    if config_operations.get("resourceTypes"):
        operations.append({"name": "resourceTypes", "method": "GET", "path": "/ResourceTypes", "mutates": False})

    if config_operations.get("createUser"):
        operations.append({
            "name": "createUser",
            "method": "POST",
            "path": "/Users",
            "payload": ensure_user_payload(plan.get("testUser", {})),
            "mutates": True,
            "captures": "userId",
        })

    if config_operations.get("updateUser"):
        update_user = plan.get("updateUser", {})
        operations.append({
            "name": "updateUser",
            "method": "PATCH",
            "path": "/Users/{userId}",
            "payload": build_patch_payload(update_user),
            "mutates": True,
            "requires": "userId",
        })

    if config_operations.get("deactivateUser"):
        operations.append({
            "name": "deactivateUser",
            "method": "PATCH",
            "path": "/Users/{userId}",
            "payload": build_deactivate_payload(),
            "mutates": True,
            "requires": "userId",
        })

    if config_operations.get("createGroup"):
        operations.append({
            "name": "createGroup",
            "method": "POST",
            "path": "/Groups",
            "payload": ensure_group_payload(plan.get("group", {})),
            "mutates": True,
            "captures": "groupId",
        })

    if config_operations.get("groupPush"):
        user_display = plan.get("testUser", {}).get("userName")
        operations.append({
            "name": "groupPush",
            "method": "PATCH",
            "path": "/Groups/{groupId}",
            "payloadTemplate": "groupMembership",
            "payload": build_group_membership_payload("{userId}", user_display),
            "mutates": True,
            "requires": ["userId", "groupId"],
        })

    if config_operations.get("cleanup"):
        operations.append({"name": "deleteGroup", "method": "DELETE", "path": "/Groups/{groupId}", "mutates": True, "requires": "groupId"})
        operations.append({"name": "deleteUser", "method": "DELETE", "path": "/Users/{userId}", "mutates": True, "requires": "userId"})

    return operations


def replace_tokens(value: Any, variables: dict[str, str]) -> Any:
    if isinstance(value, str):
        result = value
        for key, replacement in variables.items():
            result = result.replace("{" + key + "}", replacement)
        return result
    if isinstance(value, list):
        return [replace_tokens(item, variables) for item in value]
    if isinstance(value, dict):
        return {key: replace_tokens(item, variables) for key, item in value.items()}
    return value
