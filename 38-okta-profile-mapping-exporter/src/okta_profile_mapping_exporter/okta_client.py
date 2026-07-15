from __future__ import annotations

import time
from typing import Any
from urllib.parse import urljoin

import requests


class OktaClient:
    def __init__(
        self,
        org_url: str,
        api_token: str,
        timeout_seconds: int = 30,
        max_attempts: int = 3,
        backoff_seconds: float = 1.0,
    ) -> None:
        self.org_url = normalize_org_url(org_url)
        self.timeout_seconds = timeout_seconds
        self.max_attempts = max_attempts
        self.backoff_seconds = backoff_seconds
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Authorization": f"SSWS {api_token}",
                "Accept": "application/json",
                "Content-Type": "application/json",
            }
        )

    def list_profile_mappings(
        self,
        limit: int = 200,
        source_id: str | None = None,
        target_id: str | None = None,
    ) -> list[dict[str, Any]]:
        params: dict[str, Any] = {"limit": limit}
        if source_id:
            params["sourceId"] = source_id
        if target_id:
            params["targetId"] = target_id

        url = f"{self.org_url}/api/v1/mappings"
        mappings: list[dict[str, Any]] = []

        while url:
            response = self._request("GET", url, params=params)
            data = response.json()
            if not isinstance(data, list):
                raise ValueError("Expected list response from profile mappings endpoint")
            mappings.extend(data)
            url = parse_next_link(response.headers.get("Link", ""))
            params = None
        return mappings

    def get_profile_mapping(self, mapping_id: str) -> dict[str, Any]:
        url = f"{self.org_url}/api/v1/mappings/{mapping_id}"
        response = self._request("GET", url)
        data = response.json()
        if not isinstance(data, dict):
            raise ValueError(f"Expected object response for mapping {mapping_id}")
        return data

    def _request(self, method: str, url: str, **kwargs: Any) -> requests.Response:
        last_response: requests.Response | None = None
        last_error: Exception | None = None

        for attempt in range(1, self.max_attempts + 1):
            try:
                response = self.session.request(
                    method,
                    url,
                    timeout=self.timeout_seconds,
                    **kwargs,
                )
                last_response = response
                if response.status_code in {429, 500, 502, 503, 504} and attempt < self.max_attempts:
                    retry_after = response.headers.get("Retry-After")
                    sleep_seconds = float(retry_after) if retry_after else self.backoff_seconds * attempt
                    time.sleep(sleep_seconds)
                    continue
                if not response.ok:
                    raise OktaApiError(response.status_code, safe_error_text(response))
                return response
            except requests.RequestException as exc:
                last_error = exc
                if attempt < self.max_attempts:
                    time.sleep(self.backoff_seconds * attempt)
                    continue
                raise OktaApiError(0, str(exc)) from exc

        if last_response is not None:
            raise OktaApiError(last_response.status_code, safe_error_text(last_response))
        raise OktaApiError(0, str(last_error) if last_error else "Unknown API error")


class OktaApiError(RuntimeError):
    def __init__(self, status_code: int, message: str) -> None:
        self.status_code = status_code
        super().__init__(f"Okta API request failed with status {status_code}: {message}")


def normalize_org_url(org_url: str) -> str:
    clean = org_url.strip().rstrip("/")
    if not clean.startswith("https://"):
        raise ValueError("OKTA_ORG_URL must start with https://")
    if clean.endswith("/api/v1"):
        clean = clean[: -len("/api/v1")]
    return clean


def parse_next_link(link_header: str) -> str | None:
    if not link_header:
        return None
    for part in link_header.split(","):
        section = part.strip()
        if 'rel="next"' not in section:
            continue
        if section.startswith("<") and ">" in section:
            return section[1 : section.index(">")]
    return None


def safe_error_text(response: requests.Response) -> str:
    try:
        data = response.json()
        if isinstance(data, dict):
            return data.get("errorSummary") or data.get("errorCode") or response.text[:500]
    except ValueError:
        pass
    return response.text[:500]
