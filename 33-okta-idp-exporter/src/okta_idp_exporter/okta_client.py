from __future__ import annotations

import time
from typing import Any
from urllib.parse import urljoin

import requests


class OktaApiError(RuntimeError):
    def __init__(self, message: str, status_code: int | None = None, payload: Any | None = None):
        super().__init__(message)
        self.status_code = status_code
        self.payload = payload


class OktaClient:
    def __init__(self, org_url: str, api_token: str, timeout: int = 60, max_retries: int = 3) -> None:
        self.org_url = org_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Authorization": f"SSWS {api_token}",
                "Accept": "application/json",
                "Content-Type": "application/json",
            }
        )

    def _build_url(self, path_or_url: str) -> str:
        if path_or_url.startswith("https://"):
            return path_or_url
        path = path_or_url if path_or_url.startswith("/") else f"/{path_or_url}"
        return urljoin(f"{self.org_url}/", path.lstrip("/"))

    @staticmethod
    def _next_link(response: requests.Response) -> str | None:
        link_header = response.headers.get("Link", "")
        for part in link_header.split(","):
            if 'rel="next"' in part:
                start = part.find("<")
                end = part.find(">")
                if start != -1 and end != -1 and end > start:
                    return part[start + 1 : end]
        return None

    def get(self, path_or_url: str, params: dict[str, Any] | None = None) -> Any:
        url = self._build_url(path_or_url)
        for attempt in range(1, self.max_retries + 1):
            response = self.session.get(url, params=params, timeout=self.timeout)

            if response.status_code == 429 or response.status_code >= 500:
                if attempt < self.max_retries:
                    retry_after = response.headers.get("X-Rate-Limit-Reset") or response.headers.get("Retry-After")
                    sleep_seconds = 2 ** attempt
                    if retry_after and retry_after.isdigit():
                        reset_or_delay = int(retry_after)
                        now = int(time.time())
                        sleep_seconds = reset_or_delay - now if reset_or_delay > now else reset_or_delay
                        sleep_seconds = max(1, min(sleep_seconds, 60))
                    time.sleep(sleep_seconds)
                    continue

            if not response.ok:
                try:
                    payload = response.json()
                except ValueError:
                    payload = response.text
                raise OktaApiError(
                    f"Okta API request failed: GET {url} returned {response.status_code}",
                    status_code=response.status_code,
                    payload=payload,
                )

            if response.status_code == 204 or not response.content:
                return None
            return response.json()

        raise OktaApiError(f"Okta API request failed after retries: GET {url}")

    def get_paginated(self, path: str, params: dict[str, Any] | None = None) -> list[Any]:
        url = self._build_url(path)
        query = params or {}
        items: list[Any] = []

        while url:
            response = self.session.get(url, params=query, timeout=self.timeout)
            query = None

            if response.status_code == 429:
                retry_after = response.headers.get("X-Rate-Limit-Reset") or response.headers.get("Retry-After")
                sleep_seconds = 5
                if retry_after and retry_after.isdigit():
                    reset_or_delay = int(retry_after)
                    now = int(time.time())
                    sleep_seconds = reset_or_delay - now if reset_or_delay > now else reset_or_delay
                    sleep_seconds = max(1, min(sleep_seconds, 60))
                time.sleep(sleep_seconds)
                continue

            if not response.ok:
                try:
                    payload = response.json()
                except ValueError:
                    payload = response.text
                raise OktaApiError(
                    f"Okta API request failed: GET {url} returned {response.status_code}",
                    status_code=response.status_code,
                    payload=payload,
                )

            page = response.json()
            if isinstance(page, list):
                items.extend(page)
            else:
                items.append(page)

            url = self._next_link(response)

        return items

    def list_identity_providers(self) -> list[dict[str, Any]]:
        return self.get_paginated("/api/v1/idps", params={"limit": 200})

    def list_identity_provider_keys(self) -> list[dict[str, Any]]:
        return self.get_paginated("/api/v1/idps/credentials/keys", params={"limit": 200})
