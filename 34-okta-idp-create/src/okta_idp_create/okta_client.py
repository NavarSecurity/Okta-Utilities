from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any
from urllib.parse import urljoin

import requests


class OktaApiError(RuntimeError):
    pass


@dataclass
class OktaClient:
    org_url: str
    api_token: str
    timeout_seconds: int = 30

    @classmethod
    def from_env(cls, timeout_seconds: int = 30) -> "OktaClient":
        org_url = os.getenv("OKTA_ORG_URL", "").strip().rstrip("/")
        api_token = os.getenv("OKTA_API_TOKEN", "").strip()
        if not org_url:
            raise OktaApiError("OKTA_ORG_URL is not set")
        if not api_token:
            raise OktaApiError("OKTA_API_TOKEN is not set")
        return cls(org_url=org_url, api_token=api_token, timeout_seconds=timeout_seconds)

    @property
    def headers(self) -> dict[str, str]:
        return {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Authorization": f"SSWS {self.api_token}",
        }

    def _url(self, path: str) -> str:
        return urljoin(self.org_url + "/", path.lstrip("/"))

    def request(self, method: str, path_or_url: str, **kwargs: Any) -> Any:
        url = path_or_url if path_or_url.startswith("http") else self._url(path_or_url)
        response = requests.request(
            method=method,
            url=url,
            headers=self.headers,
            timeout=self.timeout_seconds,
            **kwargs,
        )
        if response.status_code >= 400:
            detail = response.text[:1000]
            raise OktaApiError(f"Okta API request failed: {method} {url} -> {response.status_code}: {detail}")
        if response.status_code == 204 or not response.text.strip():
            return None
        return response.json()

    def list_identity_providers(self) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []
        next_url: str | None = "/api/v1/idps?limit=200"
        while next_url:
            url = next_url if next_url.startswith("http") else self._url(next_url)
            response = requests.get(url, headers=self.headers, timeout=self.timeout_seconds)
            if response.status_code >= 400:
                raise OktaApiError(
                    f"Okta API request failed: GET {url} -> {response.status_code}: {response.text[:1000]}"
                )
            data = response.json()
            if isinstance(data, list):
                results.extend(data)
            next_url = _parse_next_link(response.headers.get("Link", ""))
        return results

    def create_identity_provider(self, payload: dict[str, Any]) -> dict[str, Any]:
        result = self.request("POST", "/api/v1/idps", json=payload)
        if not isinstance(result, dict):
            raise OktaApiError("Unexpected Okta response while creating Identity Provider")
        return result

    def activate_identity_provider(self, idp_id: str) -> Any:
        return self.request("POST", f"/api/v1/idps/{idp_id}/lifecycle/activate")


def _parse_next_link(link_header: str) -> str | None:
    if not link_header:
        return None
    for part in link_header.split(","):
        section = part.strip()
        if 'rel="next"' in section:
            start = section.find("<")
            end = section.find(">")
            if start != -1 and end != -1 and end > start:
                return section[start + 1 : end]
    return None


def find_existing_by_name(idps: list[dict[str, Any]], name: str) -> dict[str, Any] | None:
    for idp in idps:
        if idp.get("name") == name:
            return idp
    return None
