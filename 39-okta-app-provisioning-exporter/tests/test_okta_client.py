import pytest
from okta_app_provisioning_exporter.okta_client import _next_link, OktaClient, OktaClientError


def test_next_link_parsing():
    header = '<https://example.okta.com/api/v1/apps?after=abc>; rel="next", <https://example.okta.com/api/v1/apps>; rel="self"'
    assert _next_link(header) == 'https://example.okta.com/api/v1/apps?after=abc'


def test_next_link_missing():
    assert _next_link('') is None


def test_org_url_validation(monkeypatch):
    monkeypatch.setenv("OKTA_ORG_URL", "https://example.okta.com/api/v1")
    monkeypatch.setenv("OKTA_API_TOKEN", "token")
    with pytest.raises(OktaClientError):
        OktaClient()
