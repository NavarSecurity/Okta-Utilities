from okta_mfa_enrollment_reporter.redaction import redact_object


def test_redacts_phone_number_and_secret_keys():
    obj = {"phoneNumber": "+1 555 555 1212", "nested": {"secret": "abc", "safe": "value"}}
    redacted = redact_object(obj)
    assert redacted["phoneNumber"] == "[REDACTED]"
    assert redacted["nested"]["secret"] == "[REDACTED]"
    assert redacted["nested"]["safe"] == "value"
