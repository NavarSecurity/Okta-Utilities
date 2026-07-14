from okta_idp_exporter.config import RedactionConfig
from okta_idp_exporter.redact import prepare_export_object, redact_value, strip_links


def test_redact_secret_keys():
    data = {
        "name": "Example",
        "protocol": {
            "credentials": {
                "client": {
                    "client_id": "abc",
                    "client_secret": "super-secret"
                }
            }
        }
    }

    result = redact_value(data, RedactionConfig())

    assert result["protocol"]["credentials"]["client"]["client_id"] == "abc"
    assert result["protocol"]["credentials"]["client"]["client_secret"] == "[REDACTED]"


def test_strip_links_recursively():
    data = {"id": "123", "_links": {"self": {}}, "nested": {"_links": {"x": {}}, "value": 1}}

    result = strip_links(data)

    assert "_links" not in result
    assert "_links" not in result["nested"]
    assert result["nested"]["value"] == 1


def test_prepare_export_object_does_not_mutate_original():
    data = {"client_secret": "real", "_links": {"self": {}}}

    result = prepare_export_object(data, include_links=False, redact_sensitive=True, redaction_config=RedactionConfig())

    assert result == {"client_secret": "[REDACTED]"}
    assert data["client_secret"] == "real"
    assert "_links" in data
