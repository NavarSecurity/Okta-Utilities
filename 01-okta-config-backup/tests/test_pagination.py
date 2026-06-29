from okta_config_backup.client import parse_next_link, split_link_header


def test_parse_next_link_from_header():
    header = '<https://example.okta.com/api/v1/apps?limit=2>; rel="self", <https://example.okta.com/api/v1/apps?after=abc&limit=2>; rel="next"'

    assert parse_next_link(header) == "https://example.okta.com/api/v1/apps?after=abc&limit=2"


def test_split_link_header_does_not_split_url_commas():
    header = '<https://example.okta.com/api/v1/logs?q=a,b>; rel="self", <https://example.okta.com/api/v1/logs?after=cursor>; rel="next"'

    parts = split_link_header(header)

    assert len(parts) == 2
    assert "q=a,b" in parts[0]
