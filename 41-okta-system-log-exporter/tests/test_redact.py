from okta_system_log_exporter.redact import REDACTED, redact_event


def test_redact_sensitive_keys():
    event = {
        "debugContext": {
            "debugData": {
                "authorization": "SSWS secret",
                "clientSecret": "abc",
                "normal": "value",
            }
        }
    }
    redacted = redact_event(event)
    assert redacted["debugContext"]["debugData"]["authorization"] == REDACTED
    assert redacted["debugContext"]["debugData"]["clientSecret"] == REDACTED
    assert redacted["debugContext"]["debugData"]["normal"] == "value"
    assert event["debugContext"]["debugData"]["authorization"] == "SSWS secret"
