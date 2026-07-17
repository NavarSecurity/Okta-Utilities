from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from urllib.parse import urljoin

import requests


@dataclass
class RequestFailure:
    endpoint: str
    status_code: int | None
    message: str
    context: str = ""


class OktaClient:
    def __init__(self, org_url: str, api_token: str, timeout_seconds: int = 30):
        self.org_url = org_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Authorization": f"SSWS {api_token}",
                "Accept": "application/json",
                "Content-Type": "application/json",
                "User-Agent": "okta-rate-limit-monitor/1.0",
            }
        )

    def _url(self, path_or_url: str) -> str:
        if path_or_url.startswith("http://") or path_or_url.startswith("https://"):
            return path_or_url
        return urljoin(self.org_url + "/", path_or_url.lstrip("/"))

    def get_response(self, path_or_url: str, params: dict[str, Any] | None = None) -> requests.Response:
        url = self._url(path_or_url)
        response = self.session.get(url, params=params, timeout=self.timeout_seconds)
        if response.status_code >= 400:
            try:
                body = response.json()
                message = body.get("errorSummary") or body.get("error") or response.text
            except Exception:
                message = response.text
            raise requests.HTTPError(message, response=response)
        return response

    def get_json(self, path_or_url: str, params: dict[str, Any] | None = None) -> Any:
        response = self.get_response(path_or_url, params=params)
        if not response.text:
            return None
        return response.json()

    def get_paged(self, path_or_url: str, params: dict[str, Any] | None = None) -> list[Any]:
        url = self._url(path_or_url)
        results: list[Any] = []
        next_url: str | None = url
        next_params = params.copy() if params else None

        while next_url:
            response = self.session.get(next_url, params=next_params, timeout=self.timeout_seconds)
            if response.status_code >= 400:
                try:
                    body = response.json()
                    message = body.get("errorSummary") or body.get("error") or response.text
                except Exception:
                    message = response.text
                raise requests.HTTPError(message, response=response)

            data = response.json() if response.text else []
            if isinstance(data, list):
                results.extend(data)
            elif data is not None:
                results.append(data)

            next_url = self._next_link(response.headers.get("Link", ""))
            next_params = None
        return results

    @staticmethod
    def _next_link(link_header: str) -> str | None:
        if not link_header:
            return None
        for part in link_header.split(","):
            pieces = part.split(";")
            if len(pieces) < 2:
                continue
            url_part = pieces[0].strip()
            rel_part = ";".join(pieces[1:]).strip()
            if 'rel="next"' in rel_part and url_part.startswith("<") and url_part.endswith(">"):
                return url_part[1:-1]
        return None
