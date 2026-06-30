from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
import time

import requests


class OktaApiError(RuntimeError):
    def __init__(self, status_code: int, message: str, url: str, body: Any = None):
        super().__init__(message)
        self.status_code = status_code
        self.message = message
        self.url = url
        self.body = body


@dataclass
class RequestSummary:
    total_requests: int = 0
    by_status: dict[str, int] = field(default_factory=dict)
    total_elapsed_seconds: float = 0.0

    def record(self, status_code: int, elapsed: float) -> None:
        self.total_requests += 1
        self.total_elapsed_seconds += elapsed
        key = str(status_code)
        self.by_status[key] = self.by_status.get(key, 0) + 1


class OktaClient:
    def __init__(self, org_url: str, token: str, timeout_seconds: int = 30, max_retries: int = 4, retry_base_seconds: float = 1.0):
        self.org_url = org_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries
        self.retry_base_seconds = retry_base_seconds
        self.summary = RequestSummary()
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"SSWS {token}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        })

    def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        url = f"{self.org_url}{path}"
        last_exc: Exception | None = None
        for attempt in range(self.max_retries + 1):
            start = time.time()
            try:
                response = self.session.request(method, url, timeout=self.timeout_seconds, **kwargs)
                elapsed = time.time() - start
                self.summary.record(response.status_code, elapsed)
                if response.status_code == 429 or 500 <= response.status_code <= 599:
                    if attempt < self.max_retries:
                        retry_after = response.headers.get("Retry-After")
                        sleep_for = float(retry_after) if retry_after and retry_after.isdigit() else self.retry_base_seconds * (2 ** attempt)
                        time.sleep(min(sleep_for, 15))
                        continue
                if response.status_code >= 400:
                    try:
                        body = response.json()
                    except ValueError:
                        body = response.text
                    message = body.get("errorSummary") if isinstance(body, dict) else str(body)
                    raise OktaApiError(response.status_code, message or response.reason, url, body)
                if response.status_code == 204:
                    return None
                try:
                    return response.json()
                except ValueError:
                    return response.text
            except requests.RequestException as exc:
                last_exc = exc
                if attempt < self.max_retries:
                    time.sleep(min(self.retry_base_seconds * (2 ** attempt), 15))
                    continue
                raise OktaApiError(0, str(exc), url) from exc
        if last_exc:
            raise OktaApiError(0, str(last_exc), url) from last_exc
        raise OktaApiError(0, "Unknown request failure", url)

    def list_apps_by_query(self, query: str, limit: int = 200) -> list[dict[str, Any]]:
        data = self._request("GET", f"/api/v1/apps?q={requests.utils.quote(query)}&limit={limit}")
        return data if isinstance(data, list) else []

    def create_app(self, payload: dict[str, Any]) -> dict[str, Any]:
        data = self._request("POST", "/api/v1/apps", json=payload)
        if not isinstance(data, dict):
            raise OktaApiError(0, "Unexpected create app response", f"{self.org_url}/api/v1/apps", data)
        return data

    def assign_group(self, app_id: str, group_id: str) -> dict[str, Any] | None:
        data = self._request("PUT", f"/api/v1/apps/{app_id}/groups/{group_id}", json={})
        return data if isinstance(data, dict) else None

    def assign_user(self, app_id: str, user_id: str) -> dict[str, Any] | None:
        data = self._request("POST", f"/api/v1/apps/{app_id}/users", json={"id": user_id})
        return data if isinstance(data, dict) else None
