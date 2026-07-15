from okta_profile_mapping_exporter.redact import redact_value


def test_redact_nested_sensitive_values():
    data = {
        "safe": "value",
        "client_secret": "secret-value",
        "nested": {"api_token": "token-value"},
        "items": [{"password": "password-value"}],
    }
    redacted = redact_value(data)
    assert redacted["safe"] == "value"
    assert redacted["client_secret"] == "[REDACTED]"
    assert redacted["nested"]["api_token"] == "[REDACTED]"
    assert redacted["items"][0]["password"] == "[REDACTED]"
