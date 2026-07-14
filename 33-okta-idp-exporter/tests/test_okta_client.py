from okta_idp_exporter.okta_client import OktaClient


def test_build_url_for_relative_path():
    client = OktaClient("https://example.okta.com", "token")

    assert client._build_url("/api/v1/idps") == "https://example.okta.com/api/v1/idps"


def test_build_url_preserves_absolute_url():
    client = OktaClient("https://example.okta.com", "token")

    assert client._build_url("https://example.okta.com/api/v1/idps?after=abc") == "https://example.okta.com/api/v1/idps?after=abc"
