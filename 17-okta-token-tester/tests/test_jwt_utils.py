import base64
import json

from okta_token_tester.jwt_utils import aud_matches, decode_unverified, token_scopes, validate_jwt


def _b64(data):
    return base64.urlsafe_b64encode(json.dumps(data).encode()).decode().rstrip("=")


def make_token(claims):
    return f"{_b64({'alg':'none','typ':'JWT'})}.{_b64(claims)}."


def test_decode_unverified():
    token = make_token({"iss": "issuer", "scp": ["read:test"]})
    header, claims = decode_unverified(token)
    assert header["alg"] == "none"
    assert claims["iss"] == "issuer"


def test_token_scopes_from_list_and_string():
    assert token_scopes({"scp": ["a", "b"]}) == {"a", "b"}
    assert token_scopes({"scope": "a b"}) == {"a", "b"}


def test_aud_matches_string_or_list():
    assert aud_matches("api://x", "api://x")
    assert aud_matches(["api://x", "api://y"], "api://y")
    assert not aud_matches("api://x", "api://z")


def test_validate_jwt_without_signature_finds_missing_scope():
    token = make_token({"iss": "issuer", "aud": "api://x", "scp": ["read:x"], "exp": 9999999999, "iat": 1})
    result = validate_jwt(
        token,
        "test",
        "accessToken",
        "access",
        "issuer",
        None,
        expected_audience="api://x",
        expected_scopes=["write:x"],
        required_claims=["iss", "aud"],
        verify_signature=False,
    )
    assert not result.passed
    assert any(f.check == "scope" for f in result.findings)
