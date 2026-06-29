from __future__ import annotations

from copy import deepcopy
from typing import Any
import json


def _list_from_possible_wrapper(data: Any, wrapper_keys: list[str]) -> list[Any]:
    if data is None:
        return []
    if isinstance(data, list):
        result: list[Any] = []
        for item in data:
            if isinstance(item, dict):
                found_wrapper = False
                for key in wrapper_keys:
                    if isinstance(item.get(key), list):
                        result.extend(item[key])
                        found_wrapper = True
                        break
                if not found_wrapper:
                    result.append(item)
            else:
                result.append(item)
        return result
    if isinstance(data, dict):
        for key in wrapper_keys:
            if isinstance(data.get(key), list):
                return data[key]
        return [data]
    return []


def _authorization_servers(data: Any) -> list[dict[str, Any]]:
    servers = _list_from_possible_wrapper(data, ["authorizationServers", "items"])

    # Enrich authorization servers with nested detail sections when present.
    detail_maps: dict[str, dict[str, Any]] = {}
    if isinstance(data, dict):
        for key, value in data.items():
            if key.startswith("detailsBy") and isinstance(value, dict):
                for server_id, details in value.items():
                    if isinstance(details, dict):
                        detail_maps.setdefault(server_id, {}).update({key: details})
    if isinstance(data, list):
        for item in data:
            if isinstance(item, dict):
                for key, value in item.items():
                    if key.startswith("detailsBy") and isinstance(value, dict):
                        for server_id, details in value.items():
                            if isinstance(details, dict):
                                detail_maps.setdefault(server_id, {}).update({key: details})

    enriched: list[dict[str, Any]] = []
    for server in servers:
        if isinstance(server, dict):
            record = deepcopy(server)
            server_id = str(record.get("id", ""))
            if server_id and server_id in detail_maps:
                record["_details"] = detail_maps[server_id]
            enriched.append(record)
    return enriched


def _policies(data: Any) -> list[dict[str, Any]]:
    if not isinstance(data, dict):
        return _list_from_possible_wrapper(data, ["policies", "items"])

    policy_types = data.get("policyTypes")
    if not isinstance(policy_types, dict):
        return _list_from_possible_wrapper(data, ["policies", "items"])

    records: list[dict[str, Any]] = []
    for policy_type, type_payload in policy_types.items():
        if not isinstance(type_payload, dict):
            records.append({"_invalidPolicyType": policy_type, "value": type_payload})
            continue
        rules_by_policy_id = type_payload.get("rulesByPolicyId", {})
        for policy in type_payload.get("policies", []) or []:
            if not isinstance(policy, dict):
                continue
            record = deepcopy(policy)
            record["_policyType"] = policy_type
            policy_id = str(record.get("id", ""))
            if isinstance(rules_by_policy_id, dict) and policy_id in rules_by_policy_id:
                record["_rules"] = rules_by_policy_id[policy_id]
            records.append(record)
    return records


def _org(data: Any) -> list[dict[str, Any]]:
    if isinstance(data, dict):
        return [data]
    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]
    return []


def normalize_resource_records(resource: str, data: Any) -> list[dict[str, Any]]:
    if data is None:
        return []
    if resource == "org":
        return _org(data)
    if resource == "policies":
        return _policies(data)
    if resource == "authorization_servers":
        return _authorization_servers(data)
    if resource == "domains":
        return [x for x in _list_from_possible_wrapper(data, ["domains", "items"]) if isinstance(x, dict)]
    if resource == "brands":
        return [x for x in _list_from_possible_wrapper(data, ["brands", "items"]) if isinstance(x, dict)]
    if resource == "authenticators":
        return [x for x in _list_from_possible_wrapper(data, ["authenticators", "items"]) if isinstance(x, dict)]
    if resource == "event_hooks":
        return [x for x in _list_from_possible_wrapper(data, ["eventHooks", "items"]) if isinstance(x, dict)]
    if resource == "inline_hooks":
        return [x for x in _list_from_possible_wrapper(data, ["inlineHooks", "items"]) if isinstance(x, dict)]
    if resource == "network_zones":
        return [x for x in _list_from_possible_wrapper(data, ["zones", "networkZones", "items"]) if isinstance(x, dict)]
    if resource == "trusted_origins":
        return [x for x in _list_from_possible_wrapper(data, ["trustedOrigins", "items"]) if isinstance(x, dict)]
    return [x for x in _list_from_possible_wrapper(data, ["items", resource]) if isinstance(x, dict)]


def natural_key(resource: str, record: dict[str, Any]) -> str:
    if resource == "org":
        return "org"
    if resource == "groups":
        profile = record.get("profile") if isinstance(record.get("profile"), dict) else {}
        return str(profile.get("name") or record.get("name") or record.get("id") or "<missing-group-key>")
    if resource == "applications":
        return str(record.get("label") or record.get("name") or record.get("id") or "<missing-app-key>")
    if resource == "policies":
        return f"{record.get('type') or record.get('_policyType') or 'UNKNOWN'}::{record.get('name') or record.get('id') or '<missing-policy-key>'}"
    if resource == "authorization_servers":
        return str(record.get("name") or record.get("issuer") or record.get("id") or "<missing-authz-server-key>")
    if resource == "trusted_origins":
        return str(record.get("origin") or record.get("name") or record.get("id") or "<missing-trusted-origin-key>")
    if resource == "network_zones":
        return str(record.get("name") or record.get("id") or "<missing-network-zone-key>")
    if resource == "domains":
        return str(record.get("domain") or record.get("id") or "<missing-domain-key>")
    if resource == "identity_providers":
        return str(record.get("name") or record.get("id") or "<missing-idp-key>")
    if resource == "brands":
        return str(record.get("name") or record.get("id") or "<missing-brand-key>")
    if resource == "authenticators":
        return str(record.get("key") or record.get("name") or record.get("type") or record.get("id") or "<missing-authenticator-key>")
    if resource in {"event_hooks", "inline_hooks", "group_rules"}:
        return str(record.get("name") or record.get("id") or f"<missing-{resource}-key>")
    return str(record.get("name") or record.get("label") or record.get("id") or json.dumps(record, sort_keys=True)[:80])


def normalize_for_compare(value: Any, ignore_fields: set[str]) -> Any:
    if isinstance(value, dict):
        normalized = {}
        for key, item in value.items():
            if key in ignore_fields:
                continue
            normalized[key] = normalize_for_compare(item, ignore_fields)
        return {key: normalized[key] for key in sorted(normalized)}
    if isinstance(value, list):
        normalized_list = [normalize_for_compare(item, ignore_fields) for item in value]
        try:
            return sorted(normalized_list, key=lambda x: json.dumps(x, sort_keys=True, default=str))
        except TypeError:
            return normalized_list
    return value


def index_records(resource: str, records: list[dict[str, Any]]) -> tuple[dict[str, dict[str, Any]], dict[str, list[dict[str, Any]]]]:
    index: dict[str, dict[str, Any]] = {}
    duplicates: dict[str, list[dict[str, Any]]] = {}
    for record in records:
        key = natural_key(resource, record)
        if key in index:
            duplicates.setdefault(key, [index[key]]).append(record)
        else:
            index[key] = record
    return index, duplicates
