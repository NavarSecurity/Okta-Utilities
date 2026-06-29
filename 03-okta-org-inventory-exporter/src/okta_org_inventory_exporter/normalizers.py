from __future__ import annotations

from typing import Any


def as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, dict):
        return [value]
    return []


def compact_join(values: Any) -> str:
    if not isinstance(values, list):
        return ""
    return ";".join(str(v) for v in values if v is not None)


def nested_get(obj: dict[str, Any], path: str, default: Any = None) -> Any:
    cur: Any = obj
    for part in path.split("."):
        if not isinstance(cur, dict):
            return default
        cur = cur.get(part)
    return cur if cur is not None else default


def load_records(resource: str, data: Any) -> list[dict[str, Any]]:
    if resource == "policies":
        return normalize_policies(data)
    if resource == "authorization_servers":
        return normalize_authorization_servers(data)
    if resource == "domains":
        return normalize_domains(data)
    if resource == "org":
        return normalize_org(data)
    return [x for x in as_list(data) if isinstance(x, dict)]


def normalize_org(data: Any) -> list[dict[str, Any]]:
    if isinstance(data, dict):
        return [data]
    if isinstance(data, list):
        return [x for x in data if isinstance(x, dict)]
    return []


def normalize_domains(data: Any) -> list[dict[str, Any]]:
    if isinstance(data, dict) and isinstance(data.get("domains"), list):
        return [x for x in data["domains"] if isinstance(x, dict)]
    if isinstance(data, list):
        records: list[dict[str, Any]] = []
        for item in data:
            if isinstance(item, dict) and isinstance(item.get("domains"), list):
                records.extend(x for x in item["domains"] if isinstance(x, dict))
            elif isinstance(item, dict):
                records.append(item)
        return records
    return []


def normalize_authorization_servers(data: Any) -> list[dict[str, Any]]:
    if isinstance(data, dict):
        servers = data.get("authorizationServers") or data.get("authorization_servers") or data.get("items")
        if isinstance(servers, list):
            return [x for x in servers if isinstance(x, dict)]
        return [data] if data.get("id") or data.get("name") else []
    if isinstance(data, list):
        records: list[dict[str, Any]] = []
        for item in data:
            if isinstance(item, dict) and isinstance(item.get("authorizationServers"), list):
                records.extend(x for x in item["authorizationServers"] if isinstance(x, dict))
            elif isinstance(item, dict):
                records.append(item)
        return records
    return []


def normalize_policies(data: Any) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    if isinstance(data, dict) and isinstance(data.get("policyTypes"), dict):
        for policy_type, wrapper in data["policyTypes"].items():
            if not isinstance(wrapper, dict):
                continue
            policies = wrapper.get("policies")
            rules_by_policy_id = wrapper.get("rulesByPolicyId", {})
            if not isinstance(policies, list):
                continue
            for policy in policies:
                if not isinstance(policy, dict):
                    continue
                row = dict(policy)
                row["policyType"] = policy_type
                if isinstance(rules_by_policy_id, dict):
                    rules = rules_by_policy_id.get(policy.get("id"), [])
                    row["ruleCount"] = len(rules) if isinstance(rules, list) else 0
                else:
                    row["ruleCount"] = 0
                records.append(row)
        return records
    return [x for x in as_list(data) if isinstance(x, dict)]


def summarize(records: list[dict[str, Any]], type_field: str = "type") -> dict[str, Any]:
    by_status: dict[str, int] = {}
    by_type: dict[str, int] = {}
    for item in records:
        status = item.get("status") or item.get("validationStatus") or item.get("lifecycleStatus")
        typ = item.get(type_field) or item.get("signOnMode") or item.get("name")
        if status:
            by_status[str(status)] = by_status.get(str(status), 0) + 1
        if typ:
            by_type[str(typ)] = by_type.get(str(typ), 0) + 1
    return {"count": len(records), "byStatus": by_status, "byType": by_type}


def inventory_rows(resource: str, records: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[str]]:
    builders = {
        "org": _org_row,
        "applications": _application_row,
        "groups": _group_row,
        "group_rules": _group_rule_row,
        "policies": _policy_row,
        "identity_providers": _idp_row,
        "authorization_servers": _authz_server_row,
        "trusted_origins": _trusted_origin_row,
        "network_zones": _network_zone_row,
        "domains": _domain_row,
        "brands": _brand_row,
        "authenticators": _authenticator_row,
        "event_hooks": _hook_row,
        "inline_hooks": _hook_row,
    }
    builder = builders.get(resource, _generic_row)
    rows = [builder(x) for x in records]
    fieldnames = list(rows[0].keys()) if rows else _default_fields(resource)
    return rows, fieldnames


def _default_fields(resource: str) -> list[str]:
    defaults = {
        "applications": ["id", "label", "name", "signOnMode", "status", "created", "lastUpdated"],
        "groups": ["id", "name", "description", "type", "created", "lastUpdated"],
        "policies": ["id", "name", "policyType", "type", "status", "priority", "ruleCount"],
        "domains": ["id", "domain", "brandId", "certificateSourceType", "validationStatus"],
    }
    return defaults.get(resource, ["id", "name", "type", "status", "created", "lastUpdated"])


def _generic_row(x: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": x.get("id", ""),
        "name": x.get("name") or x.get("label") or x.get("domain") or x.get("origin") or "",
        "type": x.get("type") or x.get("name") or "",
        "status": x.get("status") or x.get("validationStatus") or "",
        "created": x.get("created", ""),
        "lastUpdated": x.get("lastUpdated", ""),
    }


def _org_row(x: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": x.get("id", ""),
        "orgType": x.get("orgType", ""),
        "companyName": x.get("companyName", ""),
        "website": x.get("website", ""),
        "status": x.get("status", ""),
        "created": x.get("created", ""),
        "lastUpdated": x.get("lastUpdated", ""),
    }


def _application_row(x: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": x.get("id", ""),
        "label": x.get("label", ""),
        "name": x.get("name", ""),
        "signOnMode": x.get("signOnMode", ""),
        "status": x.get("status", ""),
        "created": x.get("created", ""),
        "lastUpdated": x.get("lastUpdated", ""),
        "assigned": nested_get(x, "_embedded.userAssignment", ""),
        "redirectUriCount": len(nested_get(x, "settings.oauthClient.redirect_uris", []) or []),
        "grantTypes": compact_join(nested_get(x, "settings.oauthClient.grant_types", []) or []),
    }


def _group_row(x: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": x.get("id", ""),
        "name": nested_get(x, "profile.name", x.get("name", "")),
        "description": nested_get(x, "profile.description", x.get("description", "")),
        "type": x.get("type", ""),
        "created": x.get("created", ""),
        "lastUpdated": x.get("lastUpdated", ""),
        "lastMembershipUpdated": x.get("lastMembershipUpdated", ""),
    }


def _group_rule_row(x: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": x.get("id", ""),
        "name": x.get("name", ""),
        "status": x.get("status", ""),
        "type": x.get("type", ""),
        "created": x.get("created", ""),
        "lastUpdated": x.get("lastUpdated", ""),
        "targetGroupIds": compact_join(nested_get(x, "actions.assignUserToGroups.groupIds", []) or []),
    }


def _policy_row(x: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": x.get("id", ""),
        "name": x.get("name", ""),
        "policyType": x.get("policyType", x.get("type", "")),
        "type": x.get("type", ""),
        "status": x.get("status", ""),
        "priority": x.get("priority", ""),
        "system": x.get("system", ""),
        "ruleCount": x.get("ruleCount", 0),
        "created": x.get("created", ""),
        "lastUpdated": x.get("lastUpdated", ""),
    }


def _idp_row(x: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": x.get("id", ""),
        "name": x.get("name", ""),
        "type": x.get("type", ""),
        "status": x.get("status", ""),
        "issuerMode": x.get("issuerMode", ""),
        "created": x.get("created", ""),
        "lastUpdated": x.get("lastUpdated", ""),
    }


def _authz_server_row(x: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": x.get("id", ""),
        "name": x.get("name", ""),
        "description": x.get("description", ""),
        "status": x.get("status", ""),
        "issuer": x.get("issuer", ""),
        "audiences": compact_join(x.get("audiences", []) or []),
        "created": x.get("created", ""),
        "lastUpdated": x.get("lastUpdated", ""),
    }


def _trusted_origin_row(x: dict[str, Any]) -> dict[str, Any]:
    scopes = x.get("scopes", []) or []
    scope_types = [s.get("type") for s in scopes if isinstance(s, dict)]
    return {
        "id": x.get("id", ""),
        "name": x.get("name", ""),
        "origin": x.get("origin", ""),
        "status": x.get("status", ""),
        "scopes": compact_join(scope_types),
        "created": x.get("created", ""),
        "lastUpdated": x.get("lastUpdated", ""),
    }


def _network_zone_row(x: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": x.get("id", ""),
        "name": x.get("name", ""),
        "type": x.get("type", ""),
        "status": x.get("status", ""),
        "usage": x.get("usage", ""),
        "gatewayCount": len(x.get("gateways", []) or []),
        "proxyCount": len(x.get("proxies", []) or []),
        "created": x.get("created", ""),
        "lastUpdated": x.get("lastUpdated", ""),
    }


def _domain_row(x: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": x.get("id", ""),
        "domain": x.get("domain", ""),
        "brandId": x.get("brandId", ""),
        "certificateSourceType": x.get("certificateSourceType", ""),
        "validationStatus": x.get("validationStatus", ""),
    }


def _brand_row(x: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": x.get("id", ""),
        "name": x.get("name", ""),
        "isDefault": x.get("isDefault", ""),
        "removePoweredByOkta": x.get("removePoweredByOkta", ""),
        "created": x.get("created", ""),
        "lastUpdated": x.get("lastUpdated", ""),
    }


def _authenticator_row(x: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": x.get("id", ""),
        "name": x.get("name", ""),
        "key": x.get("key", ""),
        "type": x.get("type", ""),
        "status": x.get("status", ""),
        "created": x.get("created", ""),
        "lastUpdated": x.get("lastUpdated", ""),
    }


def _hook_row(x: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": x.get("id", ""),
        "name": x.get("name", ""),
        "type": x.get("type", ""),
        "status": x.get("status", ""),
        "channelType": nested_get(x, "channel.type", ""),
        "uri": nested_get(x, "channel.config.uri", ""),
        "created": x.get("created", ""),
        "lastUpdated": x.get("lastUpdated", ""),
    }
