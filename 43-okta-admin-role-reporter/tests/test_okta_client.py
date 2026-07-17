from okta_admin_role_reporter.okta_client import OktaClient


def test_next_from_links_header():
    header = '<https://example.okta.com/api/v1/users?after=abc>; rel="next", <https://example.okta.com/api/v1/users>; rel="self"'
    assert OktaClient._next_from_links_header(header) == "https://example.okta.com/api/v1/users?after=abc"


def test_absolute_url():
    client = OktaClient("https://example.okta.com", "token")
    assert client._absolute_url("/api/v1/users") == "https://example.okta.com/api/v1/users"
