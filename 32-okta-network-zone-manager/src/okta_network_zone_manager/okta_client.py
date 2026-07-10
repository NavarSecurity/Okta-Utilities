from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urljoin, urlparse, parse_qs
from urllib.request import Request, urlopen

from .config import normalize_org_url, resolve_env_value


class OktaApiError(RuntimeError):
    def __init__(self, status: int, method: str, url: str, body: str):
        self.status = status
        self.method = method
        self.url = url
        self.body = body
        super().__init__(f"Okta API error {status} for {method} {url}: {body[:500]}")


@dataclass
class OktaClient:
    org_url: str
    api_token: str
    timeout_seconds: int = 30
    max_retries: int = 4
    retry_backoff_seconds: int = 2

    @classmethod
    def from_config(cls, config: dict[str, Any]) -> "OktaClient":
        org_url = normalize_org_url(resolve_env_value(config, "orgUrlEnv", "OKTA_ORG_URL"))
        api_token = resolve_env_value(config, "apiTokenEnv", "OKTA_API_TOKEN")
        request_cfg = config.get("request", {})
        return cls(
            org_url=org_url,
            api_token=api_token,
            timeout_seconds=int(request_cfg.get("timeoutSeconds", 30)),
            max_retries=int(request_cfg.get("maxRetries", 4)),
            retry_backoff_seconds=int(request_cfg.get("retryBackoffSeconds", 2)),
        )

    def _headers(self, body: Any | None = None) -> dict[str, str]:
        headers = {
            "Authorization": f"SSWS {self.api_token}",
            "Accept": "application/json",
            "User-Agent": "okta-network-zone-manager/1.0",
        }
        if body is not None:
            headers["Content-Type"] = "application/json"
        return headers

    def _url(self, path_or_url: str, params: dict[str, Any] | None = None) -> str:
        if path_or_url.startswith("http://") or path_or_url.startswith("https://"):
            base_url = path_or_url
        else:
            base_url = urljoin(self.org_url + "/", path_or_url.lstrip("/"))
        if params:
            query = urlencode({k: v for k, v in params.items() if v is not None})
            joiner = "&" if "?" in base_url else "?"
            return f"{base_url}{joiner}{query}"
        return base_url

    def request(self, method: str, path_or_url: str, body: Any | None = None, params: dict[str, Any] | None = None) -> tuple[Any, dict[str, str]]:
        data = None if body is None else json.dumps(body).encode("utf-8")
        url = self._url(path_or_url, params)
        method = method.upper()

        last_error: Exception | None = None
        for attempt in range(self.max_retries + 1):
            req = Request(url=url, data=data, headers=self._headers(body), method=method)
            try:
                with urlopen(req, timeout=self.timeout_seconds) as response:
                    raw = response.read().decode("utf-8")
                    headers = {k.lower(): v for k, v in response.headers.items()}
                    if not raw:
                        return None, headers
                    return json.loads(raw), headers
            except HTTPError as exc:
                raw = exc.read().decode("utf-8", errors="replace")
                headers = {k.lower(): v for k, v in exc.headers.items()}
                if exc.code == 429 and attempt < self.max_retries:
                    retry_after = headers.get("retry-after")
                    sleep_for = int(retry_after) if retry_after and retry_after.isdigit() else self.retry_backoff_seconds * (attempt + 1)
                    time.sleep(sleep_for)
                    continue
                if 500 <= exc.code <= 599 and attempt < self.max_retries:
                    time.sleep(self.retry_backoff_seconds * (attempt + 1))
                    continue
                raise OktaApiError(exc.code, method, url, raw) from exc
            except URLError as exc:
                last_error = exc
                if attempt < self.max_retries:
                    time.sleep(self.retry_backoff_seconds * (attempt + 1))
                    continue
                raise RuntimeError(f"Unable to reach Okta API: {exc}") from exc

        raise RuntimeError(f"Okta API request failed after retries: {last_error}")

    def get(self, path_or_url: str, params: dict[str, Any] | None = None) -> tuple[Any, dict[str, str]]:
        return self.request("GET", path_or_url, params=params)

    def post(self, path_or_url: str, body: Any | None = None) -> tuple[Any, dict[str, str]]:
        return self.request("POST", path_or_url, body=body)

    def put(self, path_or_url: str, body: Any) -> tuple[Any, dict[str, str]]:
        return self.request("PUT", path_or_url, body=body)

    def delete(self, path_or_url: str) -> tuple[Any, dict[str, str]]:
        return self.request("DELETE", path_or_url)

    def paged_get(self, path: str, params: dict[str, Any] | None = None) -> list[Any]:
        items: list[Any] = []
        next_url: str | None = None
        first = True
        while first or next_url:
            first = False
            if next_url:
                page, headers = self.get(next_url)
            else:
                page, headers = self.get(path, params=params)
            if isinstance(page, list):
                items.extend(page)
            else:
                raise ValueError(f"Expected list response from {path}")
            next_url = parse_next_link(headers.get("link", ""))
        return items


def parse_next_link(link_header: str) -> str | None:
    if not link_header:
        return None
    parts = [p.strip() for p in link_header.split(",")]
    for part in parts:
        if 'rel="next"' not in part and "rel=next" not in part:
            continue
        if part.startswith("<") and ">" in part:
            return part[1:part.index(">")]
    return None
