from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any
from urllib.parse import urljoin

import requests


class OktaApiError(RuntimeError):
    """Raised when an Okta API request fails."""


@dataclass
class OktaClient:
    org_url: str
    api_token: str
    timeout_seconds: int = 30
    max_retries: int = 3

    def __post_init__(self) -> None:
        self.org_url = self.org_url.rstrip("/")
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Authorization": f"SSWS {self.api_token}",
                "Accept": "application/json",
                "Content-Type": "application/json",
                "User-Agent": "okta-trusted-origin-manager/1.0.0",
            }
        )

    def _url(self, path: str) -> str:
        if path.startswith("http://") or path.startswith("https://"):
            return path
        return urljoin(f"{self.org_url}/", path.lstrip("/"))

    @staticmethod
    def _next_link(link_header: str | None) -> str | None:
        if not link_header:
            return None
        for part in link_header.split(","):
            section = part.strip()
            if 'rel="next"' not in section:
                continue
            if section.startswith("<") and ">" in section:
                return section[1 : section.index(">")]
        return None

    def request(self, method: str, path: str, **kwargs: Any) -> requests.Response:
        url = self._url(path)
        for attempt in range(self.max_retries + 1):
            response = self.session.request(method, url, timeout=self.timeout_seconds, **kwargs)
            if response.status_code == 429 and attempt < self.max_retries:
                reset_header = response.headers.get("x-rate-limit-reset")
                sleep_seconds = 2
                if reset_header and reset_header.isdigit():
                    sleep_seconds = max(1, int(reset_header) - int(time.time()) + 1)
                time.sleep(min(sleep_seconds, 30))
                continue
            if response.status_code >= 500 and attempt < self.max_retries:
                time.sleep(min(2**attempt, 10))
                continue
            if response.status_code >= 400:
                message = response.text
                try:
                    payload = response.json()
                    message = payload.get("errorSummary") or payload.get("errorCode") or response.text
                except ValueError:
                    pass
                raise OktaApiError(f"Okta API request failed: {method} {path} returned {response.status_code}: {message}")
            return response
        raise OktaApiError(f"Okta API request failed after retries: {method} {path}")

    def paged_get(self, path: str) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        next_url: str | None = path
        while next_url:
            response = self.request("GET", next_url)
            page = response.json()
            if not isinstance(page, list):
                raise OktaApiError(f"Expected a list response from {path}")
            items.extend(page)
            next_url = self._next_link(response.headers.get("Link"))
        return items

    def list_trusted_origins(self) -> list[dict[str, Any]]:
        return self.paged_get("/api/v1/trustedOrigins?limit=200")

    def create_trusted_origin(self, payload: dict[str, Any]) -> dict[str, Any]:
        response = self.request("POST", "/api/v1/trustedOrigins", json=payload)
        return response.json()

    def replace_trusted_origin(self, origin_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        response = self.request("PUT", f"/api/v1/trustedOrigins/{origin_id}", json=payload)
        return response.json()

    def activate_trusted_origin(self, origin_id: str) -> dict[str, Any]:
        response = self.request("POST", f"/api/v1/trustedOrigins/{origin_id}/lifecycle/activate")
        return response.json() if response.text else {}

    def deactivate_trusted_origin(self, origin_id: str) -> dict[str, Any]:
        response = self.request("POST", f"/api/v1/trustedOrigins/{origin_id}/lifecycle/deactivate")
        return response.json() if response.text else {}
