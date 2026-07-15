from okta_profile_schema_create.redact import redact


def test_redacts_sensitive_keys():
    data = {"client_secret": "abc", "nested": {"Authorization": "SSWS token"}, "safe": "value"}
    redacted = redact(data)
    assert redacted["client_secret"] == "REDACTED"
    assert redacted["nested"]["Authorization"] == "REDACTED"
    assert redacted["safe"] == "value"
