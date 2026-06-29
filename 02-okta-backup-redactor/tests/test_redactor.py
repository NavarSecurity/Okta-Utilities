from pathlib import Path

from okta_backup_redactor.config import RedactorConfig
from okta_backup_redactor.redactor import redact_json


def test_client_secret_is_redacted():
    cfg = RedactorConfig(source_backup_dir=Path("unused"))
    data = {"credentials": {"oauthClient": {"client_secret": "secret-value"}}}
    redacted, findings = redact_json(data, file_name="applications.json", cfg=cfg)
    assert redacted["credentials"]["oauthClient"]["client_secret"] == "[REDACTED]"
    assert len(findings) == 1
    assert findings[0].path == "$.credentials.oauthClient.client_secret"


def test_policytypes_password_structure_is_preserved():
    cfg = RedactorConfig(source_backup_dir=Path("unused"))
    data = {
        "policyTypes": {
            "PASSWORD": {
                "policies": [
                    {
                        "type": "PASSWORD",
                        "settings": {
                            "password": {
                                "complexity": {"minLength": 12}
                            }
                        },
                    }
                ],
                "rulesByPolicyId": {
                    "00p1": [
                        {
                            "actions": {
                                "passwordChange": {"access": "ALLOW"},
                                "selfServicePasswordReset": {"access": "ALLOW"},
                            }
                        }
                    ]
                },
            }
        }
    }
    redacted, findings = redact_json(data, file_name="policies.json", cfg=cfg)
    assert isinstance(redacted["policyTypes"]["PASSWORD"], dict)
    assert isinstance(redacted["policyTypes"]["PASSWORD"]["policies"], list)
    assert redacted["policyTypes"]["PASSWORD"]["policies"][0]["settings"]["password"]["complexity"]["minLength"] == 12
    assert findings == []


def test_regular_password_value_is_redacted():
    cfg = RedactorConfig(source_backup_dir=Path("unused"))
    data = {"user": {"password": "P@ssw0rd!"}}
    redacted, findings = redact_json(data, file_name="users.json", cfg=cfg)
    assert redacted["user"]["password"] == "[REDACTED]"
    assert len(findings) == 1


def test_authorization_header_value_is_redacted():
    cfg = RedactorConfig(source_backup_dir=Path("unused"))
    data = {"headers": [{"key": "Authorization", "value": "Bearer abc.def.ghi"}], "authorizationServers": []}
    redacted, findings = redact_json(data, file_name="event_hooks.json", cfg=cfg)
    assert redacted["headers"][0]["key"] == "Authorization"
    assert redacted["headers"][0]["value"] == "[REDACTED]"
    assert redacted["authorizationServers"] == []
    assert len(findings) == 1


def test_token_lifetime_is_not_redacted():
    cfg = RedactorConfig(source_backup_dir=Path("unused"))
    data = {"recoveryToken": {"tokenLifetimeMinutes": 60}}
    redacted, findings = redact_json(data, file_name="policies.json", cfg=cfg)
    assert redacted == data
    assert findings == []
