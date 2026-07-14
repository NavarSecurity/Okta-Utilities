from __future__ import annotations

import time
from urllib.parse import urljoin

import requests


class OktaApiError(RuntimeError):
    def __init__(self, message: str, status_code: int | None = None, response_body: str | None = None):
        super().__init__(message)
        self.status_code = status_code
        self.response_body = response_body


class OktaClient:
    def __init__(self, org_url: str, api_token: str, timeout_seconds: int = 30, max_retries: int = 3):
        self.org_url = org_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Authorization": f"SSWS {api_token}",
                "Accept": "application/json",
                "Content-Type": "application/json",
                "User-Agent": "okta-profile-schema-exporter/1.0.0",
            }
        )

    def _url(self, path_or_url: str) -> str:
        if path_or_url.startswith("https://") or path_or_url.startswith("http://"):
            return path_or_url
        return urljoin(f"{self.org_url}/", path_or_url.lstrip("/"))

    def request(self, method: str, path_or_url: str, **kwargs):
        url = self._url(path_or_url)
        attempts = self.max_retries + 1
        last_error: Exception | None = None

        for attempt in range(1, attempts + 1):
            try:
                response = self.session.request(method, url, timeout=self.timeout_seconds, **kwargs)
                if response.status_code == 429 or 500 <= response.status_code < 600:
                    if attempt < attempts:
                        retry_after = response.headers.get("Retry-After")
                        sleep_seconds = int(retry_after) if retry_after and retry_after.isdigit() else min(2 ** attempt, 10)
                        time.sleep(sleep_seconds)
                        continue
                if response.status_code >= 400:
                    body = response.text[:2000]
                    raise OktaApiError(
                        f"Okta API request failed: {method} {url} returned {response.status_code}",
                        status_code=response.status_code,
                        response_body=body,
                    )
                if response.status_code == 204 or not response.text:
                    return None, response
                return response.json(), response
            except (requests.RequestException, ValueError) as exc:
                last_error = exc
                if attempt < attempts:
                    time.sleep(min(2 ** attempt, 10))
                    continue
                raise OktaApiError(f"Okta API request failed: {method} {url}: {exc}") from exc

        raise OktaApiError(f"Okta API request failed after retries: {last_error}")

    def get_json(self, path_or_url: str, params: dict | None = None):
        data, _response = self.request("GET", path_or_url, params=params)
        return data

    @staticmethod
    def _next_link(response: requests.Response) -> str | None:
        link = response.headers.get("Link", "")
        if not link:
            return None
        for part in link.split(","):
            section = part.strip()
            if 'rel="next"' in section or "rel=next" in section:
                start = section.find("<")
                end = section.find(">")
                if start != -1 and end != -1 and end > start:
                    return section[start + 1 : end]
        return None

    def get_paginated(self, path_or_url: str, params: dict | None = None) -> list[dict]:
        results: list[dict] = []
        next_url: str | None = self._url(path_or_url)
        first = True
        while next_url:
            data, response = self.request("GET", next_url, params=params if first else None)
            first = False
            if isinstance(data, list):
                results.extend(data)
            elif data is not None:
                raise OktaApiError(f"Expected paginated list response from {next_url}")
            next_url = self._next_link(response)
        return results

    def get_user_schema(self, schema_id: str):
        return self.get_json(f"/api/v1/meta/schemas/user/{schema_id}")

    def get_group_schema(self):
        return self.get_json("/api/v1/meta/schemas/group/default")

    def list_apps(self, include_inactive: bool = False) -> list[dict]:
        params = {"limit": 200}
        apps = self.get_paginated("/api/v1/apps", params=params)
        if include_inactive:
            return apps
        return [app for app in apps if str(app.get("status", "")).upper() == "ACTIVE"]

    def get_app_user_schema(self, app_id: str):
        return self.get_json(f"/api/v1/meta/schemas/apps/{app_id}/default")
