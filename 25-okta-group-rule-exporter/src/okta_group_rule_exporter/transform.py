from __future__ import annotations

import json
from typing import Any


def group_name_map(rule: dict[str, Any]) -> dict[str, str]:
    embedded = rule.get("_embedded") or {}
    mapping = embedded.get("groupIdToGroupName") or embedded.get("groupIdToGroupNames") or {}
    if isinstance(mapping, dict):
        return {str(k): str(v) for k, v in mapping.items()}
    return {}


def filter_rules(rules: list[dict[str, Any]], rule_ids: list[str], statuses: list[str], name_contains: str) -> list[dict[str, Any]]:
    ids = {x for x in rule_ids if x}
    status_set = {x.upper() for x in statuses if x}
    needle = (name_contains or "").lower()
    filtered: list[dict[str, Any]] = []
    for rule in rules:
        if ids and rule.get("id") not in ids:
            continue
        if status_set and str(rule.get("status", "")).upper() not in status_set:
            continue
        if needle and needle not in str(rule.get("name", "")).lower():
            continue
        filtered.append(rule)
    return filtered


def rule_summary_row(rule: dict[str, Any]) -> dict[str, Any]:
    conditions = rule.get("conditions") or {}
    actions = rule.get("actions") or {}
    expression = conditions.get("expression") or {}
    group_membership = conditions.get("groupMembership") or {}
    assign = actions.get("assignUserToGroups") or {}
    target_group_ids = assign.get("groupIds") or []
    names = group_name_map(rule)
    target_group_names = [names.get(gid, "") for gid in target_group_ids]

    return {
        "id": rule.get("id", ""),
        "name": rule.get("name", ""),
        "status": rule.get("status", ""),
        "priority": rule.get("priority", ""),
        "created": rule.get("created", ""),
        "lastUpdated": rule.get("lastUpdated", ""),
        "expressionType": expression.get("type", ""),
        "expressionValue": expression.get("value", ""),
        "targetGroupIds": ";".join(map(str, target_group_ids)),
        "targetGroupNames": ";".join(target_group_names),
        "sourceGroupInclude": ";".join(map(str, group_membership.get("include", []) or [])),
        "sourceGroupExclude": ";".join(map(str, group_membership.get("exclude", []) or [])),
        "conditionsJson": json.dumps(conditions, separators=(",", ":"), sort_keys=True),
        "actionsJson": json.dumps(actions, separators=(",", ":"), sort_keys=True),
    }


def condition_rows(rule: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    conditions = rule.get("conditions") or {}
    expression = conditions.get("expression") or {}
    if expression:
        rows.append({
            "ruleId": rule.get("id", ""),
            "ruleName": rule.get("name", ""),
            "conditionType": "expression",
            "conditionKey": expression.get("type", ""),
            "conditionValue": expression.get("value", ""),
        })
    membership = conditions.get("groupMembership") or {}
    for direction in ["include", "exclude"]:
        for group_id in membership.get(direction, []) or []:
            rows.append({
                "ruleId": rule.get("id", ""),
                "ruleName": rule.get("name", ""),
                "conditionType": "groupMembership",
                "conditionKey": direction,
                "conditionValue": group_id,
            })
    people = conditions.get("people") or {}
    users = people.get("users") or {}
    for direction in ["include", "exclude"]:
        for user_id in users.get(direction, []) or []:
            rows.append({
                "ruleId": rule.get("id", ""),
                "ruleName": rule.get("name", ""),
                "conditionType": "people.users",
                "conditionKey": direction,
                "conditionValue": user_id,
            })
    if not rows:
        rows.append({
            "ruleId": rule.get("id", ""),
            "ruleName": rule.get("name", ""),
            "conditionType": "none_or_unparsed",
            "conditionKey": "",
            "conditionValue": json.dumps(conditions, separators=(",", ":"), sort_keys=True),
        })
    return rows


def target_group_rows(rule: dict[str, Any]) -> list[dict[str, Any]]:
    names = group_name_map(rule)
    actions = rule.get("actions") or {}
    assign = actions.get("assignUserToGroups") or {}
    group_ids = assign.get("groupIds") or []
    return [{
        "ruleId": rule.get("id", ""),
        "ruleName": rule.get("name", ""),
        "targetGroupId": group_id,
        "targetGroupName": names.get(str(group_id), ""),
    } for group_id in group_ids]


def action_rows(rule: dict[str, Any]) -> list[dict[str, Any]]:
    actions = rule.get("actions") or {}
    rows: list[dict[str, Any]] = []
    for key, value in actions.items():
        rows.append({
            "ruleId": rule.get("id", ""),
            "ruleName": rule.get("name", ""),
            "actionType": key,
            "actionJson": json.dumps(value, separators=(",", ":"), sort_keys=True),
        })
    if not rows:
        rows.append({"ruleId": rule.get("id", ""), "ruleName": rule.get("name", ""), "actionType": "none", "actionJson": ""})
    return rows
