from okta_rate_limit_monitor.redact import redact


def test_redact_sensitive_keys():
    data = {
        "Authorization": "SSWS secret",
        "client_secret": "secret",
        "nested": {"apiToken": "abc", "safe": "ok"},
    }
    redacted = redact(data)
    assert redacted["Authorization"] == "[REDACTED]"
    assert redacted["client_secret"] == "[REDACTED]"
    assert redacted["nested"]["apiToken"] == "[REDACTED]"
    assert redacted["nested"]["safe"] == "ok"
