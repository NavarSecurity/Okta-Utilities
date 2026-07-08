from __future__ import annotations

from .config import GroupRuleConfig


def build_group_rule_payload(rule: GroupRuleConfig, target_group_ids: list[str]) -> dict:
    if not target_group_ids:
        raise ValueError(f"Rule {rule.name!r} has no resolved target groups.")

    return {
        "type": "group_rule",
        "name": rule.name,
        "status": "INACTIVE",
        "conditions": {
            "people": {
                "users": {
                    "exclude": rule.exclude_user_ids
                },
                "groups": {
                    "exclude": rule.exclude_group_ids
                }
            },
            "expression": {
                "type": "urn:okta:expression:1.0",
                "value": rule.expression
            }
        },
        "actions": {
            "assignUserToGroups": {
                "groupIds": target_group_ids
            }
        },
        "profile": {
            "description": rule.description
        }
    }
