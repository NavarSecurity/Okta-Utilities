import pytest

from okta_idp_create.config import ConfigError
from okta_idp_create.planner import build_payload, build_plan


def test_build_payload_from_payload():
    payload = build_payload(
        {
            "name": "Test SAML",
            "type": "SAML2",
            "payload": {
                "type": "SAML2",
                "name": "Test SAML",
                "protocol": {},
                "policy": {},
            },
        }
    )
    assert payload["name"] == "Test SAML"
    assert payload["type"] == "SAML2"


def test_oidc_requires_protocol_and_policy():
    with pytest.raises(ConfigError):
        build_payload({"name": "Bad OIDC", "type": "OIDC", "payload": {"name": "Bad OIDC", "type": "OIDC"}})


def test_duplicate_names_fail():
    idps = [
        {"name": "Dup", "type": "SAML2", "payload": {"name": "Dup", "type": "SAML2", "protocol": {}, "policy": {}}},
        {"name": "Dup", "type": "SAML2", "payload": {"name": "Dup", "type": "SAML2", "protocol": {}, "policy": {}}},
    ]
    with pytest.raises(ConfigError):
        build_plan(idps)
