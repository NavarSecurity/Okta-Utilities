from __future__ import annotations

import time
from urllib.parse import urljoin

import requests


class OktaApiError(RuntimeError):
    pass


class OktaClient:
    def __init__(self, org_url: str, api_token: str, timeout: int = 30, max_retries: int = 3):
        self.org_url = org_url.rstrip("/")
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"SSWS {api_token}",
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "okta-group-cleanup-analyzer/0.1.3",
        })
        self.timeout = timeout
        self.max_retries = max_retries
        self.request_count = 0

    def get(self, path_or_url: str, params: dict | None = None) -> requests.Response:
        url = path_or_url if path_or_url.startswith("http") else self.org_url + path_or_url
        for attempt in range(self.max_retries + 1):
            self.request_count += 1
            resp = self.session.get(url, params=params, timeout=self.timeout)
            if resp.status_code == 429 and attempt < self.max_retries:
                wait = int(resp.headers.get("X-Rate-Limit-Reset", "0") or "0") - int(time.time())
                time.sleep(max(1, min(wait, 5)))
                continue
            if 200 <= resp.status_code < 300:
                return resp
            if resp.status_code >= 500 and attempt < self.max_retries:
                time.sleep(1 + attempt)
                continue
            raise OktaApiError(f"GET {url} failed: {resp.status_code} {resp.text[:500]}")
        raise OktaApiError(f"GET {url} failed after retries")

    def paged_get(self, path: str, params: dict | None = None) -> list[dict]:
        results: list[dict] = []
        next_url: str | None = self.org_url + path
        query = dict(params or {})
        while next_url:
            resp = self.get(next_url, params=query)
            query = None
            payload = resp.json()
            if isinstance(payload, list):
                results.extend([item for item in payload if isinstance(item, dict)])
            next_url = parse_next_link(resp.headers.get("Link", ""))
        return results

    def list_groups(self) -> list[dict]:
        return self.paged_get("/api/v1/groups", params={"limit": "200"})

    def count_group_members(self, group_id: str) -> int:
        members = self.paged_get(f"/api/v1/groups/{group_id}/users", params={"limit": "200"})
        return len(members)

    def list_apps(self) -> list[dict]:
        return self.paged_get("/api/v1/apps", params={"limit": "200"})

    def list_app_group_assignments(self, app_id: str) -> list[dict]:
        return self.paged_get(f"/api/v1/apps/{app_id}/groups", params={"limit": "200"})

    def list_group_rules(self) -> list[dict]:
        return self.paged_get("/api/v1/groups/rules", params={"limit": "200"})


def parse_next_link(link_header: str) -> str | None:
    if not link_header:
        return None
    for part in link_header.split(","):
        section = part.strip()
        if 'rel="next"' in section:
            start = section.find("<")
            end = section.find(">")
            if start >= 0 and end > start:
                return section[start + 1:end]
    return None
