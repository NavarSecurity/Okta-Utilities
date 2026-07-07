from __future__ import annotations

import os
import time
from typing import Any
from urllib.parse import quote

import requests


class OktaApiError(RuntimeError):
    pass


class OktaClient:
    def __init__(self, org_url: str, token: str | None = None, timeout: int = 30, max_retries: int = 3, retry_backoff: int = 2):
        self.org_url = org_url.rstrip("/")
        self.token = token or os.getenv("OKTA_API_TOKEN", "").strip()
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_backoff = retry_backoff
        if not self.token:
            raise OktaApiError("OKTA_API_TOKEN is required in .env or environment for API operations")
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"SSWS {self.token}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        })

    def _url(self, path: str) -> str:
        if path.startswith("http"):
            return path
        return f"{self.org_url}{path}"

    def request(self, method: str, path: str, **kwargs: Any) -> Any:
        url = self._url(path)
        for attempt in range(self.max_retries + 1):
            response = self.session.request(method, url, timeout=self.timeout, **kwargs)
            if response.status_code in {429, 500, 502, 503, 504} and attempt < self.max_retries:
                retry_after = response.headers.get("Retry-After")
                sleep_for = int(retry_after) if retry_after and retry_after.isdigit() else self.retry_backoff * (attempt + 1)
                time.sleep(sleep_for)
                continue
            if response.status_code >= 400:
                try:
                    details = response.json()
                except Exception:
                    details = response.text
                raise OktaApiError(f"{method} {url} failed with {response.status_code}: {details}")
            if response.status_code == 204 or not response.content:
                return None
            return response.json()
        raise OktaApiError(f"{method} {url} failed after retries")

    def paged_get(self, path: str) -> list[dict[str, Any]]:
        url = self._url(path)
        items: list[dict[str, Any]] = []
        while url:
            response = self.session.get(url, timeout=self.timeout)
            if response.status_code >= 400:
                try:
                    details = response.json()
                except Exception:
                    details = response.text
                raise OktaApiError(f"GET {url} failed with {response.status_code}: {details}")
            payload = response.json() if response.content else []
            if isinstance(payload, list):
                items.extend(payload)
            else:
                raise OktaApiError(f"Expected list response from {url}")
            next_url = None
            links = response.links or {}
            if "next" in links:
                next_url = links["next"].get("url")
            url = next_url
        return items

    def find_group_by_name(self, name: str) -> dict[str, Any] | None:
        matches = self.paged_get(f"/api/v1/groups?q={quote(name)}&limit=200")
        exact = [g for g in matches if (g.get("profile", {}).get("name") or "").strip().lower() == name.strip().lower()]
        if len(exact) > 1:
            raise OktaApiError(f"Multiple groups found with name: {name}")
        return exact[0] if exact else None

    def get_user(self, identifier: str) -> dict[str, Any] | None:
        try:
            return self.request("GET", f"/api/v1/users/{quote(identifier, safe='')}")
        except OktaApiError as e:
            if "404" in str(e):
                return None
            raise

    def get_group_users(self, group_id: str) -> list[dict[str, Any]]:
        return self.paged_get(f"/api/v1/groups/{quote(group_id, safe='')}/users?limit=200")

    def add_user_to_group(self, group_id: str, user_id: str) -> None:
        self.request("PUT", f"/api/v1/groups/{quote(group_id, safe='')}/users/{quote(user_id, safe='')}")

    def remove_user_from_group(self, group_id: str, user_id: str) -> None:
        self.request("DELETE", f"/api/v1/groups/{quote(group_id, safe='')}/users/{quote(user_id, safe='')}")
