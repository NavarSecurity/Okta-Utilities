import pytest

from okta_scim_provisioning_tester.payloads import (
    build_deactivate_payload,
    build_group_membership_payload,
    build_patch_payload,
    ensure_group_payload,
    ensure_user_payload,
)


def test_ensure_user_payload_adds_schema():
    payload = ensure_user_payload({"userName": "test@example.com"})
    assert payload["userName"] == "test@example.com"
    assert "urn:ietf:params:scim:schemas:core:2.0:User" in payload["schemas"]


def test_ensure_user_payload_requires_username():
    with pytest.raises(ValueError):
        ensure_user_payload({})


def test_ensure_group_payload_adds_schema():
    payload = ensure_group_payload({"displayName": "Test Group"})
    assert payload["displayName"] == "Test Group"
    assert "urn:ietf:params:scim:schemas:core:2.0:Group" in payload["schemas"]


def test_build_patch_payload():
    payload = build_patch_payload({"title": "Engineer", "name.givenName": "Updated"})
    assert payload["schemas"] == ["urn:ietf:params:scim:api:messages:2.0:PatchOp"]
    assert {"op": "replace", "path": "title", "value": "Engineer"} in payload["Operations"]


def test_build_deactivate_payload():
    payload = build_deactivate_payload()
    assert payload["Operations"][0]["path"] == "active"
    assert payload["Operations"][0]["value"] is False


def test_build_group_membership_payload():
    payload = build_group_membership_payload("abc123", "test@example.com")
    member = payload["Operations"][0]["value"][0]
    assert member["value"] == "abc123"
    assert member["display"] == "test@example.com"
