from __future__ import annotations

import time
from typing import Any
from urllib.parse import quote

import requests


class OktaApiError(RuntimeError):
    def __init__(self, message: str, status_code: int | None = None, payload: Any = None):
        super().__init__(message)
        self.status_code = status_code
        self.payload = payload


class OktaClient:
    def __init__(self, org_url: str, api_token: str, timeout: int = 30, max_retries: int = 3, rate_limit_sleep: int = 5):
        self.org_url = org_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries
        self.rate_limit_sleep = rate_limit_sleep
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Authorization": f"SSWS {api_token}",
                "Accept": "application/json",
                "Content-Type": "application/json",
                "User-Agent": "okta-user-bulk-importer/0.1.0",
            }
        )
        self.request_log: list[dict[str, Any]] = []

    def request(self, method: str, path: str, **kwargs: Any) -> requests.Response:
        url = f"{self.org_url}{path}"
        last_response: requests.Response | None = None
        for attempt in range(self.max_retries + 1):
            response = self.session.request(method, url, timeout=self.timeout, **kwargs)
            self.request_log.append({"method": method.upper(), "url": url, "status_code": response.status_code})
            last_response = response
            if response.status_code == 429 and attempt < self.max_retries:
                reset = response.headers.get("X-Rate-Limit-Reset")
                sleep_for = self.rate_limit_sleep
                if reset and reset.isdigit():
                    sleep_for = max(int(reset) - int(time.time()), self.rate_limit_sleep)
                time.sleep(min(sleep_for, 60))
                continue
            if response.status_code >= 500 and attempt < self.max_retries:
                time.sleep(min(2 ** attempt, 10))
                continue
            return response
        assert last_response is not None
        return last_response

    def get_user_by_login(self, login_or_email: str) -> dict[str, Any] | None:
        encoded = quote(login_or_email, safe="")
        response = self.request("GET", f"/api/v1/users/{encoded}")
        if response.status_code == 404:
            return None
        if response.status_code >= 400:
            raise self._error("Failed to look up user", response)
        return response.json()

    def create_user(self, payload: dict[str, Any], activate: bool = False) -> dict[str, Any]:
        response = self.request("POST", f"/api/v1/users?activate={str(activate).lower()}", json=payload)
        if response.status_code >= 400:
            raise self._error("Failed to create user", response)
        return response.json()

    def update_user_profile(self, user_id: str, profile: dict[str, Any]) -> dict[str, Any]:
        response = self.request("POST", f"/api/v1/users/{quote(user_id, safe='')}", json={"profile": profile})
        if response.status_code >= 400:
            raise self._error("Failed to update user profile", response)
        return response.json()

    def add_user_to_group(self, group_id: str, user_id: str) -> None:
        response = self.request("PUT", f"/api/v1/groups/{quote(group_id, safe='')}/users/{quote(user_id, safe='')}")
        if response.status_code not in (200, 204):
            raise self._error("Failed to add user to group", response)

    def _error(self, prefix: str, response: requests.Response) -> OktaApiError:
        try:
            payload = response.json()
        except ValueError:
            payload = response.text
        return OktaApiError(f"{prefix}: HTTP {response.status_code}", response.status_code, payload)
