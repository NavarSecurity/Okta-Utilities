from okta_trusted_origin_manager.validate import validate_trusted_origins


def test_validate_accepts_https_cors_redirect():
    payload = {"trustedOrigins": [{"name": "App", "origin": "https://app.example.com", "scopes": [{"type": "CORS"}, {"type": "REDIRECT"}]}]}
    report = validate_trusted_origins(payload)
    assert report["errorCount"] == 0


def test_validate_rejects_missing_origin():
    payload = {"trustedOrigins": [{"name": "Broken", "scopes": [{"type": "CORS"}]}]}
    report = validate_trusted_origins(payload)
    assert report["errorCount"] == 1
    assert report["findings"][0]["code"] == "MISSING_ORIGIN"


def test_validate_flags_wildcard_cors_as_error():
    payload = {"trustedOrigins": [{"name": "Wildcard", "origin": "https://*.example.com", "scopes": [{"type": "CORS"}]}]}
    report = validate_trusted_origins(payload)
    assert any(item["code"] == "WILDCARD_WITH_CORS_OR_REDIRECT" for item in report["findings"])


def test_validate_warns_on_path():
    payload = {"trustedOrigins": [{"name": "Path", "origin": "https://app.example.com/callback", "scopes": [{"type": "REDIRECT"}]}]}
    report = validate_trusted_origins(payload)
    assert any(item["code"] == "ORIGIN_HAS_PATH_QUERY_OR_FRAGMENT" for item in report["findings"])
