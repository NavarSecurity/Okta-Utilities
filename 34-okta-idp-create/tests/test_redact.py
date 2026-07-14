from okta_idp_create.redact import REDACTION, redact_object


def test_redacts_secret_keys_nested():
    data = {
        "name": "OIDC",
        "protocol": {
            "credentials": {
                "client": {
                    "client_id": "abc",
                    "client_secret": "super-secret"
                }
            }
        },
        "normal": "visible"
    }
    redacted = redact_object(data)
    assert redacted["protocol"]["credentials"]["client"]["client_secret"] == REDACTION
    assert redacted["protocol"]["credentials"]["client"]["client_id"] == "abc"
    assert redacted["normal"] == "visible"


def test_does_not_mutate_original():
    data = {"client_secret": "value"}
    redacted = redact_object(data)
    assert data["client_secret"] == "value"
    assert redacted["client_secret"] == REDACTION
