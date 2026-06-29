from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urljoin

import requests

from . import __version__


class OktaApiError(RuntimeError):
    def __init__(self, status_code: int, url: str, message: str, error_body: Any | None = None):
        super().__init__(f"Okta API error {status_code} for {url}: {message}")
        self.status_code = status_code
        self.url = url
        self.message = message
        self.error_body = error_body


@dataclass(frozen=True)
class ApiRequestResult:
    url: str
    status_code: int
    elapsed_seconds: float


def parse_next_link(link_header: str | None) -> str | None:
    """Extract the rel=next URL from an RFC 5988 Link header."""
    if not link_header:
        return None
    for part in split_link_header(link_header):
        match = re.search(r"<([^>]+)>\s*;\s*rel=\"?next\"?", part, flags=re.IGNORECASE)
        if match:
            return match.group(1)
    return None


def split_link_header(link_header: str) -> list[str]:
    """Split a Link header while avoiding commas inside URLs."""
    parts: list[str] = []
    current: list[str] = []
    inside_angle = False
    for char in link_header:
        if char == "<":
            inside_angle = True
        elif char == ">":
            inside_angle = False
        if char == "," and not inside_angle:
            parts.append("".join(current).strip())
            current = []
        else:
            current.append(char)
    if current:
        parts.append("".join(current).strip())
    return parts


class OktaApiClient:
    def __init__(
        self,
        org_url: str,
        api_token: str,
        timeout_seconds: int = 30,
        max_retries: int = 4,
        retry_base_seconds: float = 1.0,
    ) -> None:
        self.org_url = org_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries
        self.retry_base_seconds = retry_base_seconds
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Authorization": f"SSWS {api_token}",
                "Accept": "application/json",
                "Content-Type": "application/json",
                "User-Agent": f"okta-config-backup/{__version__}",
            }
        )
        self.request_log: list[ApiRequestResult] = []

    def build_url(self, path_or_url: str) -> str:
        if path_or_url.startswith("https://"):
            return path_or_url
        return urljoin(self.org_url + "/", path_or_url.lstrip("/"))

    def get(self, path_or_url: str, params: dict[str, Any] | None = None) -> requests.Response:
        url = self.build_url(path_or_url)
        attempt = 0
        while True:
            started = time.monotonic()
            response = self.session.get(url, params=params, timeout=self.timeout_seconds)
            elapsed = time.monotonic() - started
            self.request_log.append(ApiRequestResult(url=response.url, status_code=response.status_code, elapsed_seconds=elapsed))

            if response.status_code not in {429, 500, 502, 503, 504}:
                break

            if attempt >= self.max_retries:
                break

            sleep_seconds = self._retry_delay(response, attempt)
            time.sleep(sleep_seconds)
            attempt += 1

        if response.status_code >= 400:
            body = safe_json(response)
            message = extract_error_message(body) or response.text[:500]
            raise OktaApiError(response.status_code, response.url, message, body)

        return response

    def get_json(self, path_or_url: str, params: dict[str, Any] | None = None) -> Any:
        response = self.get(path_or_url, params=params)
        if not response.text.strip():
            return None
        return response.json()

    def get_paginated(self, path: str, params: dict[str, Any] | None = None) -> list[Any]:
        results: list[Any] = []
        next_url: str | None = path
        first_request = True

        while next_url:
            response = self.get(next_url, params=params if first_request else None)
            first_request = False
            body = safe_json(response)

            if isinstance(body, list):
                results.extend(body)
            elif isinstance(body, dict) and isinstance(body.get("items"), list):
                results.extend(body["items"])
            elif body is not None:
                results.append(body)

            next_url = parse_next_link(response.headers.get("Link"))

        return results

    def _retry_delay(self, response: requests.Response, attempt: int) -> float:
        retry_after = response.headers.get("Retry-After")
        if retry_after:
            try:
                return max(float(retry_after), 0.0)
            except ValueError:
                pass

        reset = response.headers.get("X-Rate-Limit-Reset") or response.headers.get("x-rate-limit-reset")
        if reset:
            try:
                reset_at = datetime.fromtimestamp(float(reset), tz=timezone.utc)
                now = datetime.now(tz=timezone.utc)
                return max((reset_at - now).total_seconds(), self.retry_base_seconds)
            except ValueError:
                pass

        return min(self.retry_base_seconds * (2 ** attempt), 60.0)


def safe_json(response: requests.Response) -> Any:
    try:
        return response.json()
    except json.JSONDecodeError:
        return None


def extract_error_message(body: Any) -> str | None:
    if not isinstance(body, dict):
        return None
    if body.get("errorSummary"):
        return str(body["errorSummary"])
    if body.get("error"):
        return str(body["error"])
    if body.get("message"):
        return str(body["message"])
    return None
