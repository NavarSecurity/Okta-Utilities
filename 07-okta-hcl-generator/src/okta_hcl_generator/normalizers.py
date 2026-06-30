from __future__ import annotations

from typing import Any


def as_list(data: Any) -> list[Any]:
    if data is None:
        return []
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        # Common wrapped backup/API shapes.
        for key in (
            "items",
            "data",
            "applications",
            "groups",
            "trustedOrigins",
            "networkZones",
            "zones",
            "identityProviders",
            "idps",
            "brands",
            "domains",
            "authenticators",
        ):
            if isinstance(data.get(key), list):
                return data[key]
        return [data]
    return []


def normalize_domains(data: Any) -> list[dict[str, Any]]:
    if isinstance(data, dict) and isinstance(data.get("domains"), list):
        return [item for item in data["domains"] if isinstance(item, dict)]
    if isinstance(data, list):
        out: list[dict[str, Any]] = []
        for item in data:
            if isinstance(item, dict) and isinstance(item.get("domains"), list):
                out.extend([child for child in item["domains"] if isinstance(child, dict)])
            elif isinstance(item, dict):
                out.append(item)
        return out
    return []


def normalize_authorization_servers(data: Any) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Return top-level auth servers and details grouped by auth server ID.

    Supports both flat arrays and backup wrapper shape:
    {
      "authorizationServers": [...],
      "detailsByAuthorizationServerId": {"aus...": {...}}
    }
    """
    if isinstance(data, dict):
        servers = data.get("authorizationServers") or data.get("authorization_servers") or []
        details = data.get("detailsByAuthorizationServerId") or data.get("details_by_authorization_server_id") or {}
        return [s for s in as_list(servers) if isinstance(s, dict)], details if isinstance(details, dict) else {}
    return [s for s in as_list(data) if isinstance(s, dict)], {}


def normalize_policies(data: Any) -> list[dict[str, Any]]:
    if isinstance(data, dict) and isinstance(data.get("policyTypes"), dict):
        out: list[dict[str, Any]] = []
        for policy_type, record in data["policyTypes"].items():
            if isinstance(record, dict) and isinstance(record.get("policies"), list):
                for policy in record["policies"]:
                    if isinstance(policy, dict):
                        normalized = dict(policy)
                        normalized.setdefault("type", policy_type)
                        out.append(normalized)
        return out
    return [p for p in as_list(data) if isinstance(p, dict)]


def normalize_applications(data: Any) -> list[dict[str, Any]]:
    return [a for a in as_list(data) if isinstance(a, dict)]


def normalize_groups(data: Any) -> list[dict[str, Any]]:
    return [g for g in as_list(data) if isinstance(g, dict)]


def normalize_trusted_origins(data: Any) -> list[dict[str, Any]]:
    if isinstance(data, dict) and isinstance(data.get("trustedOrigins"), list):
        return [item for item in data["trustedOrigins"] if isinstance(item, dict)]
    return [o for o in as_list(data) if isinstance(o, dict)]


def normalize_network_zones(data: Any) -> list[dict[str, Any]]:
    if isinstance(data, dict) and isinstance(data.get("zones"), list):
        return [item for item in data["zones"] if isinstance(item, dict)]
    return [z for z in as_list(data) if isinstance(z, dict)]


def normalize_identity_providers(data: Any) -> list[dict[str, Any]]:
    return [i for i in as_list(data) if isinstance(i, dict)]
