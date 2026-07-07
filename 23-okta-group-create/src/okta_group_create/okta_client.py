from __future__ import annotations

import time
from typing import Any
from urllib.parse import quote

import requests


class OktaApiError(RuntimeError):
    def __init__(self, message: str, status_code: int | None = None, response: Any = None):
        super().__init__(message)
        self.status_code = status_code
        self.response = response


class OktaClient:
    def __init__(self, org_url: str, api_token: str, timeout: int = 30, max_retries: int = 3, backoff_seconds: int = 2):
        self.org_url = org_url.rstrip("/")
        self.api_token = api_token
        self.timeout = timeout
        self.max_retries = max_retries
        self.backoff_seconds = backoff_seconds
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"SSWS {api_token}",
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "okta-group-create/0.1.0",
        })

    def find_group_by_name(self, name: str) -> dict[str, Any] | None:
        # Okta group search uses an expression. Escape double quotes for safety.
        escaped = name.replace('"', '\\"')
        params = {"search": f'profile.name eq "{escaped}"'}
        data = self._request("GET", "/api/v1/groups", params=params)
        if isinstance(data, list):
            for group in data:
                if (group.get("profile") or {}).get("name", "").strip().lower() == name.strip().lower():
                    return group
        return None

    def create_group(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._request("POST", "/api/v1/groups", json=payload)

    def delete_group(self, group_id: str) -> None:
        self._request("DELETE", f"/api/v1/groups/{quote(group_id)}", expect_json=False)

    def _request(self, method: str, path: str, expect_json: bool = True, **kwargs: Any) -> Any:
        url = f"{self.org_url}{path}"
        last_response = None
        for attempt in range(self.max_retries + 1):
            response = self.session.request(method, url, timeout=self.timeout, **kwargs)
            last_response = response
            if response.status_code == 429 or 500 <= response.status_code <= 599:
                if attempt < self.max_retries:
                    retry_after = response.headers.get("Retry-After")
                    delay = int(retry_after) if retry_after and retry_after.isdigit() else self.backoff_seconds * (attempt + 1)
                    time.sleep(delay)
                    continue
            if 200 <= response.status_code < 300:
                if not expect_json or not response.text.strip():
                    return None
                return response.json()
            try:
                body = response.json()
            except Exception:
                body = response.text
            raise OktaApiError(f"Okta API request failed: {response.status_code} {response.reason}", response.status_code, body)
        raise OktaApiError("Okta API request failed after retries.", getattr(last_response, "status_code", None), None)
