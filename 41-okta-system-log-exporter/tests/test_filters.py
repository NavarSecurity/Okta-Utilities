from okta_system_log_exporter.config import ExportConfig
from okta_system_log_exporter.filters import build_filter, build_query_params, escape_filter_value


def test_escape_filter_value():
    assert escape_filter_value('a"b') == 'a\\"b'


def test_build_filter_from_event_type_and_outcome():
    cfg = ExportConfig(event_types=["user.authentication.failed"], outcomes=["FAILURE"])
    assert build_filter(cfg) == 'eventType eq "user.authentication.failed" and outcome.result eq "FAILURE"'


def test_build_filter_combines_custom_and_generated():
    cfg = ExportConfig(filter='client.ipAddress eq "203.0.113.1"', actor_logins=["admin@example.com"])
    assert build_filter(cfg) == '(client.ipAddress eq "203.0.113.1") and (actor.alternateId eq "admin@example.com")'


def test_build_query_params_includes_filter_and_q():
    cfg = ExportConfig(relative_hours=1, q="failed", event_types=["user.authentication.failed"])
    params = build_query_params(cfg)
    assert params["q"] == "failed"
    assert params["filter"] == 'eventType eq "user.authentication.failed"'
    assert params["limit"] == 1000
