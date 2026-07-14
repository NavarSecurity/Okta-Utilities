from okta_trusted_origin_manager.okta_client import OktaClient


def test_url_strips_duplicate_slashes():
    client = OktaClient("https://example.okta.com/", "token")
    assert client._url("/api/v1/trustedOrigins") == "https://example.okta.com/api/v1/trustedOrigins"


def test_next_link_parses_link_header():
    header = '<https://example.okta.com/api/v1/trustedOrigins?after=abc>; rel="next", <https://example.okta.com/api/v1/trustedOrigins>; rel="self"'
    assert OktaClient._next_link(header) == "https://example.okta.com/api/v1/trustedOrigins?after=abc"
