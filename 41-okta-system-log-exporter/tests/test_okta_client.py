from okta_system_log_exporter.okta_client import calculate_rate_limit_sleep, parse_next_link


def test_parse_next_link():
    header = '<https://example.okta.com/api/v1/logs?after=abc>; rel="next", <https://example.okta.com/api/v1/logs>; rel="self"'
    assert parse_next_link(header) == "https://example.okta.com/api/v1/logs?after=abc"


def test_parse_next_link_none():
    assert parse_next_link('') is None
    assert parse_next_link('<https://example.com>; rel="self"') is None


def test_calculate_rate_limit_sleep_retry_after():
    assert calculate_rate_limit_sleep({"Retry-After": "2"}) == 2.0
