from __future__ import annotations

from typing import Any


def get_nested(data: dict[str, Any], path: list[str], default: Any = None) -> Any:
    current: Any = data
    for part in path:
        if not isinstance(current, dict) or part not in current:
            return default
        current = current[part]
    return current


def idp_type(idp: dict[str, Any]) -> str:
    return str(idp.get("type") or "UNKNOWN").upper()


def idp_status(idp: dict[str, Any]) -> str:
    return str(idp.get("status") or "UNKNOWN").upper()


def should_include_idp(idp: dict[str, Any], include_inactive: bool, types: list[str], statuses: list[str]) -> bool:
    current_type = idp_type(idp)
    current_status = idp_status(idp)

    if not include_inactive and current_status != "ACTIVE":
        return False
    if types and current_type not in {item.upper() for item in types}:
        return False
    if statuses and current_status not in {item.upper() for item in statuses}:
        return False
    return True


def summarize_idp(idp: dict[str, Any]) -> dict[str, Any]:
    protocol = idp.get("protocol") or {}
    endpoints = protocol.get("endpoints") or {}
    credentials = protocol.get("credentials") or {}
    client = credentials.get("client") or {}
    signing = credentials.get("signing") or {}
    policy = idp.get("policy") or {}
    account_link = policy.get("accountLink") or {}
    provisioning = policy.get("provisioning") or {}

    return {
        "id": idp.get("id", ""),
        "name": idp.get("name", ""),
        "type": idp.get("type", ""),
        "status": idp.get("status", ""),
        "protocolType": protocol.get("type", ""),
        "issuerMode": idp.get("issuerMode", ""),
        "issuer": get_nested(protocol, ["credentials", "trust", "issuer"], ""),
        "clientId": client.get("client_id", client.get("clientId", "")),
        "authorizationUrl": endpoints.get("authorization", {}).get("url", "") if isinstance(endpoints.get("authorization"), dict) else "",
        "tokenUrl": endpoints.get("token", {}).get("url", "") if isinstance(endpoints.get("token"), dict) else "",
        "jwksUrl": endpoints.get("jwks", {}).get("url", "") if isinstance(endpoints.get("jwks"), dict) else "",
        "ssoUrl": endpoints.get("sso", {}).get("url", "") if isinstance(endpoints.get("sso"), dict) else "",
        "signatureAlgorithm": signing.get("algorithm", ""),
        "accountLinkFilter": account_link.get("filter", ""),
        "accountLinkAction": account_link.get("action", ""),
        "provisioningAction": provisioning.get("action", ""),
        "created": idp.get("created", ""),
        "lastUpdated": idp.get("lastUpdated", ""),
    }


def summarize_key(key: dict[str, Any]) -> dict[str, Any]:
    return {
        "kid": key.get("kid", key.get("id", "")),
        "kty": key.get("kty", ""),
        "use": key.get("use", ""),
        "alg": key.get("alg", ""),
        "status": key.get("status", ""),
        "created": key.get("created", ""),
        "lastUpdated": key.get("lastUpdated", ""),
        "expiresAt": key.get("expiresAt", ""),
    }


def count_by_field(items: list[dict[str, Any]], field: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in items:
        value = str(item.get(field) or "UNKNOWN")
        counts[value] = counts.get(value, 0) + 1
    return dict(sorted(counts.items()))
