from okta_api_access_auditor.redact import redact


def test_redact_sensitive_keys():
    data = {"client_secret": "abcdefghijklmnop", "nested": {"Authorization": "SSWS abcdefghijklmnop"}}
    output = redact(data)
    assert output["client_secret"] != "abcdefghijklmnop"
    assert output["nested"]["Authorization"] != "SSWS abcdefghijklmnop"
