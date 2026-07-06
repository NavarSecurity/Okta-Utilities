from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

import jwt
from jwt import InvalidTokenError


@dataclass
class Finding:
    test_name: str
    severity: str
    check: str
    message: str


@dataclass
class JwtValidationResult:
    test_name: str
    token_source: str
    token_type: str
    passed: bool
    header: dict[str, Any] = field(default_factory=dict)
    claims: dict[str, Any] = field(default_factory=dict)
    findings: list[Finding] = field(default_factory=list)


def decode_unverified(token: str) -> tuple[dict[str, Any], dict[str, Any]]:
    header = jwt.get_unverified_header(token)
    claims = jwt.decode(token, options={"verify_signature": False, "verify_aud": False})
    if not isinstance(header, dict) or not isinstance(claims, dict):
        raise InvalidTokenError("Token did not decode to JSON objects")
    return header, claims


def token_scopes(claims: dict[str, Any]) -> set[str]:
    raw = claims.get("scp", claims.get("scope", []))
    if isinstance(raw, str):
        return {part for part in raw.split() if part}
    if isinstance(raw, list):
        return {str(item) for item in raw if str(item)}
    return set()


def aud_matches(actual: Any, expected: str) -> bool:
    if isinstance(actual, str):
        return actual == expected
    if isinstance(actual, list):
        return expected in [str(item) for item in actual]
    return False


def validate_jwt(
    token: str,
    test_name: str,
    token_source: str,
    token_type: str,
    issuer_url: str,
    jwks: dict[str, Any] | None,
    expected_issuer: str | None = None,
    expected_audience: str | None = None,
    expected_scopes: list[str] | None = None,
    required_claims: list[str] | None = None,
    verify_signature: bool = True,
) -> JwtValidationResult:
    findings: list[Finding] = []
    try:
        header, unverified_claims = decode_unverified(token)
    except Exception as exc:
        return JwtValidationResult(
            test_name=test_name,
            token_source=token_source,
            token_type=token_type,
            passed=False,
            findings=[Finding(test_name, "error", "jwt_decode", f"Unable to decode JWT: {exc}")],
        )

    claims = unverified_claims
    expected_issuer = expected_issuer or issuer_url

    if verify_signature:
        try:
            claims = _decode_verified(token, header, jwks, expected_issuer, expected_audience)
        except Exception as exc:
            findings.append(Finding(test_name, "error", "signature_validation", f"JWT signature/standard validation failed: {exc}"))
    else:
        findings.append(Finding(test_name, "warning", "signature_validation", "Signature verification was disabled for this test"))

    if expected_issuer and claims.get("iss") != expected_issuer:
        findings.append(Finding(test_name, "error", "issuer", f"Expected issuer {expected_issuer}, got {claims.get('iss')}"))

    if expected_audience and not aud_matches(claims.get("aud"), expected_audience):
        findings.append(Finding(test_name, "error", "audience", f"Expected audience {expected_audience}, got {claims.get('aud')}"))

    for claim_name in required_claims or []:
        if claim_name not in claims:
            findings.append(Finding(test_name, "error", "required_claim", f"Missing required claim: {claim_name}"))

    scopes = token_scopes(claims)
    for scope in expected_scopes or []:
        if scope not in scopes:
            findings.append(Finding(test_name, "error", "scope", f"Missing expected scope: {scope}"))

    passed = not any(f.severity == "error" for f in findings)
    return JwtValidationResult(test_name, token_source, token_type, passed, header, claims, findings)


def _decode_verified(token: str, header: dict[str, Any], jwks: dict[str, Any] | None, issuer: str | None, audience: str | None) -> dict[str, Any]:
    if not jwks or not jwks.get("keys"):
        raise InvalidTokenError("JWKS keys are required for signature validation")
    kid = header.get("kid")
    alg = header.get("alg")
    if not kid:
        raise InvalidTokenError("JWT header is missing kid")
    signing_key = None
    for key in jwks.get("keys", []):
        if key.get("kid") == kid:
            signing_key = jwt.algorithms.RSAAlgorithm.from_jwk(json.dumps(key))
            break
    if signing_key is None:
        raise InvalidTokenError(f"No matching JWKS key found for kid {kid}")
    options: dict[str, Any] = {}
    kwargs: dict[str, Any] = {"algorithms": [alg] if alg else ["RS256"]}
    if issuer:
        kwargs["issuer"] = issuer
    if audience:
        kwargs["audience"] = audience
    else:
        options["verify_aud"] = False
    if options:
        kwargs["options"] = options
    decoded = jwt.decode(token, signing_key, **kwargs)
    if not isinstance(decoded, dict):
        raise InvalidTokenError("JWT claims did not decode to an object")
    return decoded
