from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, List

VALID_STATUSES = {"ACTIVE", "INACTIVE"}
VALID_ISSUER_MODES = {"ORG_URL", "CUSTOM_URL", "DYNAMIC"}
VALID_SCOPE_CONSENT = {"REQUIRED", "IMPLICIT", "FLEXIBLE"}
VALID_METADATA_PUBLISH = {"ALL_CLIENTS", "NO_CLIENTS"}
VALID_CLAIM_TYPES = {"IDENTITY", "RESOURCE"}
VALID_VALUE_TYPES = {"EXPRESSION", "GROUPS", "SYSTEM"}
VALID_SIGNATURE_ALGORITHMS = {"RS256", "RS384", "RS512", "ES256", "ES384", "ES512"}
# Okta authorization server access policy rule conditions do not accept refresh_token.
# Refresh token behavior is controlled by token lifetime/window action fields, not by
# putting refresh_token in conditions.grantTypes.include.
DISALLOWED_POLICY_RULE_GRANT_TYPES = {"refresh_token"}


def _validate_people_condition(people: Dict[str, Any] | None, rule_name: str) -> None:
    """Validate common Okta mediation rule people condition mistakes.

    Okta treats EVERYONE as a group condition value for authorization server
    policy rules. If EVERYONE is placed under users.include, Okta tries to
    resolve it as a concrete user and returns: Resource(s) not found: EVERYONE (User).
    """
    if not people:
        return
    if not isinstance(people, dict):
        raise ValueError(f"rule '{rule_name}' people condition must be an object when provided")
    users_include = people.get("users", {}).get("include", [])
    if "EVERYONE" in users_include:
        raise ValueError(
            f"rule '{rule_name}' has invalid people.users.include value: EVERYONE. "
            "For Okta authorization server policy rules, put EVERYONE under "
            "people.groups.include and leave people.users.include empty unless you are "
            "listing real Okta user IDs."
        )


def _copy_known(source: Dict[str, Any], keys: List[str]) -> Dict[str, Any]:
    return {key: deepcopy(source[key]) for key in keys if key in source and source[key] is not None}


def validate_authorization_server(server: Dict[str, Any]) -> None:
    if not server.get("name"):
        raise ValueError("authorization server name is required")
    audiences = server.get("audiences")
    if not isinstance(audiences, list) or not audiences:
        raise ValueError(f"authorization server '{server.get('name')}' requires at least one audience")
    if server.get("status") and server["status"] not in VALID_STATUSES:
        raise ValueError(f"authorization server '{server['name']}' has invalid status: {server['status']}")
    if server.get("issuerMode") and server["issuerMode"] not in VALID_ISSUER_MODES:
        raise ValueError(f"authorization server '{server['name']}' has invalid issuerMode: {server['issuerMode']}")
    if server.get("credentials") and "signing" in server.get("credentials", {}):
        # Okta may generate signing key material; this utility should not import source-org key IDs.
        raise ValueError(
            f"authorization server '{server['name']}' contains credentials.signing. "
            "Remove source-org signing key details from the build config."
        )


def build_authorization_server_payload(server: Dict[str, Any]) -> Dict[str, Any]:
    validate_authorization_server(server)
    payload = _copy_known(
        server,
        ["name", "description", "audiences", "issuerMode", "status"],
    )
    # Optional advanced fields are passed through only when explicitly provided.
    for optional_key in ["credentials", "accessTokenLifetimeMinutes"]:
        if optional_key in server and server[optional_key] is not None:
            payload[optional_key] = deepcopy(server[optional_key])
    return payload


def validate_scope(scope: Dict[str, Any], server_name: str) -> None:
    if not scope.get("name"):
        raise ValueError(f"scope name is required for authorization server '{server_name}'")
    if scope.get("consent") and scope["consent"] not in VALID_SCOPE_CONSENT:
        raise ValueError(f"scope '{scope['name']}' has invalid consent: {scope['consent']}")
    if scope.get("metadataPublish") and scope["metadataPublish"] not in VALID_METADATA_PUBLISH:
        raise ValueError(f"scope '{scope['name']}' has invalid metadataPublish: {scope['metadataPublish']}")


def build_scope_payload(scope: Dict[str, Any], server_name: str = "") -> Dict[str, Any]:
    validate_scope(scope, server_name)
    payload = _copy_known(
        scope,
        ["name", "displayName", "description", "consent", "metadataPublish", "default", "optional"],
    )
    return payload


def validate_claim(claim: Dict[str, Any], server_name: str) -> None:
    if not claim.get("name"):
        raise ValueError(f"claim name is required for authorization server '{server_name}'")
    if claim.get("claimType") and claim["claimType"] not in VALID_CLAIM_TYPES:
        raise ValueError(f"claim '{claim['name']}' has invalid claimType: {claim['claimType']}")
    if claim.get("valueType") and claim["valueType"] not in VALID_VALUE_TYPES:
        raise ValueError(f"claim '{claim['name']}' has invalid valueType: {claim['valueType']}")
    if claim.get("status") and claim["status"] not in VALID_STATUSES:
        raise ValueError(f"claim '{claim['name']}' has invalid status: {claim['status']}")
    if claim.get("valueType") in {"EXPRESSION", "GROUPS"} and "value" not in claim:
        raise ValueError(f"claim '{claim['name']}' requires value when valueType is {claim.get('valueType')}")


def build_claim_payload(claim: Dict[str, Any], server_name: str = "") -> Dict[str, Any]:
    validate_claim(claim, server_name)
    payload = _copy_known(
        claim,
        [
            "name",
            "status",
            "claimType",
            "valueType",
            "value",
            "conditions",
            "alwaysIncludeInToken",
            "system",
            "group_filter_type",
        ],
    )
    return payload


def validate_policy(policy: Dict[str, Any], server_name: str) -> None:
    if not policy.get("name"):
        raise ValueError(f"policy name is required for authorization server '{server_name}'")
    if policy.get("status") and policy["status"] not in VALID_STATUSES:
        raise ValueError(f"policy '{policy['name']}' has invalid status: {policy['status']}")


def build_policy_payload(policy: Dict[str, Any], server_name: str = "") -> Dict[str, Any]:
    validate_policy(policy, server_name)
    if "rawPayload" in policy:
        return deepcopy(policy["rawPayload"])

    client_whitelist = policy.get("clientWhitelist") or policy.get("clients") or ["ALL_CLIENTS"]
    payload: Dict[str, Any] = {
        "type": "OAUTH_AUTHORIZATION_POLICY",
        "name": policy["name"],
        "description": policy.get("description", policy["name"]),
        "priority": int(policy.get("priority", 1)),
        "status": policy.get("status", "ACTIVE"),
        "conditions": {
            "clients": {
                "include": client_whitelist
            }
        }
    }
    if "conditions" in policy:
        payload["conditions"] = deepcopy(policy["conditions"])
    return payload


def validate_rule(rule: Dict[str, Any], policy_name: str) -> None:
    if not rule.get("name"):
        raise ValueError(f"rule name is required for policy '{policy_name}'")
    if rule.get("status") and rule["status"] not in VALID_STATUSES:
        raise ValueError(f"rule '{rule['name']}' has invalid status: {rule['status']}")

    grant_types = rule.get("grantTypeWhitelist") or rule.get("grantTypes")
    if grant_types is not None:
        if not isinstance(grant_types, list) or not grant_types:
            raise ValueError(
                f"rule '{rule['name']}' grantTypeWhitelist must be a non-empty list when provided"
            )
        disallowed = sorted(set(grant_types).intersection(DISALLOWED_POLICY_RULE_GRANT_TYPES))
        if disallowed:
            raise ValueError(
                f"rule '{rule['name']}' has invalid grantTypeWhitelist value(s): {', '.join(disallowed)}. "
                "Okta authorization server policy rule conditions do not accept refresh_token. "
                "Use authorization_code in grantTypeWhitelist and keep refreshTokenLifetimeMinutes/"
                "refreshTokenWindowMinutes when refresh token lifetime behavior is needed."
            )

    scopes = rule.get("scopeWhitelist") or rule.get("scopes")
    if scopes is not None and (not isinstance(scopes, list) or not scopes):
        raise ValueError(f"rule '{rule['name']}' scopeWhitelist must be a non-empty list when provided")

    _validate_people_condition(rule.get("people"), rule["name"])
    conditions = rule.get("conditions") or {}
    if isinstance(conditions, dict):
        _validate_people_condition(conditions.get("people"), rule["name"])


def build_policy_rule_payload(rule: Dict[str, Any], policy_name: str = "") -> Dict[str, Any]:
    validate_rule(rule, policy_name)
    if "rawPayload" in rule:
        return deepcopy(rule["rawPayload"])

    grant_types = rule.get("grantTypeWhitelist") or rule.get("grantTypes") or ["authorization_code"]
    scopes = rule.get("scopeWhitelist") or rule.get("scopes") or ["*"]

    people = rule.get("people") or {
        "users": {"include": []},
        "groups": {"include": ["EVERYONE"]},
    }

    token_actions: Dict[str, Any] = {
        "accessTokenLifetimeMinutes": int(rule.get("accessTokenLifetimeMinutes", 60))
    }
    if "refreshTokenLifetimeMinutes" in rule and rule["refreshTokenLifetimeMinutes"] is not None:
        token_actions["refreshTokenLifetimeMinutes"] = int(rule["refreshTokenLifetimeMinutes"])
    if "refreshTokenWindowMinutes" in rule and rule["refreshTokenWindowMinutes"] is not None:
        token_actions["refreshTokenWindowMinutes"] = int(rule["refreshTokenWindowMinutes"])
    if "inlineHookId" in rule and rule["inlineHookId"]:
        token_actions["inlineHook"] = {"id": rule["inlineHookId"]}

    payload: Dict[str, Any] = {
        "type": "RESOURCE_ACCESS",
        "name": rule["name"],
        "priority": int(rule.get("priority", 1)),
        "status": rule.get("status", "ACTIVE"),
        "conditions": {
            "people": people,
            "grantTypes": {"include": grant_types},
            "scopes": {"include": scopes},
        },
        "actions": {
            "token": token_actions
        }
    }

    if "conditions" in rule:
        payload["conditions"] = deepcopy(rule["conditions"])
    if "actions" in rule:
        payload["actions"] = deepcopy(rule["actions"])

    return payload
