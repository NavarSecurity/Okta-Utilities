from __future__ import annotations

from pathlib import Path
from typing import Any

from .config import read_lines_file
from .normalize import (
    entity_display_name,
    flatten_target,
    get_profile_value,
    id_from_href,
    is_high_privilege,
    member_type_from_href,
    role_assignment_id,
    role_label,
    role_type,
)
from .okta_client import OktaClient
from .redact import redact_value
from .reports import make_output_dir, manifest, utc_timestamp, write_csv, write_json, write_markdown_report


def run_export(config: dict[str, Any], client: OktaClient, dry_run: bool = False) -> Path:
    output_dir = make_output_dir(config["outputDirectory"], "admin-role-report-dry-run" if dry_run else "admin-role-report")
    if dry_run:
        return _write_dry_run(config, output_dir)

    data: dict[str, Any] = {
        "usersWithRoleAssignments": [],
        "userRoleAssignments": [],
        "userRoleTargets": [],
        "userRoleGovernance": [],
        "groupsInspected": [],
        "groupRoleAssignments": [],
        "groupRoleTargets": [],
        "privilegedGroupMembers": [],
        "clientRoleAssignments": [],
        "clientRoleTargets": [],
        "customRoles": [],
        "customRolePermissions": [],
        "resourceSets": [],
        "resourceSetResources": [],
        "resourceSetBindings": [],
        "bindingMembers": [],
        "requestFailures": [],
    }

    if config.get("includeUserRoleAssignments", True):
        _export_user_assignments(config, client, data)

    if config.get("includeGroupRoleAssignments", True):
        _export_group_assignments(config, client, data)

    if config.get("includeClientRoleAssignments", False):
        _export_client_assignments(config, client, data)

    if config.get("includeCustomRoles", True):
        _export_custom_roles(config, client, data)

    if config.get("includeResourceSets", True):
        _export_resource_sets(config, client, data)

    data["requestFailures"] = [failure.__dict__ for failure in client.failures]
    return _write_outputs(config, output_dir, data)


def _write_dry_run(config: dict[str, Any], output_dir: Path) -> Path:
    dry_run_report = {
        "utility": "okta-admin-role-reporter",
        "status": "DRY_RUN",
        "timestamp": utc_timestamp(),
        "message": "Dry run completed. No Okta API calls were made.",
        "plannedOperations": {
            "includeUserRoleAssignments": config.get("includeUserRoleAssignments"),
            "includeUserRoleTargets": config.get("includeUserRoleTargets"),
            "includeGroupRoleAssignments": config.get("includeGroupRoleAssignments"),
            "includeGroupRoleTargets": config.get("includeGroupRoleTargets"),
            "includeClientRoleAssignments": config.get("includeClientRoleAssignments"),
            "includeCustomRoles": config.get("includeCustomRoles"),
            "includeResourceSets": config.get("includeResourceSets"),
        },
    }
    write_json(output_dir / "dry_run_report.json", dry_run_report)
    write_json(output_dir / "config_summary.json", redact_value(config))
    execution_report = {
        "utility": "okta-admin-role-reporter",
        "status": "DRY_RUN",
        "timestamp": utc_timestamp(),
        "summary": {
            "userRoleAssignments": 0,
            "groupRoleAssignments": 0,
            "clientRoleAssignments": 0,
            "customRoles": 0,
            "resourceSets": 0,
            "highPrivilegeAssignments": 0,
            "requestFailures": 0,
        },
    }
    write_json(output_dir / "execution_report.json", execution_report)
    write_json(output_dir / "manifest.json", manifest(config.get("configPath", ""), output_dir, ["dry_run_report.json", "config_summary.json", "execution_report.json", "manifest.json"]))
    return output_dir


def _guarded(config: dict[str, Any], failures: list[dict[str, Any]], label: str, callback):
    try:
        return callback()
    except Exception as exc:
        failures.append({"step": label, "message": str(exc)})
        if not config.get("continueOnRequestError", True):
            raise
        return None


def _export_user_assignments(config: dict[str, Any], client: OktaClient, data: dict[str, Any]) -> None:
    assignees = _guarded(config, data["requestFailures"], "list users with role assignments", lambda: client.list_paginated("/api/v1/iam/assignees/users?limit=100")) or []
    data["usersWithRoleAssignments"] = assignees
    for assignee in assignees:
        user_id = assignee.get("id")
        if not user_id:
            continue
        user = _guarded(config, data["requestFailures"], f"get user {user_id}", lambda uid=user_id: client.request("GET", f"/api/v1/users/{uid}")) or {"id": user_id, "profile": {}}
        roles = _guarded(config, data["requestFailures"], f"list roles for user {user_id}", lambda uid=user_id: client.list_paginated(f"/api/v1/users/{uid}/roles")) or []
        for role in roles:
            assignment = _assignment_row("user", user, role, config)
            data["userRoleAssignments"].append(assignment)
            role_id = role_assignment_id(role)
            if role_id and config.get("includeUserRoleTargets", True):
                _export_role_targets(config, client, data, "user", user_id, role_id, assignment)
            if role_id and config.get("includeUserRoleGovernance", False):
                governance = _guarded(config, data["requestFailures"], f"get governance for user role {user_id}/{role_id}", lambda uid=user_id, rid=role_id: client.request("GET", f"/api/v1/users/{uid}/roles/{rid}/governance"))
                if governance is not None:
                    data["userRoleGovernance"].append({**assignment, "governance": governance})


def _export_group_assignments(config: dict[str, Any], client: OktaClient, data: dict[str, Any]) -> None:
    groups = _select_groups(config, client, data)
    data["groupsInspected"] = groups
    for group in groups:
        group_id = group.get("id")
        if not group_id:
            continue
        roles = _guarded(config, data["requestFailures"], f"list roles for group {group_id}", lambda gid=group_id: client.list_paginated(f"/api/v1/groups/{gid}/roles")) or []
        for role in roles:
            assignment = _assignment_row("group", group, role, config)
            data["groupRoleAssignments"].append(assignment)
            role_id = role_assignment_id(role)
            if role_id and config.get("includeGroupRoleTargets", True):
                _export_role_targets(config, client, data, "group", group_id, role_id, assignment)
        if roles and config.get("includePrivilegedGroupMembers", False):
            members = _guarded(config, data["requestFailures"], f"list members for privileged group {group_id}", lambda gid=group_id: client.list_paginated(f"/api/v1/groups/{gid}/users?limit=200")) or []
            for member in members:
                data["privilegedGroupMembers"].append({
                    "groupId": group_id,
                    "groupName": entity_display_name(group, "group"),
                    "userId": member.get("id", ""),
                    "login": get_profile_value(member, "login"),
                    "email": get_profile_value(member, "email"),
                    "status": member.get("status", ""),
                })


def _select_groups(config: dict[str, Any], client: OktaClient, data: dict[str, Any]) -> list[dict[str, Any]]:
    group_config = config.get("groupSelection", {})
    mode = group_config.get("mode", "all")
    if mode == "ids":
        ids = list(group_config.get("groupIds", [])) + read_lines_file(group_config.get("groupFile", "input/groups.txt"))
        groups = []
        for group_id in ids:
            group = _guarded(config, data["requestFailures"], f"get group {group_id}", lambda gid=group_id: client.request("GET", f"/api/v1/groups/{gid}"))
            if isinstance(group, dict):
                groups.append(group)
        return groups

    limit = int(group_config.get("limit", 200))
    all_groups = _guarded(config, data["requestFailures"], "list groups", lambda: client.list_paginated(f"/api/v1/groups?limit={limit}")) or []
    if mode == "names":
        names = set(group_config.get("groupNames", []))
        return [group for group in all_groups if get_profile_value(group, "name") in names]
    if mode == "file":
        names = set(read_lines_file(group_config.get("groupFile", "input/groups.txt")))
        return [group for group in all_groups if get_profile_value(group, "name") in names or group.get("id") in names]
    return all_groups


def _export_client_assignments(config: dict[str, Any], client: OktaClient, data: dict[str, Any]) -> None:
    client_ids = _selected_client_ids(config)
    for client_id in client_ids:
        roles = _guarded(config, data["requestFailures"], f"list roles for client {client_id}", lambda cid=client_id: client.list_paginated(f"/oauth2/v1/clients/{cid}/roles")) or []
        client_entity = {"id": client_id, "client_id": client_id}
        for role in roles:
            assignment = _assignment_row("client", client_entity, role, config)
            data["clientRoleAssignments"].append(assignment)
            role_id = role_assignment_id(role)
            if role_id and config.get("includeClientRoleTargets", False):
                _export_role_targets(config, client, data, "client", client_id, role_id, assignment)


def _selected_client_ids(config: dict[str, Any]) -> list[str]:
    client_config = config.get("clientSelection", {})
    ids = list(client_config.get("clientIds", []))
    ids.extend(read_lines_file(client_config.get("clientFile", "input/clients.txt")))
    return [item for item in ids if item]


def _export_custom_roles(config: dict[str, Any], client: OktaClient, data: dict[str, Any]) -> None:
    roles = _guarded(config, data["requestFailures"], "list custom roles", lambda: client.list_paginated("/api/v1/iam/roles?limit=200")) or []
    data["customRoles"] = roles
    if not config.get("includeCustomRolePermissions", True):
        return
    for role in roles:
        role_id = role.get("id") or role.get("label")
        if not role_id:
            continue
        permissions = _guarded(config, data["requestFailures"], f"list custom role permissions {role_id}", lambda rid=role_id: client.list_paginated(f"/api/v1/iam/roles/{rid}/permissions")) or []
        for permission in permissions:
            data["customRolePermissions"].append({
                "roleId": role.get("id", ""),
                "roleLabel": role.get("label", ""),
                "permissionType": permission.get("type") or permission.get("permissionType") or permission.get("id") or "",
                "permission": permission,
            })


def _export_resource_sets(config: dict[str, Any], client: OktaClient, data: dict[str, Any]) -> None:
    resource_sets = _guarded(config, data["requestFailures"], "list resource sets", lambda: client.list_paginated("/api/v1/iam/resource-sets?limit=200")) or []
    data["resourceSets"] = resource_sets
    for resource_set in resource_sets:
        resource_set_id = resource_set.get("id") or resource_set.get("label")
        if not resource_set_id:
            continue
        if config.get("includeResourceSetResources", True):
            resources = _guarded(config, data["requestFailures"], f"list resources for resource set {resource_set_id}", lambda rsid=resource_set_id: client.list_paginated(f"/api/v1/iam/resource-sets/{rsid}/resources")) or []
            for resource in resources:
                data["resourceSetResources"].append({
                    "resourceSetId": resource_set.get("id", ""),
                    "resourceSetLabel": resource_set.get("label", ""),
                    "resourceId": resource.get("id", ""),
                    "resourceName": resource.get("label") or resource.get("name") or "",
                    "resourceType": resource.get("type") or resource.get("resourceType") or "",
                    "resource": resource,
                })
        if config.get("includeResourceSetBindings", True):
            bindings = _guarded(config, data["requestFailures"], f"list bindings for resource set {resource_set_id}", lambda rsid=resource_set_id: client.list_paginated(f"/api/v1/iam/resource-sets/{rsid}/bindings")) or []
            for binding in bindings:
                binding_row = {
                    "resourceSetId": resource_set.get("id", ""),
                    "resourceSetLabel": resource_set.get("label", ""),
                    "roleId": binding.get("id") or binding.get("roleId") or binding.get("role") or "",
                    "roleLabel": binding.get("label") or binding.get("roleLabel") or "",
                    "binding": binding,
                }
                data["resourceSetBindings"].append(binding_row)
                role_id = binding_row["roleId"] or binding_row["roleLabel"]
                if role_id and config.get("includeBindingMembers", True):
                    members = _guarded(config, data["requestFailures"], f"list members for binding {resource_set_id}/{role_id}", lambda rsid=resource_set_id, rid=role_id: client.list_paginated(f"/api/v1/iam/resource-sets/{rsid}/bindings/{rid}/members")) or []
                    for member in members:
                        member_href = member.get("href") or member.get("id") or ""
                        if isinstance(member.get("_links"), dict) and isinstance(member["_links"].get("self"), dict):
                            member_href = member["_links"]["self"].get("href", member_href)
                        data["bindingMembers"].append({
                            "resourceSetId": resource_set.get("id", ""),
                            "resourceSetLabel": resource_set.get("label", ""),
                            "roleId": role_id,
                            "memberId": member.get("id") or id_from_href(member_href),
                            "memberType": member.get("type") or member_type_from_href(member_href),
                            "memberHref": member_href,
                            "member": member,
                        })


def _export_role_targets(config: dict[str, Any], client: OktaClient, data: dict[str, Any], principal_type: str, principal_id: str, role_id: str, assignment: dict[str, Any]) -> None:
    base = "/api/v1/users" if principal_type == "user" else "/api/v1/groups" if principal_type == "group" else "/oauth2/v1/clients"
    target_list_name = "userRoleTargets" if principal_type == "user" else "groupRoleTargets" if principal_type == "group" else "clientRoleTargets"
    for target_kind, suffix in [("group", "targets/groups"), ("app", "targets/catalog/apps")]:
        targets = _guarded(config, data["requestFailures"], f"list {target_kind} targets for {principal_type} role {principal_id}/{role_id}", lambda b=base, pid=principal_id, rid=role_id, s=suffix: client.list_paginated(f"{b}/{pid}/roles/{rid}/{s}"))
        if targets is None:
            continue
        for target in targets:
            data[target_list_name].append({
                **assignment,
                "targetKind": target_kind,
                **flatten_target(target),
                "target": target,
            })


def _assignment_row(principal_type: str, principal: dict[str, Any], role: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    high_privilege = is_high_privilege(role, config.get("highPrivilegeRoles", []))
    row = {
        "principalType": principal_type,
        "principalId": principal.get("id") or principal.get("client_id") or "",
        "principalName": entity_display_name(principal, principal_type),
        "login": get_profile_value(principal, "login") if principal_type == "user" else "",
        "email": get_profile_value(principal, "email") if principal_type == "user" else "",
        "status": principal.get("status", ""),
        "roleAssignmentId": role_assignment_id(role),
        "roleType": role_type(role),
        "roleLabel": role_label(role),
        "roleStatus": role.get("status", ""),
        "isHighPrivilege": high_privilege,
        "assignmentSource": "direct" if principal_type == "user" else "group" if principal_type == "group" else "client",
        "role": role,
    }
    return row


def _write_outputs(config: dict[str, Any], output_dir: Path, data: dict[str, Any]) -> Path:
    if config.get("redactSensitiveValues", True):
        safe_data = redact_value(data)
    else:
        safe_data = data

    assignments = safe_data["userRoleAssignments"] + safe_data["groupRoleAssignments"] + safe_data["clientRoleAssignments"]
    high_privileged = [row for row in assignments if row.get("isHighPrivilege")]
    targets = safe_data["userRoleTargets"] + safe_data["groupRoleTargets"] + safe_data["clientRoleTargets"]

    summary = {
        "userRoleAssignments": len(safe_data["userRoleAssignments"]),
        "groupRoleAssignments": len(safe_data["groupRoleAssignments"]),
        "clientRoleAssignments": len(safe_data["clientRoleAssignments"]),
        "customRoles": len(safe_data["customRoles"]),
        "customRolePermissions": len(safe_data["customRolePermissions"]),
        "resourceSets": len(safe_data["resourceSets"]),
        "resourceSetBindings": len(safe_data["resourceSetBindings"]),
        "bindingMembers": len(safe_data["bindingMembers"]),
        "highPrivilegeAssignments": len(high_privileged),
        "requestFailures": len(safe_data["requestFailures"]),
    }
    status = "SUCCESS_WITH_WARNINGS" if summary["requestFailures"] else "SUCCESS"
    execution_report = {
        "utility": "okta-admin-role-reporter",
        "status": status,
        "timestamp": utc_timestamp(),
        "summary": summary,
        "requestFailures": safe_data["requestFailures"],
    }

    files = []
    json_files = {
        "admin_role_assignments_full.json": safe_data,
        "users_with_role_assignments.json": safe_data["usersWithRoleAssignments"],
        "custom_roles_full.json": safe_data["customRoles"],
        "resource_sets_full.json": safe_data["resourceSets"],
        "execution_report.json": execution_report,
    }
    for filename, payload in json_files.items():
        write_json(output_dir / filename, payload)
        files.append(filename)

    write_csv(output_dir / "admin_role_assignments.csv", assignments, [
        "principalType", "principalId", "principalName", "login", "email", "status", "roleAssignmentId", "roleType", "roleLabel", "roleStatus", "isHighPrivilege", "assignmentSource"
    ])
    write_csv(output_dir / "privileged_assignments.csv", high_privileged, [
        "principalType", "principalId", "principalName", "login", "email", "status", "roleAssignmentId", "roleType", "roleLabel", "roleStatus", "assignmentSource"
    ])
    write_csv(output_dir / "admin_role_targets.csv", targets, [
        "principalType", "principalId", "principalName", "roleAssignmentId", "roleType", "roleLabel", "targetKind", "targetId", "targetName", "targetType", "targetHref"
    ])
    write_csv(output_dir / "custom_role_permissions.csv", safe_data["customRolePermissions"], [
        "roleId", "roleLabel", "permissionType", "permission"
    ])
    write_csv(output_dir / "resource_set_bindings.csv", safe_data["resourceSetBindings"], [
        "resourceSetId", "resourceSetLabel", "roleId", "roleLabel", "binding"
    ])
    write_csv(output_dir / "binding_members.csv", safe_data["bindingMembers"], [
        "resourceSetId", "resourceSetLabel", "roleId", "memberId", "memberType", "memberHref", "member"
    ])
    write_csv(output_dir / "privileged_group_members.csv", safe_data["privilegedGroupMembers"], [
        "groupId", "groupName", "userId", "login", "email", "status"
    ])
    write_csv(output_dir / "request_failures.csv", safe_data["requestFailures"], ["method", "path", "status_code", "message", "step"])
    files.extend([
        "admin_role_assignments.csv", "privileged_assignments.csv", "admin_role_targets.csv", "custom_role_permissions.csv", "resource_set_bindings.csv", "binding_members.csv", "privileged_group_members.csv", "request_failures.csv"
    ])

    report = {"status": status, "timestamp": utc_timestamp(), "summary": summary}
    write_markdown_report(output_dir / "admin_role_report.md", report)
    files.append("admin_role_report.md")
    write_json(output_dir / "manifest.json", manifest(config.get("configPath", ""), output_dir, files + ["manifest.json"]))
    return output_dir
