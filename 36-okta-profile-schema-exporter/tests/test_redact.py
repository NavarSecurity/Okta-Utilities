from okta_profile_schema_exporter.redact import redact_object


def test_redacts_sensitive_keys_nested():
    data = {"ok": "value", "client_secret": "abc", "nested": {"apiToken": "secret"}}
    redacted = redact_object(data)
    assert redacted["ok"] == "value"
    assert redacted["client_secret"] == "REDACTED"
    assert redacted["nested"]["apiToken"] == "REDACTED"
