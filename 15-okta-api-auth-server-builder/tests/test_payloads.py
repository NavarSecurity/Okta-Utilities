import pytest

from okta_api_auth_server_builder.payloads import (
    build_authorization_server_payload,
    build_claim_payload,
    build_policy_payload,
    build_policy_rule_payload,
    build_scope_payload,
)
from okta_api_auth_server_builder.util import normalize_org_url


def test_rejects_admin_url():
    with pytest.raises(ValueError):
        normalize_org_url("https://example-admin.okta.com")


def test_auth_server_payload_minimal():
    payload = build_authorization_server_payload(
        {
            "name": "API AS",
            "description": "Test",
            "audiences": ["api://test"],
            "issuerMode": "ORG_URL",
            "status": "ACTIVE",
        }
    )
    assert payload["name"] == "API AS"
    assert payload["audiences"] == ["api://test"]
    assert "scopes" not in payload
    assert "policies" not in payload


def test_auth_server_requires_audience():
    with pytest.raises(ValueError):
        build_authorization_server_payload({"name": "API AS", "audiences": []})


def test_auth_server_rejects_source_signing_credentials():
    with pytest.raises(ValueError):
        build_authorization_server_payload(
            {
                "name": "API AS",
                "audiences": ["api://test"],
                "credentials": {"signing": {"kid": "source-key"}},
            }
        )


def test_scope_payload():
    payload = build_scope_payload(
        {
            "name": "read:test",
            "description": "Read test",
            "consent": "IMPLICIT",
            "metadataPublish": "ALL_CLIENTS",
            "default": False,
        }
    )
    assert payload["name"] == "read:test"
    assert payload["default"] is False


def test_claim_payload():
    payload = build_claim_payload(
        {
            "name": "email",
            "status": "ACTIVE",
            "claimType": "IDENTITY",
            "valueType": "EXPRESSION",
            "value": "user.email",
            "alwaysIncludeInToken": True,
            "conditions": {"scopes": ["openid"]},
        }
    )
    assert payload["claimType"] == "IDENTITY"
    assert payload["alwaysIncludeInToken"] is True


def test_policy_payload_defaults_clients():
    payload = build_policy_payload({"name": "Default Policy", "priority": 1})
    assert payload["type"] == "OAUTH_AUTHORIZATION_POLICY"
    assert payload["conditions"]["clients"]["include"] == ["ALL_CLIENTS"]


def test_policy_rule_payload_default_shape():
    payload = build_policy_rule_payload(
        {
            "name": "Allow Code",
            "priority": 1,
            "grantTypeWhitelist": ["authorization_code"],
            "scopeWhitelist": ["read:test"],
            "accessTokenLifetimeMinutes": 60,
        }
    )
    assert payload["type"] == "RESOURCE_ACCESS"
    assert payload["conditions"]["grantTypes"]["include"] == ["authorization_code"]
    assert payload["conditions"]["scopes"]["include"] == ["read:test"]
    assert payload["actions"]["token"]["accessTokenLifetimeMinutes"] == 60


def test_policy_rule_rejects_refresh_token_grant_condition():
    with pytest.raises(ValueError, match="refresh_token"):
        build_policy_rule_payload(
            {
                "name": "Bad Refresh Token Rule",
                "grantTypeWhitelist": ["authorization_code", "refresh_token"],
                "scopeWhitelist": ["read:test"],
                "accessTokenLifetimeMinutes": 60,
                "refreshTokenLifetimeMinutes": 10080,
                "refreshTokenWindowMinutes": 10080,
            }
        )


def test_policy_rule_allows_refresh_token_lifetime_without_refresh_grant_condition():
    payload = build_policy_rule_payload(
        {
            "name": "Code With Refresh Lifetime",
            "grantTypeWhitelist": ["authorization_code"],
            "scopeWhitelist": ["read:test"],
            "accessTokenLifetimeMinutes": 60,
            "refreshTokenLifetimeMinutes": 10080,
            "refreshTokenWindowMinutes": 10080,
        }
    )
    assert payload["conditions"]["grantTypes"]["include"] == ["authorization_code"]
    assert payload["actions"]["token"]["refreshTokenLifetimeMinutes"] == 10080
    assert payload["actions"]["token"]["refreshTokenWindowMinutes"] == 10080


def test_policy_rule_default_people_uses_everyone_group_not_user():
    payload = build_policy_rule_payload(
        {
            "name": "Default People Rule",
            "grantTypeWhitelist": ["authorization_code"],
            "scopeWhitelist": ["read:test"],
        }
    )
    people = payload["conditions"]["people"]
    assert people["groups"]["include"] == ["EVERYONE"]
    assert people["users"]["include"] == []


def test_policy_rule_rejects_everyone_under_users_include():
    with pytest.raises(ValueError, match="people.users.include"):
        build_policy_rule_payload(
            {
                "name": "Bad Everyone User Rule",
                "grantTypeWhitelist": ["authorization_code"],
                "scopeWhitelist": ["read:test"],
                "people": {
                    "users": {"include": ["EVERYONE"]},
                    "groups": {"include": []},
                },
            }
        )


def test_policy_rule_rejects_everyone_under_conditions_users_include():
    with pytest.raises(ValueError, match="people.users.include"):
        build_policy_rule_payload(
            {
                "name": "Bad Everyone User Rule In Conditions",
                "grantTypeWhitelist": ["authorization_code"],
                "scopeWhitelist": ["read:test"],
                "conditions": {
                    "people": {
                        "users": {"include": ["EVERYONE"]},
                        "groups": {"include": []},
                    },
                    "grantTypes": {"include": ["authorization_code"]},
                    "scopes": {"include": ["read:test"]},
                },
            }
        )
