from okta_app_cloner.sanitizer import sanitize_app_for_clone


def test_sanitize_removes_ids_links_and_secrets():
    app = {
        "id": "0oa123",
        "label": "Test App",
        "name": "oidc_client",
        "signOnMode": "OPENID_CONNECT",
        "created": "now",
        "_links": {"self": {}},
        "settings": {"oauthClient": {"client_id": "abc", "client_secret": "secret", "redirect_uris": ["https://example.com/cb"]}},
        "credentials": {"oauthClient": {"client_secret": "secret"}},
    }
    payload = sanitize_app_for_clone(app)
    assert "id" not in payload
    assert "created" not in payload
    assert "_links" not in payload
    assert "client_secret" not in payload["settings"]["oauthClient"]
    assert "client_id" not in payload["settings"]["oauthClient"]
    assert payload["settings"]["oauthClient"]["redirect_uris"] == ["https://example.com/cb"]
    assert "credentials" not in payload


def test_policy_like_app_names_not_redacted():
    app = {"label": "Password Help App", "name": "bookmark", "settings": {"app": {"url": "https://example.com/password-help"}}}
    payload = sanitize_app_for_clone(app)
    assert payload["label"] == "Password Help App"
    assert payload["settings"]["app"]["url"].endswith("password-help")


def test_sanitize_removes_source_org_key_mapping_fields():
    app = {
        "id": "0oa14jw2jexR0cddS698",
        "label": "My API Services App1",
        "name": "oidc_client",
        "signOnMode": "OPENID_CONNECT",
        "orn": "orn:okta:idp:00o12rbljxj8EbvI9698:apps:oidc_client:0oa14jw2jexR0cddS698",
        "credentials": {
            "signing": {
                "kid": "vWyPhFzyft1u0G-6jxB7LnPKpWtVNMB5eMxeoYIeYoU",
                "rotationMode": "AUTO",
            }
        },
        "settings": {"oauthClient": {"redirect_uris": ["https://example.com/callback"]}},
        "status": "ACTIVE",
    }

    payload = sanitize_app_for_clone(app)

    assert "orn" not in payload
    assert "credentials" not in payload
    assert "status" not in payload
    assert payload["settings"]["oauthClient"]["redirect_uris"] == ["https://example.com/callback"]


def test_sanitize_removes_nested_kid_even_outside_credentials_signing():
    app = {
        "label": "SAML App",
        "name": "template_saml_2_0",
        "settings": {
            "signOn": {
                "kid": "source-org-key-id",
                "ssoAcsUrl": "https://example.com/saml/acs",
            }
        },
    }
    payload = sanitize_app_for_clone(app)
    assert "kid" not in payload["settings"]["signOn"]
    assert payload["settings"]["signOn"]["ssoAcsUrl"] == "https://example.com/saml/acs"
