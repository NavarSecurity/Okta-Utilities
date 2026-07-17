from okta_api_access_auditor.normalize import is_service_app, normalize_app, normalize_grant, normalize_client_role, normalize_api_token


def test_is_service_app_by_application_type():
    app = {"name": "oidc_client", "settings": {"oauthClient": {"application_type": "service", "grant_types": []}}}
    assert is_service_app(app) is True


def test_is_service_app_by_client_credentials():
    app = {"name": "oidc_client", "settings": {"oauthClient": {"application_type": "web", "grant_types": ["client_credentials"]}}}
    assert is_service_app(app) is True


def test_normalize_app_extracts_client_id():
    app = {"id": "0oa1", "label": "App", "name": "oidc_client", "credentials": {"oauthClient": {"client_id": "cid"}}, "settings": {"oauthClient": {"application_type": "service", "grant_types": ["client_credentials"], "token_endpoint_auth_method": "private_key_jwt"}}}
    row = normalize_app(app)
    assert row["clientId"] == "cid"
    assert row["isServiceApp"] is True


def test_normalize_grant_scope_id():
    app = {"id": "0oa1", "label": "App", "credentials": {"oauthClient": {"client_id": "cid"}}}
    row = normalize_grant(app, {"id": "g1", "scopeId": "okta.users.read"})
    assert row["scope"] == "okta.users.read"


def test_normalize_client_role_type():
    app = {"id": "0oa1", "label": "App", "credentials": {"oauthClient": {"client_id": "cid"}}}
    row = normalize_client_role(app, {"id": "r1", "type": "SUPER_ADMIN"})
    assert row["roleType"] == "SUPER_ADMIN"


def test_normalize_api_token_network():
    token = {"id": "t1", "name": "Token", "network": {"connection": "ANYWHERE"}, "createdBy": {"login": "admin@example.com"}}
    row = normalize_api_token(token)
    assert row["networkConnection"] == "ANYWHERE"
    assert row["createdByLogin"] == "admin@example.com"
