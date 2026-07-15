from __future__ import annotations

import os
import time
from typing import Any
from urllib.parse import urljoin

import requests
from dotenv import load_dotenv


class OktaClientError(RuntimeError):
    pass


class OktaClient:
    def __init__(self, org_url: str | None = None, api_token: str | None = None, timeout_seconds: int = 30):
        load_dotenv()
        self.org_url = (org_url or os.getenv("OKTA_ORG_URL") or "").rstrip("/")
        self.api_token = api_token or os.getenv("OKTA_API_TOKEN") or ""
        self.timeout_seconds = timeout_seconds
        if not self.org_url:
            raise OktaClientError("OKTA_ORG_URL is required")
        if not self.api_token:
            raise OktaClientError("OKTA_API_TOKEN is required")
        if "/api/v1" in self.org_url:
            raise OktaClientError("OKTA_ORG_URL should be the base org URL, not /api/v1")
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"SSWS {self.api_token}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        })

    def _url(self, path: str) -> str:
        if path.startswith("http://") or path.startswith("https://"):
            return path
        return urljoin(f"{self.org_url}/", path.lstrip("/"))

    def get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        url = self._url(path)
        response = self.session.get(url, params=params, timeout=self.timeout_seconds)
        if response.status_code == 429:
            retry_after = int(response.headers.get("Retry-After", "1"))
            time.sleep(min(retry_after, 10))
            response = self.session.get(url, params=params, timeout=self.timeout_seconds)
        if response.status_code >= 400:
            raise OktaClientError(f"GET {path} returned {response.status_code}: {response.text[:500]}")
        if not response.text:
            return None
        return response.json()

    def get_with_status(self, path: str, params: dict[str, Any] | None = None) -> tuple[int, Any, str]:
        url = self._url(path)
        response = self.session.get(url, params=params, timeout=self.timeout_seconds)
        if response.status_code == 429:
            retry_after = int(response.headers.get("Retry-After", "1"))
            time.sleep(min(retry_after, 10))
            response = self.session.get(url, params=params, timeout=self.timeout_seconds)
        try:
            payload = response.json() if response.text else None
        except Exception:
            payload = None
        return response.status_code, payload, response.text

    def paged_get(self, path: str, params: dict[str, Any] | None = None) -> list[Any]:
        params = dict(params or {})
        params.setdefault("limit", 200)
        url = self._url(path)
        items: list[Any] = []
        while url:
            response = self.session.get(url, params=params if "?" not in url else None, timeout=self.timeout_seconds)
            if response.status_code == 429:
                retry_after = int(response.headers.get("Retry-After", "1"))
                time.sleep(min(retry_after, 10))
                response = self.session.get(url, params=params if "?" not in url else None, timeout=self.timeout_seconds)
            if response.status_code >= 400:
                raise OktaClientError(f"GET {url} returned {response.status_code}: {response.text[:500]}")
            payload = response.json() if response.text else []
            if isinstance(payload, list):
                items.extend(payload)
            else:
                items.append(payload)
            url = _next_link(response.headers.get("Link", ""))
            params = None
        return items

    def list_apps(self) -> list[dict[str, Any]]:
        return self.paged_get("/api/v1/apps", params={"limit": 200})

    def get_app_schema(self, app_id: str) -> Any:
        return self.get(f"/api/v1/meta/schemas/apps/{app_id}/default")

    def get_app_schema_with_status(self, app_id: str) -> tuple[int, Any, str]:
        return self.get_with_status(f"/api/v1/meta/schemas/apps/{app_id}/default")

    def list_profile_mappings(self) -> list[dict[str, Any]]:
        return self.paged_get("/api/v1/mappings", params={"limit": 200})

    def get_profile_mapping(self, mapping_id: str) -> Any:
        return self.get(f"/api/v1/mappings/{mapping_id}")

    def get_app_features_with_status(self, app_id: str) -> tuple[int, Any, str]:
        return self.get_with_status(f"/api/v1/apps/{app_id}/features")


def _next_link(link_header: str) -> str | None:
    if not link_header:
        return None
    for part in link_header.split(","):
        section = part.strip()
        if 'rel="next"' in section:
            start = section.find("<")
            end = section.find(">")
            if start != -1 and end != -1 and end > start:
                return section[start + 1:end]
    return None
