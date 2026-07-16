from okta_scim_provisioning_tester.scim_client import ScimClient


def test_build_url(monkeypatch):
    monkeypatch.setenv("SCIM_AUTH_TYPE", "none")
    client = ScimClient("https://example.com/scim/v2", "none")
    assert client.build_url("/Users") == "https://example.com/scim/v2/Users"
    assert client.build_url("ServiceProviderConfig") == "https://example.com/scim/v2/ServiceProviderConfig"


def test_bearer_header(monkeypatch):
    monkeypatch.setenv("SCIM_BEARER_TOKEN", "abc123")
    client = ScimClient("https://example.com/scim/v2", "bearer")
    assert client.session.headers["Authorization"] == "Bearer abc123"
