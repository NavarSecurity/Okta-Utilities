from __future__ import annotations

from typing import Any

PATCH_SCHEMA = "urn:ietf:params:scim:api:messages:2.0:PatchOp"
USER_SCHEMA = "urn:ietf:params:scim:schemas:core:2.0:User"
GROUP_SCHEMA = "urn:ietf:params:scim:schemas:core:2.0:Group"


def ensure_user_payload(test_user: dict[str, Any]) -> dict[str, Any]:
    payload = dict(test_user)
    payload.setdefault("schemas", [USER_SCHEMA])
    if "userName" not in payload:
        raise ValueError("testUser.userName is required.")
    return payload


def ensure_group_payload(group: dict[str, Any]) -> dict[str, Any]:
    payload = dict(group)
    payload.setdefault("schemas", [GROUP_SCHEMA])
    if "displayName" not in payload:
        raise ValueError("group.displayName is required.")
    return payload


def build_patch_payload(attributes: dict[str, Any]) -> dict[str, Any]:
    operations = []
    for path, value in attributes.items():
        operations.append({"op": "replace", "path": path, "value": value})
    return {"schemas": [PATCH_SCHEMA], "Operations": operations}


def build_deactivate_payload() -> dict[str, Any]:
    return {"schemas": [PATCH_SCHEMA], "Operations": [{"op": "replace", "path": "active", "value": False}]}


def build_group_membership_payload(user_id: str, display: str | None = None) -> dict[str, Any]:
    member: dict[str, Any] = {"value": user_id}
    if display:
        member["display"] = display
    return {"schemas": [PATCH_SCHEMA], "Operations": [{"op": "add", "path": "members", "value": [member]}]}
