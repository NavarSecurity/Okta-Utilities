from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import requests


class OktaApiError(RuntimeError):
    def __init__(self, method: str, url: str, status_code: int, response_body: Any):
        super().__init__(f"Okta API error {status_code} for {method} {url}: {response_body}")
        self.method = method
        self.url = url
        self.status_code = status_code
        self.response_body = response_body


@dataclass
class RequestRecord:
    method: str
    url: str
    status_code: int


class OktaClient:
    def __init__(self, org_url: str, token: str, timeout: int = 30, max_retries: int = 3) -> None:
        self.org_url = org_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Authorization": f"SSWS {token}",
                "Accept": "application/json",
                "Content-Type": "application/json",
            }
        )
        self.request_records: List[RequestRecord] = []

    def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        if path.startswith("http"):
            url = path
        else:
            url = f"{self.org_url}{path}"
        last_exc: Optional[Exception] = None
        for attempt in range(self.max_retries + 1):
            try:
                response = self.session.request(method, url, timeout=self.timeout, **kwargs)
                self.request_records.append(RequestRecord(method=method, url=url, status_code=response.status_code))
                if response.status_code == 429 or 500 <= response.status_code <= 599:
                    if attempt < self.max_retries:
                        retry_after = response.headers.get("Retry-After")
                        sleep_for = int(retry_after) if retry_after and retry_after.isdigit() else min(2 ** attempt, 8)
                        time.sleep(sleep_for)
                        continue
                if response.status_code >= 400:
                    try:
                        body = response.json()
                    except ValueError:
                        body = response.text
                    raise OktaApiError(method, url, response.status_code, body)
                if response.status_code == 204 or not response.text:
                    return None
                try:
                    return response.json()
                except ValueError:
                    return response.text
            except requests.RequestException as exc:
                last_exc = exc
                if attempt < self.max_retries:
                    time.sleep(min(2 ** attempt, 8))
                    continue
                raise RuntimeError(f"Request failed for {method} {url}: {exc}") from exc
        if last_exc:
            raise RuntimeError(f"Request failed for {method} {url}: {last_exc}") from last_exc
        raise RuntimeError(f"Request failed for {method} {url}")

    def get_paginated(self, path: str) -> List[Dict[str, Any]]:
        url_or_path: str = path
        items: List[Dict[str, Any]] = []
        while url_or_path:
            if path.startswith("http") or url_or_path.startswith("http"):
                url = url_or_path
            else:
                url = url_or_path
            response = self.session.get(
                url if url.startswith("http") else f"{self.org_url}{url}",
                timeout=self.timeout,
            )
            self.request_records.append(RequestRecord(method="GET", url=response.url, status_code=response.status_code))
            if response.status_code >= 400:
                try:
                    body = response.json()
                except ValueError:
                    body = response.text
                raise OktaApiError("GET", response.url, response.status_code, body)
            body = response.json() if response.text else []
            if isinstance(body, list):
                items.extend(body)
            else:
                items.append(body)

            next_url = None
            link_header = response.headers.get("Link", "")
            for part in link_header.split(","):
                if 'rel="next"' in part:
                    start = part.find("<") + 1
                    end = part.find(">")
                    if start > 0 and end > start:
                        next_url = part[start:end]
                        break
            url_or_path = next_url or ""
        return items

    def post(self, path: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        result = self._request("POST", path, json=payload)
        return result or {}

    def get_authorization_servers(self) -> List[Dict[str, Any]]:
        return self.get_paginated("/api/v1/authorizationServers")

    def get_scopes(self, auth_server_id: str) -> List[Dict[str, Any]]:
        return self.get_paginated(f"/api/v1/authorizationServers/{auth_server_id}/scopes")

    def get_claims(self, auth_server_id: str) -> List[Dict[str, Any]]:
        return self.get_paginated(f"/api/v1/authorizationServers/{auth_server_id}/claims")

    def get_policies(self, auth_server_id: str) -> List[Dict[str, Any]]:
        return self.get_paginated(f"/api/v1/authorizationServers/{auth_server_id}/policies")

    def get_policy_rules(self, auth_server_id: str, policy_id: str) -> List[Dict[str, Any]]:
        return self.get_paginated(f"/api/v1/authorizationServers/{auth_server_id}/policies/{policy_id}/rules")
