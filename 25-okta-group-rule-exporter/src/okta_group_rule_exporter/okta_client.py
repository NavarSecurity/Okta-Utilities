from __future__ import annotations

import time
from typing import Any
from urllib.parse import urlencode

import requests


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
            "User-Agent": "okta-group-rule-exporter/0.1.0",
        })
        self.request_log: list[dict[str, Any]] = []

    def _request(self, method: str, url: str, **kwargs: Any) -> requests.Response:
        last_error: Exception | None = None
        for attempt in range(self.max_retries + 1):
            try:
                response = self.session.request(method, url, timeout=self.timeout, **kwargs)
                self.request_log.append({
                    "method": method,
                    "url": url,
                    "status_code": response.status_code,
                    "attempt": attempt + 1,
                })
                if response.status_code in {429, 500, 502, 503, 504} and attempt < self.max_retries:
                    retry_after = response.headers.get("Retry-After")
                    wait = int(retry_after) if retry_after and retry_after.isdigit() else min(2 ** attempt, 10)
                    time.sleep(wait)
                    continue
                response.raise_for_status()
                return response
            except requests.RequestException as exc:
                last_error = exc
                if attempt < self.max_retries:
                    time.sleep(min(2 ** attempt, 10))
                    continue
                raise
        raise RuntimeError(f"Request failed: {last_error}")

    def list_group_rules(self, limit: int = 200, expand_group_names: bool = True) -> tuple[list[dict[str, Any]], list[list[dict[str, Any]]]]:
        params = {"limit": str(limit)}
        if expand_group_names:
            params["expand"] = "groupIdToGroupName"
        url = f"{self.org_url}/api/v1/groups/rules?{urlencode(params)}"
        rules: list[dict[str, Any]] = []
        raw_pages: list[list[dict[str, Any]]] = []

        while url:
            response = self._request("GET", url)
            page = response.json()
            if not isinstance(page, list):
                raise ValueError("Expected Okta group rules response to be a list.")
            raw_pages.append(page)
            rules.extend(page)
            url = _next_link(response.headers.get("Link", ""))

        return rules, raw_pages


def _next_link(link_header: str) -> str | None:
    if not link_header:
        return None
    for part in link_header.split(","):
        section = part.strip()
        if 'rel="next"' not in section:
            continue
        if section.startswith("<") and ">" in section:
            return section[1:section.index(">")]
    return None
