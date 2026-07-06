from okta_token_tester.config import ClientConfig, TestSettings, TokenSources, TokenTestConfig
from okta_token_tester.tester import TokenTester, summarize_jwks, summarize_token_response


def sample_config():
    return TokenTestConfig(
        org_url="https://example.okta.com",
        authorization_server_id="default",
        issuer_url="https://example.okta.com/oauth2/default",
        output_dir=__import__("pathlib").Path("output"),
        settings=TestSettings(),
        client=ClientConfig(client_id="cid", client_secret="secret"),
        token_sources=TokenSources(),
        client_credentials_tests=[{"name": "cc", "scopes": ["read:x"]}],
    )


def test_build_plan_redacts_shape():
    plan = TokenTester(sample_config()).build_plan()
    assert plan["issuerUrl"] == "https://example.okta.com/oauth2/default"
    assert plan["clientPresent"]["clientId"] is True
    assert len(plan["clientCredentialsTests"]) == 1


def test_summarize_jwks():
    rows = summarize_jwks({"keys": [{"kid": "abc", "kty": "RSA", "alg": "RS256", "use": "sig"}]})
    assert rows[0]["kid"] == "abc"


def test_summarize_token_response_redacts_tokens():
    summary, tokens = summarize_token_response({"access_token": "abc.def.ghi", "token_type": "Bearer", "expires_in": 3600})
    assert tokens["access_token"] == "abc.def.ghi"
    assert "access_token" not in summary
    assert "tokenFingerprints" in summary


def test_access_token_source_falls_back_to_runtime_issued_token():
    tester = TokenTester(sample_config())
    token = tester._resolve_token("accessToken", {"access_token": "runtime-access-token"})
    assert token == "runtime-access-token"


def test_configured_access_token_takes_precedence_over_runtime_token():
    cfg = sample_config()
    cfg.token_sources.access_token = "configured-access-token"
    tester = TokenTester(cfg)
    token = tester._resolve_token("accessToken", {"access_token": "runtime-access-token"})
    assert token == "configured-access-token"


def test_client_credentials_alias_resolves_runtime_access_token():
    tester = TokenTester(sample_config())
    token = tester._resolve_token("clientCredentialsAccessToken", {"clientCredentialsAccessToken": "cc-access-token"})
    assert token == "cc-access-token"
