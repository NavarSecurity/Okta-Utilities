from __future__ import annotations

import time
from typing import Any
from urllib.parse import quote

import requests


class OktaApiError(RuntimeError):
    def __init__(self, message: str, status_code: int | None = None, response: dict[str, Any] | None = None):
        super().__init__(message)
        self.status_code = status_code
        self.response = response or {}


class OktaClient:
    def __init__(self, org_url: str, api_token: str, timeout: int = 30, max_retries: int = 3):
        self.org_url = org_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"SSWS {api_token}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        })

    def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        url = f"{self.org_url}{path}"
        last_error: Exception | None = None
        for attempt in range(self.max_retries + 1):
            try:
                response = self.session.request(method, url, timeout=self.timeout, **kwargs)
                if response.status_code == 429 and attempt < self.max_retries:
                    reset = response.headers.get("X-Rate-Limit-Reset")
                    sleep_seconds = 1
                    if reset and reset.isdigit():
                        sleep_seconds = max(1, int(reset) - int(time.time()))
                    time.sleep(min(sleep_seconds, 10))
                    continue
                if response.status_code >= 400:
                    try:
                        body = response.json()
                    except ValueError:
                        body = {"raw": response.text}
                    raise OktaApiError(
                        f"Okta API request failed: {response.status_code} {response.reason}",
                        status_code=response.status_code,
                        response=body,
                    )
                if response.status_code == 204 or not response.content:
                    return {}
                try:
                    return response.json()
                except ValueError:
                    return {"raw": response.text}
            except (requests.RequestException, OktaApiError) as exc:
                last_error = exc
                if isinstance(exc, OktaApiError) or attempt >= self.max_retries:
                    raise
                time.sleep(min(2 ** attempt, 8))
        raise RuntimeError(f"Request failed after retries: {last_error}")

    def get_user(self, identifier: str) -> dict[str, Any]:
        encoded = quote(identifier, safe="")
        return self._request("GET", f"/api/v1/users/{encoded}")

    def suspend_user(self, user_id: str) -> dict[str, Any]:
        encoded = quote(user_id, safe="")
        return self._request("POST", f"/api/v1/users/{encoded}/lifecycle/suspend")

    def unsuspend_user(self, user_id: str) -> dict[str, Any]:
        encoded = quote(user_id, safe="")
        return self._request("POST", f"/api/v1/users/{encoded}/lifecycle/unsuspend")

    def deactivate_user(self, user_id: str, send_email: bool = False) -> dict[str, Any]:
        encoded = quote(user_id, safe="")
        send = "true" if send_email else "false"
        return self._request("POST", f"/api/v1/users/{encoded}/lifecycle/deactivate?sendEmail={send}")

    def activate_user(self, user_id: str, send_email: bool = False) -> dict[str, Any]:
        encoded = quote(user_id, safe="")
        send = "true" if send_email else "false"
        return self._request("POST", f"/api/v1/users/{encoded}/lifecycle/activate?sendEmail={send}")

    def delete_user(self, user_id: str, send_email: bool = False) -> dict[str, Any]:
        encoded = quote(user_id, safe="")
        send = "true" if send_email else "false"
        return self._request("DELETE", f"/api/v1/users/{encoded}?sendEmail={send}")
