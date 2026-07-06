from okta_user_exporter.okta_client import _parse_next_link


def test_parse_next_link():
    header = '<https://example.okta.com/api/v1/users?after=abc>; rel="next", <https://example.okta.com/api/v1/users>; rel="self"'
    assert _parse_next_link(header) == "https://example.okta.com/api/v1/users?after=abc"


def test_parse_next_link_none():
    assert _parse_next_link('<https://example.okta.com/api/v1/users>; rel="self"') is None
