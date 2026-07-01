from __future__ import annotations

from typing import Any

from .config import AppSelection, ExportOptions


def scalar_profile_fields(profile: dict[str, Any] | None, prefix: str) -> dict[str, Any]:
    if not isinstance(profile, dict):
        return {}
    output: dict[str, Any] = {}
    for key, value in sorted(profile.items()):
        if isinstance(value, (str, int, float, bool)) or value is None:
            output[f"{prefix}{key}"] = value
    return output


def app_basic(app: dict[str, Any]) -> dict[str, Any]:
    return {
        "appId": app.get("id", ""),
        "appLabel": app.get("label", ""),
        "appName": app.get("name", ""),
        "signOnMode": app.get("signOnMode", ""),
        "status": app.get("status", ""),
        "created": app.get("created", ""),
        "lastUpdated": app.get("lastUpdated", ""),
    }


def select_apps(apps: list[dict[str, Any]], selection: AppSelection, options: ExportOptions) -> tuple[list[dict[str, Any]], list[str]]:
    warnings: list[str] = []
    selected: list[dict[str, Any]] = []
    label_set = set(selection.app_labels)
    id_set = set(selection.app_ids)
    exclude_ids = set(selection.exclude_app_ids)
    exclude_labels = set(selection.exclude_app_labels)
    statuses = set(selection.statuses)
    sign_on_modes = set(selection.sign_on_modes)

    seen_ids: set[str] = set()
    for app in apps:
        app_id = str(app.get("id", ""))
        app_label = str(app.get("label", ""))
        if not app_id or app_id in seen_ids:
            continue
        seen_ids.add(app_id)

        if selection.mode == "ids" and app_id not in id_set:
            continue
        if selection.mode == "labels" and app_label not in label_set:
            continue
        if app_id in exclude_ids or app_label in exclude_labels:
            continue
        if statuses and str(app.get("status", "")).upper() not in statuses:
            continue
        if sign_on_modes and str(app.get("signOnMode", "")).upper() not in sign_on_modes:
            continue
        selected.append(app)

    if selection.mode == "labels":
        found = {str(app.get("label", "")) for app in selected}
        missing = sorted(label_set - found)
        for label in missing:
            warnings.append(f"No selected app matched label: {label}")

    if selection.mode == "ids":
        found = {str(app.get("id", "")) for app in selected}
        missing = sorted(id_set - found)
        for app_id in missing:
            warnings.append(f"No selected app matched id: {app_id}")

    if options.max_apps is not None and len(selected) > options.max_apps:
        warnings.append(f"Selected app count {len(selected)} exceeds maxApps {options.max_apps}; export will be limited")
        selected = selected[: options.max_apps]

    return selected, warnings


def user_assignment_row(app: dict[str, Any], assignment: dict[str, Any], include_profile: bool = False) -> dict[str, Any]:
    credentials = assignment.get("credentials") if isinstance(assignment.get("credentials"), dict) else {}
    profile = assignment.get("profile") if isinstance(assignment.get("profile"), dict) else {}
    scope = assignment.get("scope")
    if isinstance(scope, list):
        scope_text = ";".join(str(item) for item in scope)
    else:
        scope_text = str(scope or "")
    row = {
        **app_basic(app),
        "assignmentType": "USER",
        "userId": assignment.get("id", ""),
        "userName": credentials.get("userName") or profile.get("login") or profile.get("email") or "",
        "assignmentStatus": assignment.get("status", ""),
        "created": assignment.get("created", ""),
        "lastUpdated": assignment.get("lastUpdated", ""),
        "scope": scope_text,
        "syncState": assignment.get("syncState", ""),
    }
    if include_profile:
        row.update(scalar_profile_fields(profile, "userProfile_"))
    return row


def group_assignment_row(app: dict[str, Any], assignment: dict[str, Any], include_profile: bool = False) -> dict[str, Any]:
    profile = assignment.get("profile") if isinstance(assignment.get("profile"), dict) else {}
    embedded = assignment.get("_embedded") if isinstance(assignment.get("_embedded"), dict) else {}
    group = embedded.get("group") if isinstance(embedded.get("group"), dict) else {}
    group_profile = group.get("profile") if isinstance(group.get("profile"), dict) else {}
    row = {
        **app_basic(app),
        "assignmentType": "GROUP",
        "groupId": assignment.get("id", "") or group.get("id", ""),
        "groupName": profile.get("name") or group_profile.get("name") or assignment.get("name", ""),
        "groupType": group.get("type", ""),
        "priority": assignment.get("priority", ""),
        "created": assignment.get("created", ""),
        "lastUpdated": assignment.get("lastUpdated", ""),
    }
    if include_profile:
        combined_profile = dict(group_profile)
        combined_profile.update(profile)
        row.update(scalar_profile_fields(combined_profile, "groupProfile_"))
    return row


def summary_row(app: dict[str, Any], user_count: int, group_count: int, error_count: int) -> dict[str, Any]:
    return {
        **app_basic(app),
        "assignedUserCount": user_count,
        "assignedGroupCount": group_count,
        "errorCount": error_count,
    }
