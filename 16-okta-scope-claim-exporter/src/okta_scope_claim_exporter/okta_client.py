from __future__ import annotations

import time
from typing import Any

import requests


class OktaApiError(RuntimeError):
    def __init__(self, message: str, status_code: int | None = None, response_body: Any | None = None):
        super().__init__(message)
        self.status_code = status_code
        self.response_body = response_body


class OktaClient:
    def __init__(self, org_url: str, api_token: str, timeout_seconds: int = 30, max_retries: int = 3):
        if not api_token:
            raise ValueError("Missing Okta API token")
        self.org_url = org_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Authorization": f"SSWS {api_token}",
                "Accept": "application/json",
                "Content-Type": "application/json",
                "User-Agent": "okta-scope-claim-exporter/0.1.0",
            }
        )

    def get_paginated(self, path: str, params: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        url = self._url(path)
        results: list[dict[str, Any]] = []
        next_url: str | None = url
        next_params = params or {"limit": 200}

        while next_url:
            data, headers = self._request("GET", next_url, params=next_params)
            if isinstance(data, list):
                results.extend(data)
            elif isinstance(data, dict):
                results.append(data)
            else:
                raise OktaApiError("Unexpected Okta response shape", response_body=data)
            next_url = self._next_link(headers.get("Link"))
            next_params = None

        return results

    def _request(self, method: str, url: str, params: dict[str, Any] | None = None) -> tuple[Any, dict[str, str]]:
        last_error: Exception | None = None
        for attempt in range(self.max_retries + 1):
            try:
                response = self.session.request(method, url, params=params, timeout=self.timeout_seconds)
                if response.status_code == 429 or 500 <= response.status_code <= 599:
                    if attempt < self.max_retries:
                        retry_after = response.headers.get("Retry-After")
                        sleep_seconds = int(retry_after) if retry_after and retry_after.isdigit() else min(2**attempt, 8)
                        time.sleep(sleep_seconds)
                        continue
                if response.status_code >= 400:
                    body: Any
                    try:
                        body = response.json()
                    except Exception:
                        body = response.text
                    raise OktaApiError(
                        f"Okta API request failed: {response.status_code} {response.reason}",
                        status_code=response.status_code,
                        response_body=body,
                    )
                if not response.text:
                    return None, dict(response.headers)
                try:
                    return response.json(), dict(response.headers)
                except Exception as exc:  # pragma: no cover
                    raise OktaApiError("Okta API returned non-JSON response", response_body=response.text) from exc
            except (requests.Timeout, requests.ConnectionError) as exc:
                last_error = exc
                if attempt < self.max_retries:
                    time.sleep(min(2**attempt, 8))
                    continue
                raise OktaApiError(f"Okta API request failed after retries: {exc}") from exc
        raise OktaApiError(f"Okta API request failed: {last_error}")

    def _url(self, path: str) -> str:
        if path.startswith("http://") or path.startswith("https://"):
            return path
        return f"{self.org_url}{path}"

    @staticmethod
    def _next_link(link_header: str | None) -> str | None:
        if not link_header:
            return None
        for part in link_header.split(","):
            section = part.strip()
            if 'rel="next"' in section:
                start = section.find("<")
                end = section.find(">")
                if start != -1 and end != -1 and end > start:
                    return section[start + 1 : end]
        return None
