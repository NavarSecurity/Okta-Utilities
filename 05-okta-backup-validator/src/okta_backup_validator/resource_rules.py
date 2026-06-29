from __future__ import annotations

from typing import Any

# Required fields are intentionally conservative. The validator should flag missing
# fields that make migration/diff/restore unreliable without overfitting to every
# Okta response variant.
RESOURCE_RULES: dict[str, dict[str, Any]] = {
    "org": {"shape": "dict", "required": []},
    "applications": {"shape": "list", "required": ["id", "label", "name", "status"]},
    "groups": {"shape": "list", "required": ["id", "profile"]},
    "group_rules": {"shape": "list", "required": ["id", "name", "status", "conditions", "actions"]},
    "identity_providers": {"shape": "list", "required": ["id", "name", "type", "status"]},
    "event_hooks": {"shape": "list", "required": ["id", "name", "status", "events", "channel"]},
    "inline_hooks": {"shape": "list", "required": ["id", "name", "type", "status", "channel"]},
    "network_zones": {"shape": "list", "required": ["id", "name", "type", "status"]},
    "trusted_origins": {"shape": "list", "required": ["id", "name", "origin", "scopes", "status"]},
    "brands": {"shape": "list", "required": ["id"]},
    "domains": {"shape": "list", "required": ["id", "domain"]},
    "authenticators": {"shape": "list", "required": ["id", "key", "name", "status", "type"]},
    "features": {"shape": "list", "required": ["id", "name", "status"]},
    "user_schema": {"shape": "dict", "required": []},
}

POLICIES_REQUIRED_FIELDS = ["id", "name", "type", "status"]
AUTH_SERVER_REQUIRED_FIELDS = ["id", "name", "status"]


def normalize_resource_records(resource: str, data: Any) -> Any:
    """Return the list of resource records that should be validated.

    Most backup files are written as a flat JSON array. A few Okta endpoints return
    wrapper objects instead. The Domains API can be captured as either:

    - [{"id": "default", "domain": "example.okta.com"}]
    - {"domains": [{...}]}
    - [{"domains": [{...}]}]

    The validator should validate the actual domain records, not the wrapper.
    """
    if resource != "domains":
        return data

    if isinstance(data, dict) and isinstance(data.get("domains"), list):
        return data["domains"]

    if isinstance(data, list):
        normalized: list[Any] = []
        for item in data:
            if isinstance(item, dict) and isinstance(item.get("domains"), list):
                normalized.extend(item["domains"])
            else:
                normalized.append(item)
        return normalized

    return data


def count_objects(data: Any, resource: str | None = None) -> int:
    if resource:
        normalized = normalize_resource_records(resource, data)
        if normalized is not data:
            return count_objects(normalized)

    if isinstance(data, list):
        return len(data)
    if isinstance(data, dict):
        if "authorizationServers" in data and isinstance(data["authorizationServers"], list):
            return len(data["authorizationServers"])
        if "policyTypes" in data and isinstance(data["policyTypes"], dict):
            return sum(
                len(type_record.get("policies", []))
                for type_record in data["policyTypes"].values()
                if isinstance(type_record, dict)
            )
        return 1
    return 0 if data is None else 1


def missing_fields(obj: dict[str, Any], required: list[str]) -> list[str]:
    return [field for field in required if field not in obj or obj.get(field) in (None, "")]
