from okta_security_event_detector.redact import redact_obj


def test_redact_token_keys_and_values():
    data = {"headers": {"Authorization": "SSWS abc123"}, "message": "Bearer tokenvalue"}
    redacted = redact_obj(data)
    assert redacted["headers"]["Authorization"] == "[REDACTED]"
    assert redacted["message"] == "[REDACTED]"
