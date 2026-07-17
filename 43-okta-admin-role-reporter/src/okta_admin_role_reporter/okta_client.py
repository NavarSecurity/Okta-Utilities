from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urlparse

import requests


@dataclass
class RequestFailure:
    method: str
    path: str
    status_code: int | None
    message: str


@dataclass
class OktaClient:
    org_url: str
    token: str
    timeout_seconds: int = 30
    failures: list[RequestFailure] = field(default_factory=list)

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"SSWS {self.token}",
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "okta-admin-role-reporter/1.0.0",
        }

    def _absolute_url(self, path_or_url: str) -> str:
        if path_or_url.startswith("http://") or path_or_url.startswith("https://"):
            return path_or_url
        path = path_or_url if path_or_url.startswith("/") else f"/{path_or_url}"
        return f"{self.org_url}{path}"

    def _safe_path(self, url_or_path: str) -> str:
        if url_or_path.startswith("http://") or url_or_path.startswith("https://"):
            parsed = urlparse(url_or_path)
            return parsed.path + (f"?{parsed.query}" if parsed.query else "")
        return url_or_path

    def request(self, method: str, path_or_url: str, **kwargs: Any) -> Any:
        url = self._absolute_url(path_or_url)
        retries = int(kwargs.pop("retries", 3))
        for attempt in range(retries):
            try:
                response = requests.request(
                    method,
                    url,
                    headers=self._headers(),
                    timeout=self.timeout_seconds,
                    **kwargs,
                )
            except requests.RequestException as exc:
                if attempt == retries - 1:
                    failure = RequestFailure(method, self._safe_path(path_or_url), None, str(exc))
                    self.failures.append(failure)
                    raise RuntimeError(f"{method} {self._safe_path(path_or_url)} failed: {exc}") from exc
                time.sleep(2**attempt)
                continue

            if response.status_code == 429 and attempt < retries - 1:
                reset = response.headers.get("X-Rate-Limit-Reset")
                if reset and reset.isdigit():
                    delay = max(1, int(reset) - int(time.time()))
                    time.sleep(min(delay, 30))
                else:
                    time.sleep(2**attempt)
                continue

            if 200 <= response.status_code < 300:
                if not response.text:
                    return None
                try:
                    return response.json()
                except ValueError:
                    return response.text

            message = self._extract_error(response)
            failure = RequestFailure(method, self._safe_path(path_or_url), response.status_code, message)
            self.failures.append(failure)
            raise RuntimeError(f"{method} {self._safe_path(path_or_url)} returned {response.status_code}: {message}")

        raise RuntimeError(f"{method} {self._safe_path(path_or_url)} failed after retries")

    def _extract_error(self, response: requests.Response) -> str:
        try:
            payload = response.json()
        except ValueError:
            return response.text[:500]
        if isinstance(payload, dict):
            if payload.get("errorSummary"):
                return str(payload.get("errorSummary"))
            if payload.get("error_description"):
                return str(payload.get("error_description"))
            if payload.get("message"):
                return str(payload.get("message"))
        return str(payload)[:500]

    def list_paginated(self, path: str, result_key: str | None = None) -> list[Any]:
        url_or_path = path
        records: list[Any] = []
        seen_urls: set[str] = set()
        while url_or_path:
            absolute_url = self._absolute_url(url_or_path)
            if absolute_url in seen_urls:
                break
            seen_urls.add(absolute_url)

            response = requests.get(
                absolute_url,
                headers=self._headers(),
                timeout=self.timeout_seconds,
            )
            if response.status_code == 429:
                reset = response.headers.get("X-Rate-Limit-Reset")
                delay = 1
                if reset and reset.isdigit():
                    delay = max(1, int(reset) - int(time.time()))
                time.sleep(min(delay, 30))
                response = requests.get(
                    absolute_url,
                    headers=self._headers(),
                    timeout=self.timeout_seconds,
                )
            if not (200 <= response.status_code < 300):
                message = self._extract_error(response)
                failure = RequestFailure("GET", self._safe_path(url_or_path), response.status_code, message)
                self.failures.append(failure)
                raise RuntimeError(f"GET {self._safe_path(url_or_path)} returned {response.status_code}: {message}")

            payload = response.json() if response.text else []
            if isinstance(payload, dict) and result_key and isinstance(payload.get(result_key), list):
                records.extend(payload[result_key])
            elif isinstance(payload, dict) and isinstance(payload.get("value"), list):
                records.extend(payload["value"])
            elif isinstance(payload, list):
                records.extend(payload)
            elif payload:
                records.append(payload)

            next_url = self._next_from_links_header(response.headers.get("Link", ""))
            if not next_url and isinstance(payload, dict):
                links = payload.get("_links", {})
                next_link = links.get("next") if isinstance(links, dict) else None
                if isinstance(next_link, dict):
                    next_url = next_link.get("href")
            url_or_path = next_url or ""
        return records

    @staticmethod
    def _next_from_links_header(link_header: str) -> str | None:
        if not link_header:
            return None
        for part in link_header.split(","):
            section = part.strip()
            if 'rel="next"' not in section and "rel=next" not in section:
                continue
            if section.startswith("<") and ">" in section:
                return section[1:section.index(">")]
        return None
