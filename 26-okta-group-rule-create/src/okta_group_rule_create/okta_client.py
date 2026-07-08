from __future__ import annotations

import time
from typing import Any
from urllib.parse import quote

import requests


class OktaApiError(RuntimeError):
    def __init__(self, message: str, status_code: int | None = None, response_body: Any = None):
        super().__init__(message)
        self.status_code = status_code
        self.response_body = response_body


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
            "User-Agent": "okta-group-rule-create/0.1.1",
        })
        self.requests_made: list[dict[str, Any]] = []

    def _url(self, path: str) -> str:
        return f"{self.org_url}{path}"

    def request(self, method: str, path: str, **kwargs) -> requests.Response:
        url = self._url(path)
        last_response: requests.Response | None = None
        for attempt in range(self.max_retries + 1):
            response = self.session.request(method, url, timeout=self.timeout, **kwargs)
            last_response = response
            self.requests_made.append({
                "method": method.upper(),
                "path": path,
                "status": response.status_code,
            })
            if response.status_code not in {429, 500, 502, 503, 504}:
                return response
            if attempt < self.max_retries:
                retry_after = response.headers.get("Retry-After")
                wait = int(retry_after) if retry_after and retry_after.isdigit() else min(2 ** attempt, 8)
                time.sleep(wait)
        assert last_response is not None
        return last_response

    def _json_or_text(self, response: requests.Response) -> Any:
        try:
            return response.json()
        except ValueError:
            return response.text

    def ensure_success(self, response: requests.Response, message: str) -> Any:
        if 200 <= response.status_code < 300:
            if response.status_code == 204:
                return None
            return self._json_or_text(response)
        raise OktaApiError(message, response.status_code, self._json_or_text(response))

    def list_group_rules(self) -> list[dict[str, Any]]:
        path = "/api/v1/groups/rules?limit=200&expand=groupIdToGroupNameMap"
        results: list[dict[str, Any]] = []
        while path:
            response = self.request("GET", path)
            data = self.ensure_success(response, "Failed to list group rules.")
            if isinstance(data, list):
                results.extend(data)
            next_url = response.links.get("next", {}).get("url")
            if next_url and next_url.startswith(self.org_url):
                path = next_url[len(self.org_url):]
            else:
                path = ""
        return results

    def find_group_rule_by_name(self, name: str) -> dict[str, Any] | None:
        lowered = name.strip().lower()
        for rule in self.list_group_rules():
            if str(rule.get("name", "")).strip().lower() == lowered:
                return rule
        return None

    def find_group_by_exact_name(self, group_name: str) -> dict[str, Any]:
        q = quote(group_name)
        response = self.request("GET", f"/api/v1/groups?q={q}&limit=200")
        data = self.ensure_success(response, f"Failed to search group {group_name!r}.")
        matches = []
        for group in data if isinstance(data, list) else []:
            profile = group.get("profile") or {}
            if str(profile.get("name", "")).strip().lower() == group_name.strip().lower():
                matches.append(group)
        if not matches:
            raise OktaApiError(f"Target group name was not found: {group_name}")
        if len(matches) > 1:
            raise OktaApiError(f"Multiple groups matched target group name: {group_name}")
        return matches[0]

    def create_group_rule(self, payload: dict) -> dict[str, Any]:
        response = self.request("POST", "/api/v1/groups/rules", json=payload)
        return self.ensure_success(response, "Failed to create group rule.")

    def activate_group_rule(self, rule_id: str) -> None:
        response = self.request("POST", f"/api/v1/groups/rules/{rule_id}/lifecycle/activate")
        self.ensure_success(response, "Failed to activate group rule.")
