from okta_selective_restore.sanitizers import sanitize_application, sanitize_group, sanitize_trusted_origin


def test_sanitize_group_keeps_only_profile_name_description():
    source = {"id": "00g1", "profile": {"name": "Engineering", "description": "Eng"}, "_links": {"self": {}}}
    assert sanitize_group(source) == {"profile": {"name": "Engineering", "description": "Eng"}}


def test_sanitize_application_removes_secret_and_read_only_fields():
    source = {
        "id": "app1",
        "label": "OIDC App",
        "name": "oidc_client",
        "credentials": {"oauthClient": {"client_id": "abc", "client_secret": "secret"}},
        "_links": {"self": {}},
        "created": "today",
        "status": "ACTIVE",
    }
    payload = sanitize_application(source)
    assert "id" not in payload
    assert "_links" not in payload
    assert "created" not in payload
    assert "status" not in payload
    assert "client_secret" not in payload["credentials"]["oauthClient"]
    assert payload["credentials"]["oauthClient"]["client_id"] == "abc"


def test_sanitize_trusted_origin_removes_status_and_links():
    payload = sanitize_trusted_origin({"id": "to1", "name": "App", "origin": "https://a.example", "status": "ACTIVE", "_links": {}})
    assert payload == {"name": "App", "origin": "https://a.example"}
