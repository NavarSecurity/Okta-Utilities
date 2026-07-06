from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

try:
    from dotenv import load_dotenv
except Exception:  # pragma: no cover
    load_dotenv = None


@dataclass
class ClientConfig:
    client_id: str | None = None
    client_secret: str | None = None
    token_endpoint_auth_method: str = "client_secret_basic"


@dataclass
class TokenSources:
    access_token: str | None = None
    id_token: str | None = None
    access_token_file: str | None = None
    id_token_file: str | None = None
    authorization_code: str | None = None
    code_verifier: str | None = None


@dataclass
class TestSettings:
    run_discovery: bool = True
    fetch_jwks: bool = True
    include_raw_responses: bool = False
    request_timeout_seconds: int = 30
    max_retries: int = 3
    continue_on_error: bool = True
    redact_tokens_in_output: bool = True


@dataclass
class TokenTestConfig:
    org_url: str
    authorization_server_id: str
    issuer_url: str
    output_dir: Path
    settings: TestSettings
    client: ClientConfig
    token_sources: TokenSources
    client_credentials_tests: list[dict[str, Any]] = field(default_factory=list)
    authorization_code_tests: list[dict[str, Any]] = field(default_factory=list)
    jwt_validation_tests: list[dict[str, Any]] = field(default_factory=list)
    introspection_tests: list[dict[str, Any]] = field(default_factory=list)


def normalize_org_url(url: str) -> str:
    url = (url or "").strip().rstrip("/")
    if not url:
        raise ValueError("Missing Okta org URL")
    parsed = urlparse(url)
    if parsed.scheme not in {"https", "http"} or not parsed.netloc:
        raise ValueError(f"Invalid Okta org URL: {url}")
    host = parsed.netloc.lower()
    path = parsed.path.strip("/")
    if "-admin.okta" in host or "-admin.oktapreview" in host or "-admin.okta-emea" in host:
        raise ValueError("Use the normal Okta org URL, not the Admin Console -admin URL")
    if path:
        raise ValueError("Use the Okta org base URL only. Do not include /admin, /api/v1, or /oauth2 paths")
    return f"{parsed.scheme}://{parsed.netloc}".rstrip("/")


def normalize_issuer_url(org_url: str, authorization_server_id: str, issuer_url: str | None = None) -> str:
    if issuer_url:
        issuer = issuer_url.strip().rstrip("/")
        parsed = urlparse(issuer)
        if parsed.scheme not in {"https", "http"} or not parsed.netloc:
            raise ValueError(f"Invalid issuer URL: {issuer}")
        return issuer
    auth_id = (authorization_server_id or "default").strip()
    if not auth_id:
        auth_id = "default"
    if auth_id.lower() in {"org", "org_authorization_server", "org-auth-server"}:
        return org_url.rstrip("/")
    return f"{org_url.rstrip('/')}/oauth2/{auth_id}"


def _string_or_none(value: Any) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError("Expected string value")
    value = value.strip()
    return value or None


def _as_list_of_dicts(value: Any, field_name: str) -> list[dict[str, Any]]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise ValueError(f"{field_name} must be a list")
    result: list[dict[str, Any]] = []
    for item in value:
        if not isinstance(item, dict):
            raise ValueError(f"{field_name} must contain objects")
        result.append(item)
    return result


def _read_optional_file(path_text: str | None) -> str | None:
    if not path_text:
        return None
    path = Path(path_text)
    if not path.exists():
        raise FileNotFoundError(f"Token file not found: {path}")
    return path.read_text(encoding="utf-8").strip() or None


def load_config(config_path: str | Path) -> TokenTestConfig:
    if load_dotenv:
        load_dotenv()

    path = Path(config_path)
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")
    raw = json.loads(path.read_text(encoding="utf-8"))

    env_org_url = os.getenv("OKTA_ORG_URL")
    org_url = normalize_org_url(env_org_url or raw.get("orgUrl", ""))
    authorization_server_id = str(raw.get("authorizationServerId") or "default").strip() or "default"
    issuer_url = normalize_issuer_url(org_url, authorization_server_id, raw.get("issuerUrl"))
    output_dir = Path(raw.get("outputDir") or "output")

    settings_raw = raw.get("settings") or {}
    settings = TestSettings(
        run_discovery=bool(settings_raw.get("runDiscovery", True)),
        fetch_jwks=bool(settings_raw.get("fetchJwks", True)),
        include_raw_responses=bool(settings_raw.get("includeRawResponses", False)),
        request_timeout_seconds=int(settings_raw.get("requestTimeoutSeconds", 30)),
        max_retries=int(settings_raw.get("maxRetries", 3)),
        continue_on_error=bool(settings_raw.get("continueOnError", True)),
        redact_tokens_in_output=bool(settings_raw.get("redactTokensInOutput", True)),
    )
    if settings.request_timeout_seconds <= 0:
        raise ValueError("requestTimeoutSeconds must be greater than 0")
    if settings.max_retries < 0:
        raise ValueError("maxRetries must be 0 or greater")

    client_raw = raw.get("client") or {}
    client = ClientConfig(
        client_id=os.getenv("OKTA_CLIENT_ID") or _string_or_none(client_raw.get("clientId")),
        client_secret=os.getenv("OKTA_CLIENT_SECRET") or _string_or_none(client_raw.get("clientSecret")),
        token_endpoint_auth_method=str(client_raw.get("tokenEndpointAuthMethod") or "client_secret_basic"),
    )
    if client.token_endpoint_auth_method not in {"client_secret_basic", "client_secret_post", "none"}:
        raise ValueError("client.tokenEndpointAuthMethod must be client_secret_basic, client_secret_post, or none")

    sources_raw = raw.get("tokenSources") or {}
    access_file = _string_or_none(sources_raw.get("accessTokenFile"))
    id_file = _string_or_none(sources_raw.get("idTokenFile"))
    token_sources = TokenSources(
        access_token=os.getenv("OKTA_ACCESS_TOKEN") or _read_optional_file(access_file) or _string_or_none(sources_raw.get("accessToken")),
        id_token=os.getenv("OKTA_ID_TOKEN") or _read_optional_file(id_file) or _string_or_none(sources_raw.get("idToken")),
        access_token_file=access_file,
        id_token_file=id_file,
        authorization_code=os.getenv("OKTA_AUTHORIZATION_CODE") or _string_or_none(sources_raw.get("authorizationCode")),
        code_verifier=os.getenv("OKTA_CODE_VERIFIER") or _string_or_none(sources_raw.get("codeVerifier")),
    )

    return TokenTestConfig(
        org_url=org_url,
        authorization_server_id=authorization_server_id,
        issuer_url=issuer_url,
        output_dir=output_dir,
        settings=settings,
        client=client,
        token_sources=token_sources,
        client_credentials_tests=_as_list_of_dicts(raw.get("clientCredentialsTests"), "clientCredentialsTests"),
        authorization_code_tests=_as_list_of_dicts(raw.get("authorizationCodeTests"), "authorizationCodeTests"),
        jwt_validation_tests=_as_list_of_dicts(raw.get("jwtValidationTests"), "jwtValidationTests"),
        introspection_tests=_as_list_of_dicts(raw.get("introspectionTests"), "introspectionTests"),
    )
