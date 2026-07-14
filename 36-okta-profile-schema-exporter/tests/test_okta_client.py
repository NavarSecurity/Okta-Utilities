from requests import Response

from okta_profile_schema_exporter.okta_client import OktaClient


def test_url_joins_relative_path():
    client = OktaClient("https://example.okta.com", "token")
    assert client._url("/api/v1/meta/schemas/user/default") == "https://example.okta.com/api/v1/meta/schemas/user/default"


def test_next_link_extracts_next_url():
    response = Response()
    response.headers["Link"] = '<https://example.okta.com/api/v1/apps?after=abc>; rel="next"'
    assert OktaClient._next_link(response) == "https://example.okta.com/api/v1/apps?after=abc"
