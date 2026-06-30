from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any
from urllib.parse import urljoin

import requests


class OktaApiError(RuntimeError):
    def __init__(self, method: str, url: str, status_code: int, message: str, body: Any | None = None):
        super().__init__(message)
        self.method = method
        self.url = url
        self.status_code = status_code
        self.message = message
        self.body = body

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": "OktaApiError",
            "method": self.method,
            "url": self.url,
            "statusCode": self.status_code,
            "message": self.message,
            "errorBody": self.body,
        }


@dataclass
class RequestLogEntry:
    method: str
    url: str
    status_code: int
    elapsed_seconds: float


class OktaClient:
    def __init__(
        self,
        org_url: str,
        api_token: str,
        timeout_seconds: int = 30,
        max_retries: int = 4,
        retry_base_seconds: float = 1.0,
        page_limit: int = 200,
    ):
        self.org_url = org_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries
        self.retry_base_seconds = retry_base_seconds
        self.page_limit = page_limit
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Authorization": f"SSWS {api_token}",
                "Accept": "application/json",
                "Content-Type": "application/json",
                "User-Agent": "okta-app-cloner/0.1.0",
            }
        )
        self.request_log: list[RequestLogEntry] = []

    def _url(self, path: str) -> str:
        if path.startswith("http://") or path.startswith("https://"):
            return path
        return urljoin(self.org_url + "/", path.lstrip("/"))

    def request(self, method: str, path: str, *, json_body: Any | None = None, params: dict[str, Any] | None = None) -> Any:
        url = self._url(path)
        last_error: OktaApiError | None = None
        for attempt in range(self.max_retries + 1):
            start = time.monotonic()
            response = self.session.request(method, url, json=json_body, params=params, timeout=self.timeout_seconds)
            elapsed = round(time.monotonic() - start, 3)
            self.request_log.append(RequestLogEntry(method=method.upper(), url=response.url, status_code=response.status_code, elapsed_seconds=elapsed))

            if response.status_code in (429, 500, 502, 503, 504) and attempt < self.max_retries:
                retry_after = response.headers.get("Retry-After")
                if retry_after and retry_after.isdigit():
                    sleep_for = float(retry_after)
                else:
                    sleep_for = self.retry_base_seconds * (2 ** attempt)
                time.sleep(sleep_for)
                continue

            if response.status_code >= 400:
                try:
                    body = response.json()
                    msg = body.get("errorSummary") or body.get("message") or response.text
                except Exception:
                    body = response.text
                    msg = response.text
                last_error = OktaApiError(method.upper(), response.url, response.status_code, msg, body)
                raise last_error

            if response.status_code == 204 or not response.content:
                return None
            try:
                return response.json()
            except ValueError:
                return response.text

        if last_error:
            raise last_error
        raise RuntimeError(f"Unexpected request failure for {method} {url}")

    def get(self, path: str, *, params: dict[str, Any] | None = None) -> Any:
        return self.request("GET", path, params=params)

    def post(self, path: str, *, json_body: Any | None = None, params: dict[str, Any] | None = None) -> Any:
        return self.request("POST", path, json_body=json_body, params=params)

    def put(self, path: str, *, json_body: Any | None = None) -> Any:
        return self.request("PUT", path, json_body=json_body)

    def delete(self, path: str) -> Any:
        return self.request("DELETE", path)

    def paged_get(self, path: str, *, params: dict[str, Any] | None = None) -> list[Any]:
        params = dict(params or {})
        params.setdefault("limit", self.page_limit)
        items: list[Any] = []
        next_url: str | None = self._url(path)
        first = True
        while next_url:
            response = self.session.get(next_url, params=params if first else None, timeout=self.timeout_seconds)
            elapsed = 0.0
            self.request_log.append(RequestLogEntry(method="GET", url=response.url, status_code=response.status_code, elapsed_seconds=elapsed))
            if response.status_code >= 400:
                try:
                    body = response.json()
                    msg = body.get("errorSummary") or body.get("message") or response.text
                except Exception:
                    body = response.text
                    msg = response.text
                raise OktaApiError("GET", response.url, response.status_code, msg, body)
            data = response.json()
            if isinstance(data, list):
                items.extend(data)
            else:
                items.append(data)
            next_url = None
            link = response.headers.get("Link", "")
            for part in link.split(","):
                if 'rel="next"' in part:
                    next_url = part.split(";")[0].strip().strip("<>")
                    break
            first = False
        return items

    def find_apps_by_label(self, label: str) -> list[dict[str, Any]]:
        try:
            result = self.paged_get("/api/v1/apps", params={"q": label, "limit": self.page_limit})
        except OktaApiError:
            result = self.paged_get("/api/v1/apps", params={"limit": self.page_limit})
        return [app for app in result if isinstance(app, dict) and app.get("label") == label]

    def request_summary(self) -> dict[str, Any]:
        by_status: dict[str, int] = {}
        for entry in self.request_log:
            by_status[str(entry.status_code)] = by_status.get(str(entry.status_code), 0) + 1
        return {"totalRequests": len(self.request_log), "byStatus": by_status}
