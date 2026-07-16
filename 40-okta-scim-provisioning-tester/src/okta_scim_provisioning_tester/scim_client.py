from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any
from urllib.parse import urljoin

import requests
from requests import Response


@dataclass
class ScimResponse:
    method: str
    url: str
    status_code: int
    ok: bool
    body: Any
    error: str | None = None


class ScimClient:
    def __init__(self, base_url: str, auth_type: str, timeout_seconds: int = 30, verify_ssl: bool = True):
        self.base_url = base_url.rstrip("/") + "/"
        self.auth_type = auth_type.lower()
        self.timeout_seconds = timeout_seconds
        self.verify_ssl = verify_ssl
        self.session = requests.Session()
        self.session.headers.update({"Accept": "application/scim+json, application/json"})
        if self.auth_type == "bearer":
            token = os.getenv("SCIM_BEARER_TOKEN", "").strip()
            if not token:
                raise ValueError("SCIM_AUTH_TYPE is bearer, but SCIM_BEARER_TOKEN is missing.")
            self.session.headers.update({"Authorization": f"Bearer {token}"})
        elif self.auth_type == "basic":
            username = os.getenv("SCIM_BASIC_USERNAME", "").strip()
            password = os.getenv("SCIM_BASIC_PASSWORD", "").strip()
            if not username or not password:
                raise ValueError("SCIM_AUTH_TYPE is basic, but SCIM_BASIC_USERNAME or SCIM_BASIC_PASSWORD is missing.")
            self.session.auth = (username, password)
        elif self.auth_type == "none":
            pass
        else:
            raise ValueError("Unsupported auth type.")

    def build_url(self, path: str) -> str:
        clean_path = path.lstrip("/")
        return urljoin(self.base_url, clean_path)

    def request(self, method: str, path: str, payload: dict[str, Any] | None = None) -> ScimResponse:
        url = self.build_url(path)
        headers = {}
        kwargs: dict[str, Any] = {
            "timeout": self.timeout_seconds,
            "verify": self.verify_ssl,
        }
        if payload is not None:
            headers["Content-Type"] = "application/scim+json"
            kwargs["json"] = payload
        try:
            response = self.session.request(method.upper(), url, headers=headers, **kwargs)
            return self._to_scim_response(method, url, response)
        except requests.RequestException as exc:
            return ScimResponse(method=method.upper(), url=url, status_code=0, ok=False, body=None, error=str(exc))

    @staticmethod
    def _to_scim_response(method: str, url: str, response: Response) -> ScimResponse:
        try:
            body: Any = response.json()
        except ValueError:
            body = response.text
        return ScimResponse(
            method=method.upper(),
            url=url,
            status_code=response.status_code,
            ok=200 <= response.status_code < 300,
            body=body,
            error=None if 200 <= response.status_code < 300 else f"HTTP {response.status_code}",
        )
