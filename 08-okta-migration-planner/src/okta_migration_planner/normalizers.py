from __future__ import annotations

import copy
import json
from typing import Any

VOLATILE_KEYS = {
    "id",
    "_links",
    "_embedded",
    "created",
    "lastUpdated",
    "lastMembershipUpdated",
    "lastUpdatedBy",
}

HIGH_RISK_RESOURCES = {
    "policies",
    "identity_providers",
    "event_hooks",
    "inline_hooks",
    "domains",
    "brands",
    "authenticators",
    "profile_schemas",
    "profile_mappings",
}

RESOURCE_FILES = {
    "groups": "groups.json",
    "applications": "applications.json",
    "trusted_origins": "trusted_origins.json",
    "network_zones": "network_zones.json",
    "authorization_servers": "authorization_servers.json",
    "policies": "policies.json",
    "identity_providers": "identity_providers.json",
    "event_hooks": "event_hooks.json",
    "inline_hooks": "inline_hooks.json",
    "domains": "domains.json",
    "brands": "brands.json",
    "authenticators": "authenticators.json",
}


def is_high_risk(resource: str) -> bool:
    return resource in HIGH_RISK_RESOURCES


def stable_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)


def strip_volatile(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: strip_volatile(val)
            for key, val in value.items()
            if key not in VOLATILE_KEYS and not key.endswith("Id") and key != "brandId"
        }
    if isinstance(value, list):
        return [strip_volatile(item) for item in value]
    return value


def material_fingerprint(item: dict[str, Any]) -> str:
    return stable_json(strip_volatile(copy.deepcopy(item)))


def get_nested(item: dict[str, Any], path: list[str]) -> Any:
    current: Any = item
    for part in path:
        if not isinstance(current, dict):
            return None
        current = current.get(part)
    return current


def normalize_resource(resource: str, data: Any) -> list[dict[str, Any]]:
    if data is None:
        return []

    if resource == "groups":
        return _as_dict_list(data)
    if resource == "applications":
        return _as_dict_list(data)
    if resource == "trusted_origins":
        return _unwrap_list(data, "trustedOrigins")
    if resource == "network_zones":
        return _unwrap_list(data, "zones")
    if resource == "authorization_servers":
        return _normalize_authorization_servers(data)
    if resource == "policies":
        return _normalize_policies(data)
    if resource == "identity_providers":
        return _unwrap_list(data, "identityProviders")
    if resource == "domains":
        return _unwrap_list(data, "domains")
    if resource == "brands":
        return _unwrap_list(data, "brands")
    if resource == "event_hooks":
        return _unwrap_list(data, "eventHooks")
    if resource == "inline_hooks":
        return _unwrap_list(data, "inlineHooks")
    if resource == "authenticators":
        return _unwrap_list(data, "authenticators")
    return _as_dict_list(data)


def _as_dict_list(data: Any) -> list[dict[str, Any]]:
    if isinstance(data, dict):
        return [data]
    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]
    return []


def _unwrap_list(data: Any, key: str) -> list[dict[str, Any]]:
    if isinstance(data, dict) and isinstance(data.get(key), list):
        return [item for item in data[key] if isinstance(item, dict)]
    if isinstance(data, list):
        result: list[dict[str, Any]] = []
        for item in data:
            if isinstance(item, dict) and isinstance(item.get(key), list):
                result.extend([inner for inner in item[key] if isinstance(inner, dict)])
            elif isinstance(item, dict):
                result.append(item)
        return result
    return []


def _normalize_authorization_servers(data: Any) -> list[dict[str, Any]]:
    # The backup utility may write authorization server data as:
    # [{"authorizationServers": [...], "detailsByAuthorizationServerId": {...}}]
    # or {"authorizationServers": [...]} or a flat list.
    return _unwrap_list(data, "authorizationServers")


def _normalize_policies(data: Any) -> list[dict[str, Any]]:
    if isinstance(data, dict) and isinstance(data.get("policyTypes"), dict):
        result: list[dict[str, Any]] = []
        for policy_type, record in data["policyTypes"].items():
            if not isinstance(record, dict):
                continue
            policies = record.get("policies", [])
            if not isinstance(policies, list):
                continue
            for policy in policies:
                if isinstance(policy, dict):
                    clone = copy.deepcopy(policy)
                    clone.setdefault("type", policy_type)
                    clone["_migrationPolicyType"] = policy_type
                    result.append(clone)
        return result
    return _as_dict_list(data)


def natural_key(resource: str, item: dict[str, Any]) -> str | None:
    if resource == "groups":
        return _first_string(get_nested(item, ["profile", "name"]), item.get("name"))
    if resource == "applications":
        return _first_string(item.get("label"), item.get("name"))
    if resource == "trusted_origins":
        return _first_string(item.get("origin"), item.get("name"))
    if resource == "network_zones":
        return _first_string(item.get("name"))
    if resource == "authorization_servers":
        return _first_string(item.get("name"), item.get("audiences"))
    if resource == "policies":
        policy_type = item.get("_migrationPolicyType") or item.get("type") or "UNKNOWN"
        name = item.get("name")
        if isinstance(name, str) and name.strip():
            return f"{policy_type}::{name}"
        return None
    if resource == "identity_providers":
        return _first_string(item.get("name"), item.get("type"))
    if resource == "domains":
        return _first_string(item.get("domain"), item.get("id"))
    if resource == "brands":
        return _first_string(item.get("name"), item.get("id"))
    if resource in {"event_hooks", "inline_hooks", "authenticators"}:
        return _first_string(item.get("name"), item.get("key"), item.get("id"))
    return _first_string(item.get("name"), item.get("label"), item.get("id"))


def display_name(resource: str, item: dict[str, Any]) -> str:
    key = natural_key(resource, item)
    if key:
        return key
    return str(item.get("id") or item.get("name") or item.get("label") or "<unknown>")


def source_id(item: dict[str, Any]) -> str:
    value = item.get("id")
    return str(value) if value is not None else ""


def _first_string(*values: Any) -> str | None:
    for value in values:
        if isinstance(value, str) and value.strip():
            return value.strip()
        if isinstance(value, list) and value:
            return ",".join(str(v) for v in value)
    return None
