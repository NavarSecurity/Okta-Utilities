from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any
from urllib.parse import urljoin

import requests


class OktaApiError(RuntimeError):
    def __init__(self, message: str, status_code: int | None = None, body: Any | None = None):
        super().__init__(message)
        self.status_code = status_code
        self.body = body


@dataclass(frozen=True)
class OktaClient:
    org_url: str
    api_token: str
    timeout_seconds: int = 30
    max_retries: int = 3

    def __post_init__(self) -> None:
        object.__setattr__(self, "org_url", self.org_url.rstrip("/"))

    @property
    def headers(self) -> dict[str, str]:
        return {
            "Authorization": f"SSWS {self.api_token}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

    def _url(self, path: str) -> str:
        return urljoin(f"{self.org_url}/", path.lstrip("/"))

    def request(self, method: str, path: str, **kwargs: Any) -> Any:
        url = self._url(path)
        for attempt in range(1, self.max_retries + 1):
            response = requests.request(
                method=method,
                url=url,
                headers=self.headers,
                timeout=self.timeout_seconds,
                **kwargs,
            )
            if response.status_code == 429 and attempt < self.max_retries:
                retry_after = int(response.headers.get("X-Rate-Limit-Reset", "0")) - int(time.time())
                time.sleep(max(1, min(retry_after, 30)))
                continue
            if response.status_code >= 400:
                body: Any
                try:
                    body = response.json()
                except ValueError:
                    body = response.text
                raise OktaApiError(
                    f"Okta API request failed: {method} {path} returned {response.status_code}",
                    status_code=response.status_code,
                    body=body,
                )
            if response.status_code == 204:
                return None
            try:
                return response.json()
            except ValueError:
                return response.text
        raise OktaApiError(f"Okta API request failed after retries: {method} {path}")

    def get_user_schema(self, schema_id: str = "default") -> dict[str, Any]:
        return self.request("GET", f"/api/v1/meta/schemas/user/{schema_id}")

    def update_user_schema(self, schema_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        return self.request("POST", f"/api/v1/meta/schemas/user/{schema_id}", json=payload)

    def get_app_schema(self, app_id: str, schema_id: str = "default") -> dict[str, Any]:
        return self.request("GET", f"/api/v1/meta/schemas/apps/{app_id}/{schema_id}")

    def update_app_schema(self, app_id: str, schema_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        return self.request("POST", f"/api/v1/meta/schemas/apps/{app_id}/{schema_id}", json=payload)

    def find_app_by_name(self, app_name: str) -> dict[str, Any] | None:
        apps = self.request("GET", "/api/v1/apps", params={"q": app_name, "limit": 200})
        if not isinstance(apps, list):
            return None
        lowered = app_name.lower()
        for app in apps:
            if str(app.get("label", "")).lower() == lowered or str(app.get("name", "")).lower() == lowered:
                return app
        return None
