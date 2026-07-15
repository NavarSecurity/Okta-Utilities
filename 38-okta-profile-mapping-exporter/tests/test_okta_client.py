import pytest

from okta_profile_mapping_exporter.okta_client import normalize_org_url, parse_next_link


def test_parse_next_link():
    link = '<https://example.okta.com/api/v1/mappings?after=abc>; rel="next", <https://example.okta.com/api/v1/mappings>; rel="self"'
    assert parse_next_link(link) == "https://example.okta.com/api/v1/mappings?after=abc"


def test_parse_next_link_returns_none_without_next():
    assert parse_next_link('<https://example.okta.com/api/v1/mappings>; rel="self"') is None


def test_normalize_org_url():
    assert normalize_org_url("https://example.okta.com/") == "https://example.okta.com"


def test_normalize_org_url_requires_https():
    with pytest.raises(ValueError):
        normalize_org_url("http://example.okta.com")
