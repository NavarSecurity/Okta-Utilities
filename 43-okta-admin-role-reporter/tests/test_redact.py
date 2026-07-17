from okta_admin_role_reporter.redact import redact_value


def test_redacts_sensitive_keys():
    payload = {
        "Authorization": "SSWS token",
        "nested": {"client_secret": "secret", "safe": "value"},
    }
    redacted = redact_value(payload)
    assert redacted["Authorization"] == "***REDACTED***"
    assert redacted["nested"]["client_secret"] == "***REDACTED***"
    assert redacted["nested"]["safe"] == "value"
