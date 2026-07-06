from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from .config import TokenTestConfig
from .jwt_utils import Finding, JwtValidationResult, validate_jwt
from .okta_client import OktaTokenClient, OktaTokenError
from .redaction import fingerprint, redact_dict


@dataclass
class FlowResult:
    test_name: str
    flow_type: str
    passed: bool
    response_summary: dict[str, Any] = field(default_factory=dict)
    token_fingerprints: dict[str, str] = field(default_factory=dict)
    error: str | None = None
    status_code: int | None = None
    response_body: Any | None = None


@dataclass
class IntrospectionResult:
    test_name: str
    passed: bool
    active: bool | None = None
    response_summary: dict[str, Any] = field(default_factory=dict)
    error: str | None = None
    status_code: int | None = None
    response_body: Any | None = None


@dataclass
class TokenTestResult:
    mode: str
    org_url: str
    issuer_url: str
    discovery: dict[str, Any] | None = None
    jwks_summary: list[dict[str, Any]] = field(default_factory=list)
    client_credentials_results: list[FlowResult] = field(default_factory=list)
    authorization_code_results: list[FlowResult] = field(default_factory=list)
    jwt_validation_results: list[JwtValidationResult] = field(default_factory=list)
    introspection_results: list[IntrospectionResult] = field(default_factory=list)
    errors: list[dict[str, Any]] = field(default_factory=list)

    def summary(self) -> dict[str, int]:
        flow_results = self.client_credentials_results + self.authorization_code_results
        jwt_total = len(self.jwt_validation_results)
        introspection_total = len(self.introspection_results)
        failed = sum(1 for r in flow_results if not r.passed)
        failed += sum(1 for r in self.jwt_validation_results if not r.passed)
        failed += sum(1 for r in self.introspection_results if not r.passed)
        failed += len(self.errors)
        findings = sum(len(r.findings) for r in self.jwt_validation_results)
        return {
            "flowsTested": len(flow_results),
            "jwtValidations": jwt_total,
            "introspectionTests": introspection_total,
            "jwksKeys": len(self.jwks_summary),
            "findings": findings,
            "errors": len(self.errors),
            "failedChecks": failed,
        }


class TokenTester:
    def __init__(self, config: TokenTestConfig):
        self.config = config
        self.client = OktaTokenClient(config.issuer_url, config.settings.request_timeout_seconds, config.settings.max_retries)

    def build_plan(self) -> dict[str, Any]:
        cfg = self.config
        return {
            "mode": "dry-run",
            "orgUrl": cfg.org_url,
            "authorizationServerId": cfg.authorization_server_id,
            "issuerUrl": cfg.issuer_url,
            "willRunDiscovery": cfg.settings.run_discovery,
            "willFetchJwks": cfg.settings.fetch_jwks,
            "clientCredentialsTests": [_safe_test(item) for item in cfg.client_credentials_tests],
            "authorizationCodeTests": [_safe_test(item) for item in cfg.authorization_code_tests],
            "jwtValidationTests": [_safe_test(item) for item in cfg.jwt_validation_tests],
            "introspectionTests": [_safe_test(item) for item in cfg.introspection_tests],
            "tokenSourcesPresent": {
                "accessToken": bool(cfg.token_sources.access_token),
                "idToken": bool(cfg.token_sources.id_token),
                "authorizationCode": bool(cfg.token_sources.authorization_code),
                "codeVerifier": bool(cfg.token_sources.code_verifier),
            },
            "clientPresent": {
                "clientId": bool(cfg.client.client_id),
                "clientSecret": bool(cfg.client.client_secret),
                "tokenEndpointAuthMethod": cfg.client.token_endpoint_auth_method,
            },
        }

    def run_tests(self) -> TokenTestResult:
        result = TokenTestResult("test", self.config.org_url, self.config.issuer_url)
        jwks: dict[str, Any] | None = None

        if self.config.settings.run_discovery:
            try:
                discovery = self.client.fetch_discovery()
                result.discovery = redact_dict(discovery)
                if self.config.settings.fetch_jwks:
                    jwks_uri = discovery.get("jwks_uri")
                    jwks = self.client.fetch_jwks(jwks_uri)
                    result.jwks_summary = summarize_jwks(jwks)
            except Exception as exc:
                result.errors.append(_error_dict("discovery_or_jwks", exc))
                if not self.config.settings.continue_on_error:
                    return result
        elif self.config.settings.fetch_jwks:
            try:
                jwks = self.client.fetch_jwks()
                result.jwks_summary = summarize_jwks(jwks)
            except Exception as exc:
                result.errors.append(_error_dict("jwks", exc))
                if not self.config.settings.continue_on_error:
                    return result

        issued_tokens: dict[str, str] = {}
        for test in self.config.client_credentials_tests:
            flow = self._run_client_credentials(test)
            result.client_credentials_results.append(flow)
            if flow.passed and getattr(flow, "_tokens", None):  # type: ignore[attr-defined]
                _store_issued_tokens(issued_tokens, flow._tokens, "clientCredentials", flow.test_name)  # type: ignore[attr-defined]
            if not flow.passed and not self.config.settings.continue_on_error:
                return result

        for test in self.config.authorization_code_tests:
            flow = self._run_authorization_code(test)
            result.authorization_code_results.append(flow)
            if flow.passed and getattr(flow, "_tokens", None):  # type: ignore[attr-defined]
                _store_issued_tokens(issued_tokens, flow._tokens, "authorizationCode", flow.test_name)  # type: ignore[attr-defined]
            if not flow.passed and not self.config.settings.continue_on_error:
                return result

        for test in self.config.jwt_validation_tests:
            validation = self._run_jwt_validation(test, jwks, issued_tokens)
            result.jwt_validation_results.append(validation)
            if not validation.passed and not self.config.settings.continue_on_error:
                return result

        for test in self.config.introspection_tests:
            introspection = self._run_introspection(test, issued_tokens)
            result.introspection_results.append(introspection)
            if not introspection.passed and not self.config.settings.continue_on_error:
                return result

        return result

    def _run_client_credentials(self, test: dict[str, Any]) -> FlowResult:
        name = str(test.get("name") or "Client Credentials Test")
        if not self.config.client.client_id:
            return FlowResult(name, "client_credentials", False, error="Missing client ID")
        try:
            scopes = _string_list(test.get("scopes"))
            token_response = self.client.request_client_credentials_token(
                self.config.client.client_id,
                self.config.client.client_secret,
                scopes,
                self.config.client.token_endpoint_auth_method,
            )
            summary, tokens = summarize_token_response(token_response)
            flow = FlowResult(name, "client_credentials", True, response_summary=summary, token_fingerprints={k: fingerprint(v) for k, v in tokens.items()})
            flow._tokens = tokens  # type: ignore[attr-defined]
            return flow
        except Exception as exc:
            return _flow_error(name, "client_credentials", exc)

    def _run_authorization_code(self, test: dict[str, Any]) -> FlowResult:
        name = str(test.get("name") or "Authorization Code Exchange")
        if not self.config.client.client_id:
            return FlowResult(name, "authorization_code", False, error="Missing client ID")
        code = test.get("authorizationCode") or self.config.token_sources.authorization_code
        if not code:
            return FlowResult(name, "authorization_code", False, error="Missing authorization code")
        redirect_uri = test.get("redirectUri")
        if not redirect_uri:
            return FlowResult(name, "authorization_code", False, error="Missing redirectUri")
        code_verifier = test.get("codeVerifier") or self.config.token_sources.code_verifier
        try:
            token_response = self.client.exchange_authorization_code(
                self.config.client.client_id,
                self.config.client.client_secret,
                str(code),
                str(redirect_uri),
                str(code_verifier) if code_verifier else None,
                self.config.client.token_endpoint_auth_method,
            )
            summary, tokens = summarize_token_response(token_response)
            flow = FlowResult(name, "authorization_code", True, response_summary=summary, token_fingerprints={k: fingerprint(v) for k, v in tokens.items()})
            flow._tokens = tokens  # type: ignore[attr-defined]
            return flow
        except Exception as exc:
            return _flow_error(name, "authorization_code", exc)

    def _run_jwt_validation(self, test: dict[str, Any], jwks: dict[str, Any] | None, issued_tokens: dict[str, str]) -> JwtValidationResult:
        name = str(test.get("name") or "JWT Validation")
        token_source = str(test.get("tokenSource") or "accessToken")
        token_type = str(test.get("tokenType") or "access")
        token = self._resolve_token(token_source, issued_tokens)
        if not token:
            return JwtValidationResult(
                test_name=name,
                token_source=token_source,
                token_type=token_type,
                passed=False,
                findings=[Finding(name, "error", "token_source", f"No token found for source {token_source}")],
            )
        return validate_jwt(
            token,
            name,
            token_source,
            token_type,
            self.config.issuer_url,
            jwks,
            expected_issuer=test.get("expectedIssuer"),
            expected_audience=test.get("expectedAudience"),
            expected_scopes=_string_list(test.get("expectedScopes")),
            required_claims=_string_list(test.get("requiredClaims")),
            verify_signature=bool(test.get("verifySignature", True)),
        )

    def _run_introspection(self, test: dict[str, Any], issued_tokens: dict[str, str]) -> IntrospectionResult:
        name = str(test.get("name") or "Introspection Test")
        if not self.config.client.client_id:
            return IntrospectionResult(name, False, error="Missing client ID")
        token_source = str(test.get("tokenSource") or "accessToken")
        token = self._resolve_token(token_source, issued_tokens)
        if not token:
            return IntrospectionResult(name, False, error=f"No token found for source {token_source}")
        expected_active = test.get("expectedActive")
        try:
            response = self.client.introspect_token(
                self.config.client.client_id,
                self.config.client.client_secret,
                token,
                test.get("tokenTypeHint"),
                self.config.client.token_endpoint_auth_method,
            )
            active = bool(response.get("active"))
            passed = active == bool(expected_active) if expected_active is not None else active
            summary = {k: v for k, v in response.items() if k not in {"access_token", "id_token", "refresh_token"}}
            return IntrospectionResult(name, passed, active=active, response_summary=redact_dict(summary))
        except Exception as exc:
            err = _error_dict("introspection", exc)
            return IntrospectionResult(name, False, error=err["message"], status_code=err.get("statusCode"), response_body=err.get("responseBody"))

    def _resolve_token(self, source: str, issued_tokens: dict[str, str]) -> str | None:
        """Resolve a token source from explicit config first, then runtime-issued tokens.

        The default config uses tokenSource="accessToken" for validation and introspection.
        If the user did not paste an access token, a successful token-flow test should
        automatically supply the access token for later validation steps.
        """
        if source == "accessToken":
            return self.config.token_sources.access_token or issued_tokens.get("accessToken") or issued_tokens.get("access_token")
        if source == "idToken":
            return self.config.token_sources.id_token or issued_tokens.get("idToken") or issued_tokens.get("id_token")
        if source in issued_tokens:
            return issued_tokens[source]
        if source == "access_token":
            return issued_tokens.get("access_token") or issued_tokens.get("accessToken")
        if source == "id_token":
            return issued_tokens.get("id_token") or issued_tokens.get("idToken")
        if source == "clientCredentialsAccessToken":
            return issued_tokens.get("clientCredentialsAccessToken") or issued_tokens.get("accessToken") or issued_tokens.get("access_token")
        if source == "authorizationCodeAccessToken":
            return issued_tokens.get("authorizationCodeAccessToken") or issued_tokens.get("accessToken") or issued_tokens.get("access_token")
        if source == "authorizationCodeIdToken":
            return issued_tokens.get("authorizationCodeIdToken") or issued_tokens.get("idToken") or issued_tokens.get("id_token")
        return None


def _store_issued_tokens(store: dict[str, str], tokens: dict[str, str], flow_prefix: str, test_name: str) -> None:
    """Store tokens from a successful flow using generic and flow-specific aliases."""
    store.update(tokens)
    access_token = tokens.get("access_token")
    id_token = tokens.get("id_token")
    refresh_token = tokens.get("refresh_token")
    safe_test_name = _token_source_name(test_name)

    if access_token:
        store.setdefault("accessToken", access_token)
        store[f"{flow_prefix}AccessToken"] = access_token
        store[f"{flow_prefix}:{safe_test_name}:accessToken"] = access_token
    if id_token:
        store.setdefault("idToken", id_token)
        store[f"{flow_prefix}IdToken"] = id_token
        store[f"{flow_prefix}:{safe_test_name}:idToken"] = id_token
    if refresh_token:
        store.setdefault("refreshToken", refresh_token)
        store[f"{flow_prefix}RefreshToken"] = refresh_token
        store[f"{flow_prefix}:{safe_test_name}:refreshToken"] = refresh_token


def _token_source_name(value: str) -> str:
    return "".join(ch if ch.isalnum() or ch in {"-", "_"} else "_" for ch in value.strip()) or "default"


def summarize_jwks(jwks: dict[str, Any]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for key in jwks.get("keys", []):
        result.append(
            {
                "kid": key.get("kid", ""),
                "kty": key.get("kty", ""),
                "alg": key.get("alg", ""),
                "use": key.get("use", ""),
                "key_ops": ",".join(key.get("key_ops", [])) if isinstance(key.get("key_ops"), list) else "",
            }
        )
    return result


def summarize_token_response(response: dict[str, Any]) -> tuple[dict[str, Any], dict[str, str]]:
    tokens: dict[str, str] = {}
    for key in ["access_token", "id_token", "refresh_token"]:
        value = response.get(key)
        if isinstance(value, str) and value:
            tokens[key] = value
    summary = {k: v for k, v in response.items() if k not in tokens}
    summary["tokenFingerprints"] = {k: fingerprint(v) for k, v in tokens.items()}
    return summary, tokens


def _flow_error(name: str, flow_type: str, exc: Exception) -> FlowResult:
    err = _error_dict(flow_type, exc)
    return FlowResult(name, flow_type, False, error=err["message"], status_code=err.get("statusCode"), response_body=err.get("responseBody"))


def _error_dict(stage: str, exc: Exception) -> dict[str, Any]:
    if isinstance(exc, OktaTokenError):
        return {"stage": stage, "message": str(exc), "statusCode": exc.status_code, "responseBody": redact_dict(exc.response_body) if isinstance(exc.response_body, dict) else exc.response_body}
    return {"stage": stage, "message": str(exc)}


def _string_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [part for part in value.split() if part]
    if isinstance(value, list):
        return [str(item) for item in value if str(item)]
    raise ValueError("Expected string or list of strings")


def _safe_test(test: dict[str, Any]) -> dict[str, Any]:
    return redact_dict(dict(test))


def result_to_dict(result: TokenTestResult) -> dict[str, Any]:
    return asdict(result)
