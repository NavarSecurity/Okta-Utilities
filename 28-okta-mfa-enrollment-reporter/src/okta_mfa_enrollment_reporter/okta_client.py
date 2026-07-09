from __future__ import annotations

import time
from typing import Any
from urllib.parse import quote

import requests


class OktaApiError(RuntimeError):
    def __init__(self, message: str, status_code: int | None = None, response_body: Any = None):
        super().__init__(message)
        self.status_code = status_code
        self.response_body = response_body


class OktaClient:
    def __init__(self, org_url: str, api_token: str, timeout: int = 30, max_retries: int = 3, page_limit: int = 200):
        self.org_url = org_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries
        self.page_limit = page_limit
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"SSWS {api_token}",
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "okta-mfa-enrollment-reporter/0.1.0",
        })
        self.request_counts: dict[str, int] = {}

    def _record(self, status: int) -> None:
        key = str(status)
        self.request_counts[key] = self.request_counts.get(key, 0) + 1

    def request(self, method: str, path_or_url: str, **kwargs: Any) -> requests.Response:
        url = path_or_url if path_or_url.startswith("http") else f"{self.org_url}{path_or_url}"
        last_error: Exception | None = None
        for attempt in range(self.max_retries + 1):
            try:
                response = self.session.request(method, url, timeout=self.timeout, **kwargs)
                self._record(response.status_code)
                if response.status_code == 429 or 500 <= response.status_code < 600:
                    if attempt < self.max_retries:
                        retry_after = response.headers.get("Retry-After")
                        delay = int(retry_after) if retry_after and retry_after.isdigit() else min(2 ** attempt, 10)
                        time.sleep(delay)
                        continue
                return response
            except requests.RequestException as exc:
                last_error = exc
                if attempt < self.max_retries:
                    time.sleep(min(2 ** attempt, 10))
                    continue
        raise OktaApiError(f"Okta request failed: {last_error}")

    def get_json(self, path_or_url: str, params: dict[str, Any] | None = None) -> Any:
        response = self.request("GET", path_or_url, params=params)
        if response.status_code >= 400:
            try:
                body = response.json()
            except ValueError:
                body = response.text
            raise OktaApiError(f"Okta GET failed with HTTP {response.status_code}", response.status_code, body)
        if response.text.strip() == "":
            return None
        return response.json()

    def paginate(self, path: str, params: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        next_url: str | None = path
        next_params = dict(params or {})
        while next_url:
            response = self.request("GET", next_url, params=next_params)
            if response.status_code >= 400:
                try:
                    body = response.json()
                except ValueError:
                    body = response.text
                raise OktaApiError(f"Okta list request failed with HTTP {response.status_code}", response.status_code, body)
            batch = response.json()
            if isinstance(batch, list):
                items.extend(batch)
            else:
                raise OktaApiError("Expected list response from Okta pagination endpoint.")
            next_url = self._next_link(response.headers.get("Link"))
            next_params = None
        return items

    @staticmethod
    def _next_link(link_header: str | None) -> str | None:
        if not link_header:
            return None
        parts = [part.strip() for part in link_header.split(",")]
        for part in parts:
            if 'rel="next"' in part:
                start = part.find("<")
                end = part.find(">")
                if start >= 0 and end > start:
                    return part[start + 1:end]
        return None

    def list_users(self) -> list[dict[str, Any]]:
        return self.paginate("/api/v1/users", params={"limit": self.page_limit})

    def get_user(self, user_id_or_login: str) -> dict[str, Any]:
        encoded = quote(user_id_or_login, safe="")
        return self.get_json(f"/api/v1/users/{encoded}")

    def list_user_factors(self, user_id: str) -> list[dict[str, Any]]:
        return self.paginate(f"/api/v1/users/{quote(user_id, safe='')}/factors", params={"limit": self.page_limit})

    def get_group_by_id(self, group_id: str) -> dict[str, Any]:
        return self.get_json(f"/api/v1/groups/{quote(group_id, safe='')}")

    def find_group_by_name(self, name: str) -> dict[str, Any] | None:
        groups = self.paginate("/api/v1/groups", params={"q": name, "limit": self.page_limit})
        for group in groups:
            if (group.get("profile") or {}).get("name") == name:
                return group
        return None

    def list_group_users(self, group_id: str) -> list[dict[str, Any]]:
        return self.paginate(f"/api/v1/groups/{quote(group_id, safe='')}/users", params={"limit": self.page_limit})
