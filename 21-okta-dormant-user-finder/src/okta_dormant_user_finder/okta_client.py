from __future__ import annotations

import time
from typing import Any
from urllib.parse import urljoin

import requests


class OktaClientError(RuntimeError):
    pass


class OktaClient:
    def __init__(self, org_url: str, api_token: str, timeout: int = 30, max_retries: int = 3):
        self.org_url = org_url.rstrip("/")
        self.api_token = api_token
        self.timeout = timeout
        self.max_retries = max_retries
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"SSWS {api_token}",
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "okta-dormant-user-finder/0.1.0",
        })

    def _request(self, method: str, path_or_url: str, **kwargs: Any) -> requests.Response:
        url = path_or_url if path_or_url.startswith("http") else urljoin(self.org_url + "/", path_or_url.lstrip("/"))
        for attempt in range(self.max_retries + 1):
            response = self.session.request(method, url, timeout=self.timeout, **kwargs)
            if response.status_code == 429 and attempt < self.max_retries:
                retry_after = response.headers.get("X-Rate-Limit-Reset")
                sleep_seconds = 2 ** attempt
                if retry_after and retry_after.isdigit():
                    sleep_seconds = max(1, int(retry_after) - int(time.time()))
                time.sleep(min(sleep_seconds, 30))
                continue
            if 500 <= response.status_code < 600 and attempt < self.max_retries:
                time.sleep(min(2 ** attempt, 10))
                continue
            return response
        return response

    def get_paginated(self, path: str, params: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []
        next_url: str | None = path
        next_params = params or {}
        while next_url:
            response = self._request("GET", next_url, params=next_params)
            if response.status_code >= 400:
                raise OktaClientError(f"GET {next_url} failed with {response.status_code}: {response.text[:500]}")
            data = response.json()
            if isinstance(data, list):
                results.extend(data)
            else:
                results.append(data)
            next_url = None
            link_header = response.headers.get("Link", "")
            for part in link_header.split(","):
                if 'rel="next"' in part:
                    start = part.find("<")
                    end = part.find(">")
                    if start >= 0 and end > start:
                        next_url = part[start + 1:end]
                        next_params = {}
                        break
        return results

    def list_users(self, statuses: list[str], limit: int = 200) -> list[dict[str, Any]]:
        # Okta list users doesn't support status array directly, so fetch status filters one by one.
        all_users: dict[str, dict[str, Any]] = {}
        if not statuses:
            users = self.get_paginated("/api/v1/users", params={"limit": limit})
            return users
        for status in statuses:
            users = self.get_paginated("/api/v1/users", params={"limit": limit, "filter": f'status eq "{status}"'})
            for user in users:
                user_id = user.get("id") or user.get("profile", {}).get("login")
                all_users[str(user_id)] = user
        return list(all_users.values())

    def list_user_app_links(self, user_id: str) -> list[dict[str, Any]]:
        return self.get_paginated(f"/api/v1/users/{user_id}/appLinks")

    def list_user_groups(self, user_id: str) -> list[dict[str, Any]]:
        return self.get_paginated(f"/api/v1/users/{user_id}/groups")
