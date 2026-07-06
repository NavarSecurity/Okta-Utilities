from __future__ import annotations

import time
from typing import Any, Dict, Iterable, List, Optional

import requests


class OktaApiError(RuntimeError):
    def __init__(self, message: str, status_code: Optional[int] = None, payload: Any = None):
        super().__init__(message)
        self.status_code = status_code
        self.payload = payload


class OktaClient:
    def __init__(self, org_url: str, api_token: str, timeout: int = 30, max_retries: int = 3):
        self.org_url = org_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Authorization": f"SSWS {api_token}",
                "Accept": "application/json",
                "Content-Type": "application/json",
                "User-Agent": "okta-user-exporter/0.1.0",
            }
        )
        self.request_count = 0
        self.status_counts: Dict[str, int] = {}

    def _url(self, path: str) -> str:
        if path.startswith("http"):
            return path
        return f"{self.org_url}{path}"

    def get(self, path: str, params: Optional[Dict[str, Any]] = None) -> requests.Response:
        url = self._url(path)
        last_error = None
        for attempt in range(self.max_retries + 1):
            self.request_count += 1
            response = self.session.get(url, params=params if attempt == 0 else None, timeout=self.timeout)
            self.status_counts[str(response.status_code)] = self.status_counts.get(str(response.status_code), 0) + 1
            if response.status_code == 429:
                wait = int(response.headers.get("X-Rate-Limit-Reset", "0") or "0") - int(time.time())
                wait = max(1, min(wait, 15))
                time.sleep(wait)
                last_error = response
                continue
            if response.status_code >= 500 and attempt < self.max_retries:
                time.sleep(min(2 ** attempt, 8))
                last_error = response
                continue
            if not response.ok:
                try:
                    payload = response.json()
                except ValueError:
                    payload = response.text
                raise OktaApiError(f"Okta API request failed: {response.status_code} {response.reason}", response.status_code, payload)
            return response
        assert last_error is not None
        raise OktaApiError(f"Okta API request failed after retries: {last_error.status_code}", last_error.status_code, last_error.text)

    def paginate(self, path: str, params: Optional[Dict[str, Any]] = None, max_items: Optional[int] = None) -> Iterable[Dict[str, Any]]:
        next_url: Optional[str] = path
        request_params = dict(params or {})
        returned = 0
        while next_url:
            response = self.get(next_url, params=request_params)
            request_params = None
            try:
                items = response.json()
            except ValueError as exc:
                raise OktaApiError("Okta API returned non-JSON response", response.status_code, response.text) from exc
            if isinstance(items, dict):
                items = [items]
            for item in items:
                yield item
                returned += 1
                if max_items is not None and returned >= max_items:
                    return
            next_url = _parse_next_link(response.headers.get("Link", ""))

    def list_users(self, params: Dict[str, Any], max_users: Optional[int] = None) -> List[Dict[str, Any]]:
        return list(self.paginate("/api/v1/users", params=params, max_items=max_users))

    def get_user(self, user_id: str) -> Dict[str, Any]:
        return self.get(f"/api/v1/users/{user_id}").json()

    def get_user_groups(self, user_id: str) -> List[Dict[str, Any]]:
        return list(self.paginate(f"/api/v1/users/{user_id}/groups", params={"limit": 200}))

    def get_user_app_links(self, user_id: str) -> List[Dict[str, Any]]:
        return list(self.paginate(f"/api/v1/users/{user_id}/appLinks", params={"limit": 200}))


def _parse_next_link(link_header: str) -> Optional[str]:
    if not link_header:
        return None
    for part in link_header.split(","):
        section = part.strip()
        if 'rel="next"' in section or "rel=next" in section:
            start = section.find("<")
            end = section.find(">")
            if start != -1 and end != -1 and end > start:
                return section[start + 1 : end]
    return None
