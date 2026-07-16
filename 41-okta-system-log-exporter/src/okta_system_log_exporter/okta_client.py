from __future__ import annotations

import time
from dataclasses import dataclass
from email.utils import parsedate_to_datetime
from typing import Any
from urllib.parse import urljoin

import requests


class OktaApiError(RuntimeError):
    pass


@dataclass
class OktaResponsePage:
    events: list[dict[str, Any]]
    next_url: str | None
    status_code: int
    request_url: str


class OktaClient:
    def __init__(self, org_url: str, api_token: str, timeout_seconds: int = 30) -> None:
        self.org_url = org_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Authorization": f"SSWS {api_token}",
                "Accept": "application/json",
                "Content-Type": "application/json",
                "User-Agent": "okta-system-log-exporter/1.0.0",
            }
        )

    def list_logs_page(self, params: dict[str, Any] | None = None, next_url: str | None = None) -> OktaResponsePage:
        url = next_url or urljoin(self.org_url + "/", "api/v1/logs")
        response = self._request_with_retries(url, params=None if next_url else params)
        try:
            payload = response.json()
        except ValueError as exc:
            raise OktaApiError(f"Okta returned non-JSON response for {response.url}: {response.text[:300]}") from exc
        if not isinstance(payload, list):
            raise OktaApiError(f"Expected list response from System Log API, got {type(payload).__name__}")
        return OktaResponsePage(
            events=payload,
            next_url=parse_next_link(response.headers.get("Link", "")),
            status_code=response.status_code,
            request_url=response.url,
        )

    def _request_with_retries(self, url: str, params: dict[str, Any] | None = None, max_attempts: int = 3) -> requests.Response:
        attempt = 0
        while True:
            attempt += 1
            response = self.session.get(url, params=params, timeout=self.timeout_seconds)
            if response.status_code == 429 and attempt < max_attempts:
                sleep_seconds = calculate_rate_limit_sleep(response.headers)
                time.sleep(sleep_seconds)
                continue
            if response.status_code >= 400:
                raise OktaApiError(
                    f"Okta request failed: status={response.status_code} url={response.url} body={response.text[:500]}"
                )
            return response


def parse_next_link(link_header: str) -> str | None:
    if not link_header:
        return None
    for part in link_header.split(","):
        section = part.strip()
        if 'rel="next"' not in section:
            continue
        start = section.find("<")
        end = section.find(">")
        if start != -1 and end != -1 and end > start:
            return section[start + 1 : end]
    return None


def calculate_rate_limit_sleep(headers: dict[str, str]) -> float:
    reset_value = headers.get("X-Rate-Limit-Reset") or headers.get("x-rate-limit-reset")
    if reset_value:
        try:
            reset_epoch = int(reset_value)
            return max(1.0, min(float(reset_epoch - int(time.time()) + 1), 60.0))
        except ValueError:
            pass
    retry_after = headers.get("Retry-After") or headers.get("retry-after")
    if retry_after:
        try:
            return max(1.0, min(float(retry_after), 60.0))
        except ValueError:
            try:
                dt = parsedate_to_datetime(retry_after)
                return max(1.0, min(dt.timestamp() - time.time(), 60.0))
            except Exception:
                pass
    return 5.0
