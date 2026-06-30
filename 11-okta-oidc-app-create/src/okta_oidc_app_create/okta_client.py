from __future__ import annotations

from dataclasses import dataclass
from typing import Any
import time

import requests


@dataclass
class OktaApiError(Exception):
    status_code: int
    message: str
    url: str
    error_body: Any = None

    def __str__(self) -> str:
        return f"OktaApiError({self.status_code}): {self.message}"


class OktaClient:
    def __init__(self, org_url: str, token: str | None, timeout: int = 30, max_retries: int = 4, retry_base: float = 1.0):
        self.org_url = org_url.rstrip("/")
        self.token = token
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_base = retry_base
        self.total_requests = 0
        self.by_status: dict[str, int] = {}

    def _headers(self) -> dict[str, str]:
        headers = {"Accept": "application/json", "Content-Type": "application/json"}
        if self.token:
            headers["Authorization"] = f"SSWS {self.token}"
        return headers

    def _request(self, method: str, path_or_url: str, **kwargs: Any) -> requests.Response:
        url = path_or_url if path_or_url.startswith("http") else f"{self.org_url}{path_or_url}"
        last_response: requests.Response | None = None
        for attempt in range(self.max_retries + 1):
            self.total_requests += 1
            response = requests.request(method, url, headers=self._headers(), timeout=self.timeout, **kwargs)
            self.by_status[str(response.status_code)] = self.by_status.get(str(response.status_code), 0) + 1
            last_response = response
            if response.status_code not in {429, 500, 502, 503, 504}:
                return response
            wait = response.headers.get("X-Rate-Limit-Reset")
            if wait and wait.isdigit():
                sleep_seconds = max(0, int(wait) - int(time.time()))
            else:
                sleep_seconds = self.retry_base * (2 ** attempt)
            time.sleep(min(sleep_seconds, 30))
        assert last_response is not None
        return last_response

    def _json_or_error(self, response: requests.Response) -> Any:
        try:
            body = response.json() if response.text else None
        except ValueError:
            body = response.text
        if response.status_code >= 400:
            message = "Okta API request failed"
            if isinstance(body, dict):
                message = body.get("errorSummary") or body.get("message") or message
            raise OktaApiError(response.status_code, message, response.url, body)
        return body

    def get_paginated(self, path: str, limit: int = 200) -> list[dict[str, Any]]:
        separator = "&" if "?" in path else "?"
        url = f"{self.org_url}{path}{separator}limit={limit}"
        results: list[dict[str, Any]] = []
        while url:
            response = self._request("GET", url)
            data = self._json_or_error(response)
            if isinstance(data, list):
                results.extend(data)
            elif isinstance(data, dict):
                results.append(data)
            url = None
            link = response.headers.get("Link", "")
            for part in link.split(","):
                if 'rel="next"' in part:
                    url = part[part.find("<") + 1 : part.find(">")]
                    break
        return results

    def find_app_by_label(self, label: str, limit: int = 200) -> dict[str, Any] | None:
        apps = self.get_paginated(f"/api/v1/apps?q={requests.utils.quote(label)}", limit=limit)
        for app in apps:
            if app.get("label") == label:
                return app
        return None

    def create_app(self, payload: dict[str, Any]) -> dict[str, Any]:
        response = self._request("POST", "/api/v1/apps", json=payload)
        return self._json_or_error(response)

    def find_group_by_name(self, name: str, limit: int = 200) -> dict[str, Any] | None:
        groups = self.get_paginated(f"/api/v1/groups?q={requests.utils.quote(name)}", limit=limit)
        for group in groups:
            if group.get("profile", {}).get("name") == name:
                return group
        return None

    def find_user_by_login(self, login: str) -> dict[str, Any] | None:
        response = self._request("GET", f"/api/v1/users/{requests.utils.quote(login, safe='')}")
        if response.status_code == 404:
            return None
        return self._json_or_error(response)

    def assign_group_to_app(self, app_id: str, group_id: str) -> dict[str, Any] | None:
        response = self._request("PUT", f"/api/v1/apps/{app_id}/groups/{group_id}", json={})
        return self._json_or_error(response)

    def assign_user_to_app(self, app_id: str, user_id: str) -> dict[str, Any] | None:
        response = self._request("POST", f"/api/v1/apps/{app_id}/users", json={"id": user_id})
        return self._json_or_error(response)

    def request_summary(self) -> dict[str, Any]:
        return {"totalRequests": self.total_requests, "byStatus": self.by_status}
