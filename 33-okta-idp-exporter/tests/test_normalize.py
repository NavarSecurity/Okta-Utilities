from okta_idp_exporter.normalize import should_include_idp, summarize_idp, summarize_key


def test_should_include_idp_filters_inactive():
    idp = {"type": "OIDC", "status": "INACTIVE"}

    assert should_include_idp(idp, include_inactive=True, types=[], statuses=[])
    assert not should_include_idp(idp, include_inactive=False, types=[], statuses=[])


def test_should_include_idp_filters_type():
    idp = {"type": "SAML2", "status": "ACTIVE"}

    assert should_include_idp(idp, include_inactive=True, types=["SAML2"], statuses=[])
    assert not should_include_idp(idp, include_inactive=True, types=["OIDC"], statuses=[])


def test_summarize_oidc_idp():
    idp = {
        "id": "0oa123",
        "name": "OIDC Partner",
        "type": "OIDC",
        "status": "ACTIVE",
        "protocol": {
            "type": "OIDC",
            "endpoints": {
                "authorization": {"url": "https://issuer.example/authorize"},
                "token": {"url": "https://issuer.example/token"},
                "jwks": {"url": "https://issuer.example/keys"}
            },
            "credentials": {
                "client": {"client_id": "client-123"}
            }
        }
    }

    summary = summarize_idp(idp)

    assert summary["name"] == "OIDC Partner"
    assert summary["type"] == "OIDC"
    assert summary["clientId"] == "client-123"
    assert summary["authorizationUrl"] == "https://issuer.example/authorize"


def test_summarize_key():
    key = {"kid": "kid123", "kty": "RSA", "alg": "RS256", "status": "ACTIVE"}

    summary = summarize_key(key)

    assert summary["kid"] == "kid123"
    assert summary["kty"] == "RSA"
    assert summary["alg"] == "RS256"
