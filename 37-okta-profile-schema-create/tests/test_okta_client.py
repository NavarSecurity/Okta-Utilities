from okta_profile_schema_create.okta_client import OktaClient


def test_url_joining_strips_duplicate_slashes():
    client = OktaClient("https://example.okta.com/", "token")
    assert client._url("/api/v1/meta/schemas/user/default") == "https://example.okta.com/api/v1/meta/schemas/user/default"
