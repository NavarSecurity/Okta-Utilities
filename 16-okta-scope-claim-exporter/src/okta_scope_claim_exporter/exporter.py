from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from .config import ExportConfig
from .okta_client import OktaApiError, OktaClient


@dataclass
class ExportError:
    stage: str
    authorization_server_id: str | None
    authorization_server_name: str | None
    message: str
    status_code: int | None = None
    response_body: Any | None = None


@dataclass
class ExportResult:
    mode: str
    source_org_url: str
    authorization_servers: list[dict[str, Any]] = field(default_factory=list)
    scopes_by_authorization_server_id: dict[str, list[dict[str, Any]]] = field(default_factory=dict)
    claims_by_authorization_server_id: dict[str, list[dict[str, Any]]] = field(default_factory=dict)
    skipped_authorization_servers: list[dict[str, Any]] = field(default_factory=list)
    raw: dict[str, Any] = field(default_factory=dict)
    errors: list[ExportError] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "mode": self.mode,
            "sourceOrgUrl": self.source_org_url,
            "summary": self.summary(),
            "authorizationServers": self.authorization_servers,
            "scopesByAuthorizationServerId": self.scopes_by_authorization_server_id,
            "claimsByAuthorizationServerId": self.claims_by_authorization_server_id,
            "skippedAuthorizationServers": self.skipped_authorization_servers,
            "errors": [asdict(e) for e in self.errors],
        }

    def summary(self) -> dict[str, int]:
        return {
            "authorizationServersExported": len(self.authorization_servers),
            "authorizationServersSkipped": len(self.skipped_authorization_servers),
            "scopesExported": sum(len(v) for v in self.scopes_by_authorization_server_id.values()),
            "claimsExported": sum(len(v) for v in self.claims_by_authorization_server_id.values()),
            "errors": len(self.errors),
        }


class ScopeClaimExporter:
    def __init__(self, config: ExportConfig):
        self.config = config

    def build_plan(self) -> dict[str, Any]:
        return {
            "mode": "dry-run",
            "sourceOrgUrl": self.config.source_org_url,
            "settings": {
                "includeInactiveAuthorizationServers": self.config.settings.include_inactive_authorization_servers,
                "includeScopes": self.config.settings.include_scopes,
                "includeClaims": self.config.settings.include_claims,
                "includeRawResponses": self.config.settings.include_raw_responses,
                "continueOnError": self.config.settings.continue_on_error,
                "requestTimeoutSeconds": self.config.settings.request_timeout_seconds,
                "maxRetries": self.config.settings.max_retries,
            },
            "filters": {
                "authorizationServerIds": self.config.filters.authorization_server_ids,
                "authorizationServerNames": self.config.filters.authorization_server_names,
                "excludeAuthorizationServerIds": self.config.filters.exclude_authorization_server_ids,
                "excludeAuthorizationServerNames": self.config.filters.exclude_authorization_server_names,
            },
            "plannedActions": [
                "List custom authorization servers",
                "Filter authorization servers by configured include/exclude rules",
                "Export scopes for each matched authorization server" if self.config.settings.include_scopes else "Skip scope export",
                "Export claims for each matched authorization server" if self.config.settings.include_claims else "Skip claim export",
                "Write CSV, JSON, Markdown, and execution evidence output",
            ],
            "apiCallsWillBeMade": False,
        }

    def export(self) -> ExportResult:
        if not self.config.api_token:
            raise ValueError("Missing Okta API token. Set OKTA_API_TOKEN in .env or environment variables.")

        client = OktaClient(
            self.config.source_org_url,
            self.config.api_token,
            timeout_seconds=self.config.settings.request_timeout_seconds,
            max_retries=self.config.settings.max_retries,
        )
        result = ExportResult(mode="export", source_org_url=self.config.source_org_url)

        try:
            auth_servers = client.get_paginated("/api/v1/authorizationServers", params={"limit": 200})
            if self.config.settings.include_raw_responses:
                result.raw["authorization_servers"] = auth_servers
        except OktaApiError as exc:
            result.errors.append(self._error("authorization_servers", None, None, exc))
            return result

        matched_servers = []
        for server in auth_servers:
            if self._should_include_server(server):
                matched_servers.append(server)
            else:
                result.skipped_authorization_servers.append(self._server_summary(server, "Filtered out by config"))

        for server in matched_servers:
            server_id = server.get("id")
            server_name = server.get("name")
            result.authorization_servers.append(server)

            if not server_id:
                result.errors.append(
                    ExportError(
                        stage="authorization_server",
                        authorization_server_id=None,
                        authorization_server_name=server_name,
                        message="Authorization server object is missing id",
                    )
                )
                if not self.config.settings.continue_on_error:
                    break
                continue

            if self.config.settings.include_scopes:
                try:
                    scopes = client.get_paginated(f"/api/v1/authorizationServers/{server_id}/scopes", params={"limit": 200})
                    result.scopes_by_authorization_server_id[server_id] = scopes
                    if self.config.settings.include_raw_responses:
                        result.raw[f"{server_id}_scopes"] = scopes
                except OktaApiError as exc:
                    result.errors.append(self._error("scopes", server_id, server_name, exc))
                    if not self.config.settings.continue_on_error:
                        break

            if self.config.settings.include_claims:
                try:
                    claims = client.get_paginated(f"/api/v1/authorizationServers/{server_id}/claims", params={"limit": 200})
                    result.claims_by_authorization_server_id[server_id] = claims
                    if self.config.settings.include_raw_responses:
                        result.raw[f"{server_id}_claims"] = claims
                except OktaApiError as exc:
                    result.errors.append(self._error("claims", server_id, server_name, exc))
                    if not self.config.settings.continue_on_error:
                        break

        return result

    def _should_include_server(self, server: dict[str, Any]) -> bool:
        server_id = str(server.get("id") or "")
        server_name = str(server.get("name") or "")
        server_status = str(server.get("status") or "")

        if not self.config.settings.include_inactive_authorization_servers and server_status.upper() != "ACTIVE":
            return False

        filters = self.config.filters
        if filters.authorization_server_ids and server_id not in filters.authorization_server_ids:
            return False
        if filters.authorization_server_names and server_name not in filters.authorization_server_names:
            return False
        if filters.exclude_authorization_server_ids and server_id in filters.exclude_authorization_server_ids:
            return False
        if filters.exclude_authorization_server_names and server_name in filters.exclude_authorization_server_names:
            return False
        return True

    @staticmethod
    def _server_summary(server: dict[str, Any], reason: str) -> dict[str, Any]:
        return {
            "id": server.get("id"),
            "name": server.get("name"),
            "status": server.get("status"),
            "reason": reason,
        }

    @staticmethod
    def _error(stage: str, server_id: str | None, server_name: str | None, exc: OktaApiError) -> ExportError:
        return ExportError(
            stage=stage,
            authorization_server_id=server_id,
            authorization_server_name=server_name,
            message=str(exc),
            status_code=exc.status_code,
            response_body=exc.response_body,
        )
