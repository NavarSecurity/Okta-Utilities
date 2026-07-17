from okta_admin_role_reporter.normalize import (
    entity_display_name,
    id_from_href,
    is_high_privilege,
    member_type_from_href,
    role_type,
)


def test_entity_display_name_user():
    user = {"id": "00u1", "profile": {"firstName": "Jane", "lastName": "Admin", "login": "jane@example.com"}}
    assert entity_display_name(user, "user") == "Jane Admin"


def test_role_type_prefers_type():
    assert role_type({"type": "SUPER_ADMIN", "label": "Super Administrator"}) == "SUPER_ADMIN"


def test_is_high_privilege():
    assert is_high_privilege({"type": "SUPER_ADMIN"}, ["SUPER_ADMIN"])
    assert not is_high_privilege({"type": "READ_ONLY_ADMIN"}, ["SUPER_ADMIN"])


def test_member_type_and_id_from_href():
    href = "https://example.okta.com/api/v1/groups/00g123"
    assert member_type_from_href(href) == "group"
    assert id_from_href(href) == "00g123"
