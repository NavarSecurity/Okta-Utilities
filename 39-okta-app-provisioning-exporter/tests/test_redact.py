from okta_app_provisioning_exporter.redact import redact_object, is_sensitive_key


def test_sensitive_key_detection():
    assert is_sensitive_key("client_secret")
    assert is_sensitive_key("authorizationHeader")
    assert not is_sensitive_key("label")


def test_redact_nested_values():
    data = {"credentials":{"userName":"u"}, "settings":{"app":{"client_secret":"abc", "url":"https://example.com"}}}
    redacted = redact_object(data)
    assert redacted["credentials"] == "[REDACTED]"
    assert redacted["settings"]["app"]["client_secret"] == "[REDACTED]"
    assert redacted["settings"]["app"]["url"] == "https://example.com"
