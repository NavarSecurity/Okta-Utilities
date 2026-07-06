from __future__ import annotations

import time
from typing import Any

import requests


class OktaTokenError(RuntimeError):
    def __init__(self, message: str, status_code: int | None = None, response_body: Any | None = None):
        super().__init__(message)
        self.status_code = status_code
        self.response_body = response_body


class OktaTokenClient:
    def __init__(self, issuer_url: str, timeout_seconds: int = 30, max_retries: int = 3):
        self.issuer_url = issuer_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries
        self.session = requests.Session()
        self.session.headers.update({"Accept": "application/json", "User-Agent": "okta-token-tester/0.1.1"})

    @property
    def discovery_url(self) -> str:
        return f"{self.issuer_url}/.well-known/openid-configuration"

    @property
    def token_endpoint(self) -> str:
        return f"{self.issuer_url}/v1/token"

    @property
    def introspection_endpoint(self) -> str:
        return f"{self.issuer_url}/v1/introspect"

    @property
    def jwks_uri(self) -> str:
        return f"{self.issuer_url}/v1/keys"

    def get_json(self, url: str) -> Any:
        data, _ = self._request("GET", url)
        return data

    def fetch_discovery(self) -> dict[str, Any]:
        data = self.get_json(self.discovery_url)
        if not isinstance(data, dict):
            raise OktaTokenError("Discovery endpoint returned an unexpected response")
        return data

    def fetch_jwks(self, jwks_uri: str | None = None) -> dict[str, Any]:
        data = self.get_json(jwks_uri or self.jwks_uri)
        if not isinstance(data, dict):
            raise OktaTokenError("JWKS endpoint returned an unexpected response")
        return data

    def request_client_credentials_token(
        self,
        client_id: str,
        client_secret: str | None,
        scopes: list[str],
        auth_method: str = "client_secret_basic",
    ) -> dict[str, Any]:
        data = {"grant_type": "client_credentials"}
        if scopes:
            data["scope"] = " ".join(scopes)
        auth = None
        if auth_method == "client_secret_basic":
            if not client_secret:
                raise OktaTokenError("client_secret_basic requires a client secret")
            auth = (client_id, client_secret)
        elif auth_method == "client_secret_post":
            data["client_id"] = client_id
            if client_secret:
                data["client_secret"] = client_secret
        elif auth_method == "none":
            data["client_id"] = client_id
        else:
            raise OktaTokenError(f"Unsupported token endpoint auth method: {auth_method}")
        result, _ = self._request("POST", self.token_endpoint, data=data, auth=auth)
        if not isinstance(result, dict):
            raise OktaTokenError("Token endpoint returned an unexpected response")
        return result

    def exchange_authorization_code(
        self,
        client_id: str,
        client_secret: str | None,
        authorization_code: str,
        redirect_uri: str,
        code_verifier: str | None,
        auth_method: str = "client_secret_basic",
    ) -> dict[str, Any]:
        data = {"grant_type": "authorization_code", "code": authorization_code, "redirect_uri": redirect_uri}
        if code_verifier:
            data["code_verifier"] = code_verifier
        auth = None
        if auth_method == "client_secret_basic":
            if not client_secret:
                raise OktaTokenError("client_secret_basic requires a client secret")
            auth = (client_id, client_secret)
        elif auth_method == "client_secret_post":
            data["client_id"] = client_id
            if client_secret:
                data["client_secret"] = client_secret
        elif auth_method == "none":
            data["client_id"] = client_id
        else:
            raise OktaTokenError(f"Unsupported token endpoint auth method: {auth_method}")
        result, _ = self._request("POST", self.token_endpoint, data=data, auth=auth)
        if not isinstance(result, dict):
            raise OktaTokenError("Token endpoint returned an unexpected response")
        return result

    def introspect_token(
        self,
        client_id: str,
        client_secret: str | None,
        token: str,
        token_type_hint: str | None = None,
        auth_method: str = "client_secret_basic",
    ) -> dict[str, Any]:
        data = {"token": token}
        if token_type_hint:
            data["token_type_hint"] = token_type_hint
        auth = None
        if auth_method == "client_secret_basic":
            if not client_secret:
                raise OktaTokenError("client_secret_basic requires a client secret")
            auth = (client_id, client_secret)
        elif auth_method == "client_secret_post":
            data["client_id"] = client_id
            if client_secret:
                data["client_secret"] = client_secret
        elif auth_method == "none":
            data["client_id"] = client_id
        else:
            raise OktaTokenError(f"Unsupported token endpoint auth method: {auth_method}")
        result, _ = self._request("POST", self.introspection_endpoint, data=data, auth=auth)
        if not isinstance(result, dict):
            raise OktaTokenError("Introspection endpoint returned an unexpected response")
        return result

    def _request(self, method: str, url: str, data: dict[str, Any] | None = None, auth: Any | None = None) -> tuple[Any, dict[str, str]]:
        last_error: Exception | None = None
        for attempt in range(self.max_retries + 1):
            try:
                response = self.session.request(method, url, data=data, auth=auth, timeout=self.timeout_seconds)
                if response.status_code == 429 or 500 <= response.status_code <= 599:
                    if attempt < self.max_retries:
                        retry_after = response.headers.get("Retry-After")
                        sleep_seconds = int(retry_after) if retry_after and retry_after.isdigit() else min(2**attempt, 8)
                        time.sleep(sleep_seconds)
                        continue
                if response.status_code >= 400:
                    try:
                        body: Any = response.json()
                    except Exception:
                        body = response.text
                    raise OktaTokenError(f"Okta token request failed: {response.status_code} {response.reason}", response.status_code, body)
                if not response.text:
                    return None, dict(response.headers)
                try:
                    return response.json(), dict(response.headers)
                except Exception as exc:  # pragma: no cover
                    raise OktaTokenError("Okta returned non-JSON response", response_body=response.text) from exc
            except (requests.Timeout, requests.ConnectionError) as exc:
                last_error = exc
                if attempt < self.max_retries:
                    time.sleep(min(2**attempt, 8))
                    continue
                raise OktaTokenError(f"Okta token request failed after retries: {exc}") from exc
        raise OktaTokenError(f"Okta token request failed: {last_error}")
