from okta_scim_provisioning_tester.redact import redact


def test_redact_sensitive_values():
    data = {
        "Authorization": "Bearer secret",
        "nested": {"client_secret": "secret"},
        "safe": "value",
    }
    result = redact(data)
    assert result["Authorization"] == "***REDACTED***"
    assert result["nested"]["client_secret"] == "***REDACTED***"
    assert result["safe"] == "value"
