from __future__ import annotations

import csv
import json
from collections import Counter
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

from .config import ExportConfig, is_sensitive_profile_key
from .okta_client import OktaApiError, OktaClient


def utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def write_json(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, indent=2, sort_keys=True, default=str), encoding="utf-8")


def write_csv(path: Path, rows: List[Dict[str, Any]], fieldnames: List[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({k: _csv_value(row.get(k, "")) for k in fieldnames})


def _csv_value(value: Any) -> Any:
    if value is None:
        return ""
    if isinstance(value, (dict, list)):
        return json.dumps(value, sort_keys=True)
    return value


class UserExporter:
    def __init__(self, config: ExportConfig, mode: str = "dry-run"):
        self.config = config
        self.mode = mode
        self.run_id = f"okta-user-exporter-{utc_stamp()}"
        self.output_dir = Path("output") / self.run_id
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.errors: List[Dict[str, Any]] = []
        self.warnings: List[str] = []

    def dry_run(self) -> Dict[str, Any]:
        plan = {
            "runId": self.run_id,
            "mode": "dry-run",
            "targetOrgUrl": self.config.org_url,
            "operation": "read-only user export",
            "willCallOktaApi": False,
            "filters": asdict(self.config.filters),
            "include": asdict(self.config.include),
            "settings": _safe_settings(self.config),
            "plannedOutputs": asdict(self.config.output),
            "notes": [
                "Dry-run does not call Okta.",
                "Use --export to perform read-only API calls and write export files.",
            ],
        }
        write_json(self.output_dir / "user_export_plan.json", plan)
        self._write_report(plan, result=None)
        return plan

    def export(self) -> Dict[str, Any]:
        client = OktaClient(
            self.config.org_url,
            self.config.api_token,
            timeout=self.config.settings.request_timeout_seconds,
            max_retries=self.config.settings.max_retries,
        )
        users = self._fetch_users(client)
        group_rows: List[Dict[str, Any]] = []
        app_link_rows: List[Dict[str, Any]] = []
        user_rows: List[Dict[str, Any]] = []
        users_json: List[Dict[str, Any]] = []
        raw_users: List[Dict[str, Any]] = []
        raw_groups_by_user: Dict[str, Any] = {}
        raw_app_links_by_user: Dict[str, Any] = {}

        for user in users:
            raw_users.append(user)
            user_summary = self._summarize_user(user)
            user_id = user.get("id", "")
            user_login = (user.get("profile") or {}).get("login", "")
            user_email = (user.get("profile") or {}).get("email", "")

            groups: List[Dict[str, Any]] = []
            app_links: List[Dict[str, Any]] = []
            if self.config.include.groups:
                try:
                    groups = client.get_user_groups(user_id)
                    raw_groups_by_user[user_id] = groups
                    for group in groups:
                        profile = group.get("profile") or {}
                        group_rows.append(
                            {
                                "user_id": user_id,
                                "user_login": user_login,
                                "user_email": user_email,
                                "group_id": group.get("id", ""),
                                "group_name": profile.get("name", ""),
                                "group_type": group.get("type", ""),
                                "group_description": profile.get("description", ""),
                            }
                        )
                except Exception as exc:  # noqa: BLE001
                    self._record_user_error("groups", user_id, user_login, exc)
                    if not self.config.settings.continue_on_error:
                        raise
            if self.config.include.app_links:
                try:
                    app_links = client.get_user_app_links(user_id)
                    raw_app_links_by_user[user_id] = app_links
                    for app in app_links:
                        app_link_rows.append(
                            {
                                "user_id": user_id,
                                "user_login": user_login,
                                "user_email": user_email,
                                "app_link_id": app.get("id", ""),
                                "app_instance_id": app.get("appInstanceId", ""),
                                "app_name": app.get("appName", ""),
                                "app_label": app.get("label", app.get("appName", "")),
                                "app_link_url": app.get("linkUrl", ""),
                                "credentials_setup": app.get("credentialsSetup", ""),
                                "hidden": app.get("hidden", ""),
                            }
                        )
                except Exception as exc:  # noqa: BLE001
                    self._record_user_error("appLinks", user_id, user_login, exc)
                    if not self.config.settings.continue_on_error:
                        raise

            user_summary["groupCount"] = len(groups)
            user_summary["appLinkCount"] = len(app_links)
            user_rows.append(user_summary)
            users_json.append(
                {
                    "user": user_summary,
                    "groups": group_rows_for_user(group_rows, user_id),
                    "appLinks": app_rows_for_user(app_link_rows, user_id),
                }
            )

        user_fieldnames = self._user_fieldnames(user_rows)
        write_csv(self.output_dir / self.config.output.users_csv, user_rows, user_fieldnames)
        write_csv(
            self.output_dir / self.config.output.user_groups_csv,
            group_rows,
            ["user_id", "user_login", "user_email", "group_id", "group_name", "group_type", "group_description"],
        )
        write_csv(
            self.output_dir / self.config.output.user_app_links_csv,
            app_link_rows,
            [
                "user_id",
                "user_login",
                "user_email",
                "app_link_id",
                "app_instance_id",
                "app_name",
                "app_label",
                "app_link_url",
                "credentials_setup",
                "hidden",
            ],
        )
        write_json(self.output_dir / self.config.output.users_json, users_json)

        status_counts = Counter(row.get("status", "UNKNOWN") for row in user_rows)
        summary_rows = [
            {"metric": "users_exported", "value": len(user_rows)},
            {"metric": "group_assignments_exported", "value": len(group_rows)},
            {"metric": "app_links_exported", "value": len(app_link_rows)},
            {"metric": "errors", "value": len(self.errors)},
        ]
        for status, count in sorted(status_counts.items()):
            summary_rows.append({"metric": f"users_status_{status}", "value": count})
        write_csv(self.output_dir / self.config.output.summary_csv, summary_rows, ["metric", "value"])

        if self.config.settings.save_raw_responses:
            self.warnings.append("Raw response output was enabled. Treat raw output as sensitive user data.")
            write_json(self.output_dir / "raw_users.json", raw_users)
            write_json(self.output_dir / "raw_groups_by_user.json", raw_groups_by_user)
            write_json(self.output_dir / "raw_app_links_by_user.json", raw_app_links_by_user)

        result = {
            "runId": self.run_id,
            "mode": "export",
            "targetOrgUrl": self.config.org_url,
            "counts": {
                "usersExported": len(user_rows),
                "groupAssignmentsExported": len(group_rows),
                "appLinksExported": len(app_link_rows),
                "errors": len(self.errors),
            },
            "statusCounts": dict(status_counts),
            "requestSummary": {
                "totalRequests": client.request_count,
                "byStatus": client.status_counts,
            },
            "warnings": self.warnings,
            "errors": self.errors,
            "outputFiles": [
                self.config.output.users_csv,
                self.config.output.users_json,
                self.config.output.user_groups_csv,
                self.config.output.user_app_links_csv,
                self.config.output.summary_csv,
                self.config.output.result_json,
                self.config.output.report_markdown,
            ],
        }
        write_json(self.output_dir / self.config.output.result_json, result)
        self._write_report(plan=None, result=result)
        return result

    def _fetch_users(self, client: OktaClient) -> List[Dict[str, Any]]:
        filters = self.config.filters
        users: List[Dict[str, Any]] = []
        if filters.user_ids:
            for user_id in filters.user_ids:
                try:
                    user = client.get_user(user_id)
                    users.append(user)
                except Exception as exc:  # noqa: BLE001
                    self._record_user_error("user", user_id, "", exc)
                    if not self.config.settings.continue_on_error:
                        raise
            return self._post_filter_users(users)

        params: Dict[str, Any] = {"limit": self.config.settings.page_limit}
        if filters.query:
            params["q"] = filters.query
        if filters.search:
            params["search"] = filters.search
        if filters.filter:
            params["filter"] = filters.filter
        users = client.list_users(params, max_users=self.config.settings.max_users)
        return self._post_filter_users(users)

    def _post_filter_users(self, users: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        filtered: List[Dict[str, Any]] = []
        statuses = set(self.config.filters.statuses)
        login_contains = self.config.filters.login_contains
        for user in users:
            status = str(user.get("status", "")).upper()
            profile = user.get("profile") or {}
            login = str(profile.get("login", "")).lower()
            if statuses and status not in statuses:
                continue
            if login_contains and login_contains not in login:
                continue
            filtered.append(user)
            if self.config.settings.max_users is not None and len(filtered) >= self.config.settings.max_users:
                break
        return filtered

    def _summarize_user(self, user: Dict[str, Any]) -> Dict[str, Any]:
        profile = user.get("profile") or {}
        row: Dict[str, Any] = {
            "id": user.get("id", ""),
            "status": user.get("status", ""),
            "created": user.get("created", ""),
            "activated": user.get("activated", ""),
            "statusChanged": user.get("statusChanged", ""),
            "lastLogin": user.get("lastLogin", ""),
            "lastUpdated": user.get("lastUpdated", ""),
            "passwordChanged": user.get("passwordChanged", ""),
            "type_id": ((user.get("type") or {}).get("id") if isinstance(user.get("type"), dict) else ""),
        }
        fields = sorted(profile.keys()) if self.config.filters.include_profile_all else self.config.filters.profile_fields
        for field in fields:
            value = profile.get(field, "")
            key = f"profile.{field}"
            if self.config.settings.redact_sensitive_profile_fields and is_sensitive_profile_key(field):
                row[key] = "[REDACTED]" if value not in ("", None) else ""
            else:
                row[key] = value
        # Common aliases for easier filtering in spreadsheets.
        row["login"] = profile.get("login", "")
        row["email"] = profile.get("email", "")
        row["firstName"] = profile.get("firstName", "")
        row["lastName"] = profile.get("lastName", "")
        return row

    def _user_fieldnames(self, rows: List[Dict[str, Any]]) -> List[str]:
        first = [
            "id",
            "status",
            "login",
            "email",
            "firstName",
            "lastName",
            "created",
            "activated",
            "statusChanged",
            "lastLogin",
            "lastUpdated",
            "passwordChanged",
            "type_id",
            "groupCount",
            "appLinkCount",
        ]
        all_keys = sorted({key for row in rows for key in row.keys()})
        return first + [key for key in all_keys if key not in first]

    def _record_user_error(self, operation: str, user_id: str, user_login: str, exc: Exception) -> None:
        payload = None
        status_code = None
        if isinstance(exc, OktaApiError):
            payload = exc.payload
            status_code = exc.status_code
        self.errors.append(
            {
                "operation": operation,
                "userId": user_id,
                "userLogin": user_login,
                "errorType": exc.__class__.__name__,
                "statusCode": status_code,
                "message": str(exc),
                "payload": payload,
            }
        )

    def _write_report(self, plan: Dict[str, Any] | None, result: Dict[str, Any] | None) -> None:
        lines: List[str] = []
        lines.append(f"# Okta User Export Report")
        lines.append("")
        lines.append(f"Run ID: `{self.run_id}`")
        lines.append(f"Mode: `{self.mode}`")
        lines.append(f"Target org: `{self.config.org_url}`")
        lines.append("")
        if plan:
            lines.append("## Dry-Run Plan")
            lines.append("")
            lines.append("Dry-run completed without calling Okta.")
            lines.append("")
            lines.append("### Planned Includes")
            lines.append("")
            lines.append(f"- Groups: `{self.config.include.groups}`")
            lines.append(f"- App links: `{self.config.include.app_links}`")
            lines.append(f"- Raw responses: `{self.config.settings.save_raw_responses}`")
        if result:
            lines.append("## Results")
            lines.append("")
            counts = result.get("counts", {})
            lines.append(f"- Users exported: `{counts.get('usersExported', 0)}`")
            lines.append(f"- Group assignments exported: `{counts.get('groupAssignmentsExported', 0)}`")
            lines.append(f"- App links exported: `{counts.get('appLinksExported', 0)}`")
            lines.append(f"- Errors: `{counts.get('errors', 0)}`")
            lines.append("")
            status_counts = result.get("statusCounts", {})
            if status_counts:
                lines.append("### Users by Status")
                lines.append("")
                for status, count in sorted(status_counts.items()):
                    lines.append(f"- {status}: `{count}`")
                lines.append("")
            lines.append("### Request Summary")
            lines.append("")
            req = result.get("requestSummary", {})
            lines.append(f"- Total requests: `{req.get('totalRequests', 0)}`")
            lines.append(f"- Status counts: `{req.get('byStatus', {})}`")
            lines.append("")
            if result.get("warnings"):
                lines.append("### Warnings")
                lines.append("")
                for warning in result["warnings"]:
                    lines.append(f"- {warning}")
                lines.append("")
            if result.get("errors"):
                lines.append("### Errors")
                lines.append("")
                for error in result["errors"]:
                    lines.append(f"- `{error.get('operation')}` for `{error.get('userLogin') or error.get('userId')}`: {error.get('message')}")
                lines.append("")
        lines.append("## Output Files")
        lines.append("")
        for name in asdict(self.config.output).values():
            lines.append(f"- `{name}`")
        lines.append("")
        lines.append("Treat user exports as sensitive identity data.")
        (self.output_dir / self.config.output.report_markdown).write_text("\n".join(lines), encoding="utf-8")


def _safe_settings(config: ExportConfig) -> Dict[str, Any]:
    data = asdict(config.settings)
    return data


def group_rows_for_user(rows: List[Dict[str, Any]], user_id: str) -> List[Dict[str, Any]]:
    return [row for row in rows if row.get("user_id") == user_id]


def app_rows_for_user(rows: List[Dict[str, Any]], user_id: str) -> List[Dict[str, Any]]:
    return [row for row in rows if row.get("user_id") == user_id]
