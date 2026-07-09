from __future__ import annotations

import time
from typing import Any, Dict, List, Optional
from urllib.parse import quote
import requests


class OktaApiError(Exception):
    def __init__(self, message: str, status_code: int | None = None, response: Any = None):
        super().__init__(message)
        self.status_code = status_code
        self.response = response


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
        })

    def _request(self, method: str, path: str, **kwargs: Any) -> requests.Response:
        url = f"{self.org_url}{path}"
        last_response = None
        for attempt in range(self.max_retries + 1):
            response = self.session.request(method, url, timeout=self.timeout, **kwargs)
            last_response = response
            if response.status_code in {429, 500, 502, 503, 504} and attempt < self.max_retries:
                retry_after = response.headers.get("Retry-After")
                sleep_for = int(retry_after) if retry_after and retry_after.isdigit() else min(2 ** attempt, 8)
                time.sleep(sleep_for)
                continue
            return response
        return last_response  # type: ignore[return-value]

    def _json_or_text(self, response: requests.Response) -> Any:
        try:
            return response.json()
        except Exception:
            return response.text

    def get_user(self, user_identifier: str) -> Dict[str, Any]:
        encoded = quote(user_identifier, safe="")
        response = self._request("GET", f"/api/v1/users/{encoded}")
        if response.status_code >= 400:
            raise OktaApiError("Unable to fetch user", response.status_code, self._json_or_text(response))
        return response.json()

    def list_factors(self, user_id: str) -> List[Dict[str, Any]]:
        encoded = quote(user_id, safe="")
        response = self._request("GET", f"/api/v1/users/{encoded}/factors")
        if response.status_code >= 400:
            raise OktaApiError("Unable to list factors", response.status_code, self._json_or_text(response))
        return response.json()

    def reset_all_factors(self, user_id: str) -> Any:
        encoded = quote(user_id, safe="")
        response = self._request("POST", f"/api/v1/users/{encoded}/lifecycle/reset_factors")
        if response.status_code >= 400:
            raise OktaApiError("Unable to reset all factors", response.status_code, self._json_or_text(response))
        return self._json_or_text(response)

    def delete_factor(self, user_id: str, factor_id: str) -> Any:
        encoded_user = quote(user_id, safe="")
        encoded_factor = quote(factor_id, safe="")
        response = self._request("DELETE", f"/api/v1/users/{encoded_user}/factors/{encoded_factor}")
        if response.status_code >= 400:
            raise OktaApiError("Unable to delete factor", response.status_code, self._json_or_text(response))
        return self._json_or_text(response)

    def delete_authenticator_enrollment(self, user_id: str, enrollment_id: str) -> Any:
        encoded_user = quote(user_id, safe="")
        encoded_enrollment = quote(enrollment_id, safe="")
        response = self._request("DELETE", f"/api/v1/users/{encoded_user}/authenticator-enrollments/{encoded_enrollment}")
        if response.status_code >= 400:
            raise OktaApiError("Unable to delete authenticator enrollment", response.status_code, self._json_or_text(response))
        return self._json_or_text(response)
