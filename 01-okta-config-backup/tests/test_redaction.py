from okta_config_backup.redaction import REDACTED, redact_sensitive_values


def test_redacts_nested_oauth_client_secret():
    data = {
        "settings": {
            "oauthClient": {
                "client_id": "abc123",
                "client_secret": "super-secret-value",
            }
        }
    }

    redacted = redact_sensitive_values(data)

    assert redacted["settings"]["oauthClient"]["client_id"] == "abc123"
    assert redacted["settings"]["oauthClient"]["client_secret"] == REDACTED


def test_redacts_hook_authorization_header_value():
    data = {"channel": {"config": {"authScheme": {"key": "Authorization", "value": "Bearer abc"}}}}

    redacted = redact_sensitive_values(data)

    assert redacted["channel"]["config"]["authScheme"]["key"] == "Authorization"
    assert redacted["channel"]["config"]["authScheme"]["value"] == REDACTED


def test_redacts_secret_query_parameters_inside_strings():
    data = {"url": "https://example.com/callback?client_secret=abc&state=123"}

    redacted = redact_sensitive_values(data)

    assert "abc" not in redacted["url"]
    assert "client_secret=[REDACTED]" in redacted["url"]


def test_does_not_redact_okta_password_policy_type_container():
    data = {
        "policyTypes": {
            "PASSWORD": {
                "errors": [],
                "policies": [
                    {
                        "id": "00pabc123",
                        "name": "Default Policy",
                        "type": "PASSWORD",
                    }
                ],
                "rulesByPolicyId": {},
            }
        }
    }

    redacted = redact_sensitive_values(data)

    assert redacted["policyTypes"]["PASSWORD"] != REDACTED
    assert redacted["policyTypes"]["PASSWORD"]["policies"][0]["type"] == "PASSWORD"
    assert redacted["policyTypes"]["PASSWORD"]["policies"][0]["name"] == "Default Policy"


def test_still_redacts_real_password_fields():
    data = {"profile": {"login": "user@example.com", "password": "plain-text-secret"}}

    redacted = redact_sensitive_values(data)

    assert redacted["profile"]["login"] == "user@example.com"
    assert redacted["profile"]["password"] == REDACTED
