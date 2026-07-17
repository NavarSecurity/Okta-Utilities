from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests

from .config import Config, read_lines_if_exists
from .normalize import (
    app_client_id,
    days_since,
    is_oidc_app,
    is_service_app,
    normalize_api_token,
    normalize_app,
    normalize_client_role,
    normalize_grant,
    value_list,
)
from .okta_client import OktaClient, RequestFailure
from .redact import redact
from .reports import utc_timestamp, write_csv, write_json, write_markdown


class ApiAccessAuditor:
    def __init__(self, client: OktaClient, config: Config):
        self.client = client
        self.config = config
        self.failures: list[RequestFailure] = []

    def dry_run(self) -> dict[str, Any]:
        timestamp = utc_timestamp()
        out_dir = Path(self.config.output_directory) / f"api-access-audit-dry-run-{timestamp}"
        out_dir.mkdir(parents=True, exist_ok=True)
        report = {
            "status": "DRY_RUN",
            "timestamp": timestamp,
            "message": "Configuration validated. No Okta export calls were made.",
            "includeApiTokens": self.config.include_api_tokens,
            "includeOAuthApps": self.config.include_oauth_apps,
            "includeAppGrants": self.config.include_app_grants,
            "includeClientRoleAssignments": self.config.include_client_role_assignments,
            "appSelectionMode": self.config.app_selection.mode,
            "outputDirectory": str(out_dir),
        }
        write_json(out_dir / "dry_run_report.json", report)
        write_json(out_dir / "execution_report.json", report)
        write_json(out_dir / "manifest.json", {"files": ["dry_run_report.json", "execution_report.json"]})
        return report

    def run(self) -> dict[str, Any]:
        timestamp = utc_timestamp()
        out_dir = Path(self.config.output_directory) / f"api-access-audit-{timestamp}"
        out_dir.mkdir(parents=True, exist_ok=True)

        api_tokens: list[dict[str, Any]] = []
        api_token_rows: list[dict[str, Any]] = []
        apps: list[dict[str, Any]] = []
        selected_apps: list[dict[str, Any]] = []
        app_rows: list[dict[str, Any]] = []
        grant_records: list[dict[str, Any]] = []
        grant_rows: list[dict[str, Any]] = []
        role_records: list[dict[str, Any]] = []
        role_rows: list[dict[str, Any]] = []

        if self.config.include_api_tokens:
            api_tokens = self._safe_paged("/api/v1/api-tokens", {"limit": 200}, "api_tokens")
            api_token_rows = [normalize_api_token(t) for t in api_tokens]

        if self.config.include_oauth_apps:
            apps = self._safe_paged("/api/v1/apps", {"limit": 200}, "apps")
            selected_apps = self._select_apps(apps)
            app_rows = [normalize_app(app) for app in selected_apps]

        if self.config.include_app_grants and selected_apps:
            for app in selected_apps:
                grants = self._safe_paged(
                    f"/api/v1/apps/{app.get('id')}/grants",
                    {"limit": 200},
                    f"app_grants:{app.get('label') or app.get('id')}",
                )
                grant_records.append(
                    {
                        "appId": app.get("id", ""),
                        "appLabel": app.get("label", ""),
                        "clientId": app_client_id(app),
                        "grants": grants,
                    }
                )
                grant_rows.extend(normalize_grant(app, grant) for grant in grants)

        if self.config.include_client_role_assignments and selected_apps:
            for app in selected_apps:
                client_id = app_client_id(app)
                if not client_id:
                    self.failures.append(RequestFailure("/oauth2/v1/clients/{clientId}/roles", None, "Missing client_id", app.get("label", "")))
                    continue
                roles = self._safe_paged(
                    f"/oauth2/v1/clients/{client_id}/roles",
                    None,
                    f"client_roles:{app.get('label') or client_id}",
                )
                role_records.append(
                    {
                        "appId": app.get("id", ""),
                        "appLabel": app.get("label", ""),
                        "clientId": client_id,
                        "roles": roles,
                    }
                )
                role_rows.extend(normalize_client_role(app, role) for role in roles)

        findings = self._build_findings(api_token_rows, app_rows, grant_rows, role_rows)
        high_risk_clients = self._build_high_risk_clients(app_rows, grant_rows, role_rows, findings)
        failure_rows = [f.__dict__ for f in self.failures]

        raw_api_tokens = redact(api_tokens) if self.config.redact_sensitive_values else api_tokens
        raw_apps = redact(selected_apps) if self.config.redact_sensitive_values else selected_apps
        raw_grants = redact(grant_records) if self.config.redact_sensitive_values else grant_records
        raw_roles = redact(role_records) if self.config.redact_sensitive_values else role_records

        write_json(out_dir / "api_tokens_full.json", raw_api_tokens)
        write_csv(out_dir / "api_tokens_summary.csv", api_token_rows)
        write_json(out_dir / "oauth_apps_full.json", raw_apps)
        write_csv(out_dir / "oauth_apps_summary.csv", app_rows)
        write_json(out_dir / "app_grants_full.json", raw_grants)
        write_csv(out_dir / "app_grants.csv", grant_rows)
        write_json(out_dir / "client_role_assignments_full.json", raw_roles)
        write_csv(out_dir / "client_role_assignments.csv", role_rows)
        write_csv(out_dir / "high_risk_clients.csv", high_risk_clients)
        write_csv(out_dir / "api_access_risk_findings.csv", findings)
        write_csv(out_dir / "request_failures.csv", failure_rows)

        counts = Counter(f["severity"] for f in findings)
        execution_report = {
            "status": "SUCCESS" if not failure_rows or self.config.continue_on_request_error else "COMPLETED_WITH_ERRORS",
            "timestamp": timestamp,
            "outputDirectory": str(out_dir),
            "apiTokensExported": len(api_token_rows),
            "appsDiscovered": len(apps),
            "oauthAppsSelected": len(app_rows),
            "appGrantsExported": len(grant_rows),
            "clientRoleAssignmentsExported": len(role_rows),
            "riskFindings": len(findings),
            "findingCounts": dict(counts),
            "requestFailures": len(failure_rows),
        }
        write_json(out_dir / "execution_report.json", execution_report)
        write_json(
            out_dir / "manifest.json",
            {
                "utility": "okta-api-access-auditor",
                "timestamp": timestamp,
                "files": [
                    "api_tokens_full.json",
                    "api_tokens_summary.csv",
                    "oauth_apps_full.json",
                    "oauth_apps_summary.csv",
                    "app_grants_full.json",
                    "app_grants.csv",
                    "client_role_assignments_full.json",
                    "client_role_assignments.csv",
                    "high_risk_clients.csv",
                    "api_access_risk_findings.csv",
                    "request_failures.csv",
                    "api_access_audit_report.md",
                    "execution_report.json",
                ],
            },
        )
        write_markdown(
            out_dir / "api_access_audit_report.md",
            {
                "timestamp": timestamp,
                "apiTokens": len(api_token_rows),
                "oauthApps": len(app_rows),
                "appGrants": len(grant_rows),
                "clientRoles": len(role_rows),
                "riskFindings": len(findings),
                "requestFailures": len(failure_rows),
                "findingCounts": dict(counts),
            },
        )
        return execution_report

    def _safe_paged(self, endpoint: str, params: dict[str, Any] | None, context: str) -> list[dict[str, Any]]:
        try:
            data = self.client.get_paged(endpoint, params)
            return [item for item in data if isinstance(item, dict)]
        except requests.HTTPError as exc:
            response = getattr(exc, "response", None)
            status_code = getattr(response, "status_code", None)
            message = str(exc)
            self.failures.append(RequestFailure(endpoint, status_code, message, context))
            if not self.config.continue_on_request_error:
                raise
            return []
        except Exception as exc:
            self.failures.append(RequestFailure(endpoint, None, str(exc), context))
            if not self.config.continue_on_request_error:
                raise
            return []

    def _select_apps(self, apps: list[dict[str, Any]]) -> list[dict[str, Any]]:
        selection = self.config.app_selection
        file_values = set(read_lines_if_exists(selection.app_file))
        ids = set(selection.app_ids) | {v for v in file_values if v.startswith("0oa")}
        names = set(selection.app_names) | {v for v in file_values if not v.startswith("0oa")}

        selected: list[dict[str, Any]] = []
        for app in apps:
            if not self.config.include_inactive_apps and app.get("status") != "ACTIVE":
                continue
            mode = selection.mode.lower()
            if mode == "all":
                selected.append(app)
            elif mode == "all_oidc":
                if is_oidc_app(app):
                    selected.append(app)
            elif mode == "service":
                if is_service_app(app):
                    selected.append(app)
            elif mode == "ids":
                if app.get("id") in ids:
                    selected.append(app)
            elif mode == "names":
                if app.get("label") in names or app.get("name") in names:
                    selected.append(app)
            elif mode == "file":
                if app.get("id") in ids or app.get("label") in names or app.get("name") in names:
                    selected.append(app)
            else:
                if is_service_app(app):
                    selected.append(app)
        return selected

    def _build_findings(
        self,
        api_tokens: list[dict[str, Any]],
        apps: list[dict[str, Any]],
        grants: list[dict[str, Any]],
        roles: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        findings: list[dict[str, Any]] = []
        now = datetime.now(timezone.utc)
        rules = self.config.risk_rules
        high_scopes = set(rules.high_risk_scopes)
        high_roles = set(rules.high_risk_roles)

        for token in api_tokens:
            token_id = token.get("tokenId", "")
            name = token.get("name", "")
            last_used_days = days_since(token.get("lastUsed"), now)
            created_days = days_since(token.get("created"), now)
            network = str(token.get("networkConnection", "") or "").upper()
            if last_used_days is None:
                findings.append(self._finding("MEDIUM", "API_TOKEN_LAST_USED_UNKNOWN", "api_token", token_id, name, "API token has no last-used timestamp in the export."))
            elif last_used_days >= rules.stale_api_token_days:
                findings.append(self._finding("MEDIUM", "STALE_API_TOKEN", "api_token", token_id, name, f"API token has not been used for {last_used_days} days."))
            if created_days is not None and created_days >= rules.old_api_token_days:
                findings.append(self._finding("LOW", "OLD_API_TOKEN", "api_token", token_id, name, f"API token was created {created_days} days ago."))
            if rules.flag_broad_network_api_tokens and network in {"ANYWHERE", "ANY", "ALL", ""}:
                findings.append(self._finding("HIGH", "API_TOKEN_BROAD_NETWORK", "api_token", token_id, name, "API token has broad or unspecified network restrictions."))

        grants_by_client: dict[str, list[dict[str, Any]]] = defaultdict(list)
        roles_by_client: dict[str, list[dict[str, Any]]] = defaultdict(list)
        apps_by_client = {app.get("clientId", ""): app for app in apps if app.get("clientId")}
        for grant in grants:
            grants_by_client[grant.get("clientId", "")].append(grant)
            scope = grant.get("scope", "")
            if scope in high_scopes or scope.endswith(".manage"):
                findings.append(self._finding("HIGH", "HIGH_RISK_OAUTH_SCOPE", "oauth_client", grant.get("clientId", ""), grant.get("appLabel", ""), f"Client has high-risk OAuth scope: {scope}"))
        for role in roles:
            roles_by_client[role.get("clientId", "")].append(role)
            role_type = role.get("roleType", "")
            if role_type in high_roles:
                severity = "CRITICAL" if role_type in {"SUPER_ADMIN", "ORG_ADMIN"} else "HIGH"
                findings.append(self._finding(severity, "HIGH_RISK_CLIENT_ADMIN_ROLE", "oauth_client", role.get("clientId", ""), role.get("appLabel", ""), f"Client has high-risk admin role: {role_type}"))

        for client_id, app in apps_by_client.items():
            client_grants = grants_by_client.get(client_id, [])
            client_roles = roles_by_client.get(client_id, [])
            if rules.flag_client_with_scopes_but_no_roles and client_grants and not client_roles:
                findings.append(self._finding("MEDIUM", "CLIENT_SCOPES_WITHOUT_ADMIN_ROLE_EXPORT", "oauth_client", client_id, app.get("label", ""), "Client has granted OAuth scopes but no client admin role assignments were exported."))
            if rules.flag_client_with_roles_but_no_scopes and client_roles and not client_grants:
                findings.append(self._finding("MEDIUM", "CLIENT_ROLES_WITHOUT_SCOPE_EXPORT", "oauth_client", client_id, app.get("label", ""), "Client has admin role assignments but no OAuth scope grants were exported."))
            app_age_days = days_since(app.get("lastUpdated"), now)
            if app_age_days is not None and app_age_days >= rules.stale_app_days:
                findings.append(self._finding("LOW", "OAUTH_CLIENT_NOT_RECENTLY_UPDATED", "oauth_client", client_id, app.get("label", ""), f"Client app has not been updated for {app_age_days} days."))
        return findings

    @staticmethod
    def _finding(severity: str, code: str, object_type: str, object_id: str, object_name: str, detail: str) -> dict[str, Any]:
        return {
            "severity": severity,
            "findingCode": code,
            "objectType": object_type,
            "objectId": object_id,
            "objectName": object_name,
            "detail": detail,
        }

    def _build_high_risk_clients(
        self,
        apps: list[dict[str, Any]],
        grants: list[dict[str, Any]],
        roles: list[dict[str, Any]],
        findings: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        grants_by_client: dict[str, list[dict[str, Any]]] = defaultdict(list)
        roles_by_client: dict[str, list[dict[str, Any]]] = defaultdict(list)
        findings_by_client: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for grant in grants:
            grants_by_client[grant.get("clientId", "")].append(grant)
        for role in roles:
            roles_by_client[role.get("clientId", "")].append(role)
        for finding in findings:
            if finding.get("objectType") == "oauth_client":
                findings_by_client[finding.get("objectId", "")].append(finding)

        rows: list[dict[str, Any]] = []
        for app in apps:
            client_id = app.get("clientId", "")
            client_findings = findings_by_client.get(client_id, [])
            if not client_findings:
                continue
            rows.append(
                {
                    "appId": app.get("appId", ""),
                    "appLabel": app.get("label", ""),
                    "clientId": client_id,
                    "applicationType": app.get("applicationType", ""),
                    "grantTypes": app.get("grantTypes", ""),
                    "highRiskScopes": ";".join(value_list(grants_by_client.get(client_id, []), "scope")),
                    "adminRoles": ";".join(value_list(roles_by_client.get(client_id, []), "roleType")),
                    "findingCount": len(client_findings),
                    "highestSeverity": self._highest_severity(client_findings),
                }
            )
        return rows

    @staticmethod
    def _highest_severity(findings: list[dict[str, Any]]) -> str:
        order = {"CRITICAL": 4, "HIGH": 3, "MEDIUM": 2, "LOW": 1}
        if not findings:
            return ""
        return max((f.get("severity", "LOW") for f in findings), key=lambda s: order.get(s, 0))
