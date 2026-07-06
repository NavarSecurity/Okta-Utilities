from __future__ import annotations

import csv
import json
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from .config import UserImportConfig, public_config
from .okta_client import OktaApiError, OktaClient

SENSITIVE_FIELD_NAMES = {"password", "temporarypassword", "temptpassword", "secret", "token", "apikey", "api_key"}


def utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def redact_value(key: str, value: Any) -> Any:
    normalized = key.replace("_", "").replace("-", "").lower()
    if normalized in SENSITIVE_FIELD_NAMES or "password" in normalized or "secret" in normalized or "token" in normalized:
        return "[REDACTED]" if value not in (None, "") else value
    return value


def redact_payload(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {k: redact_payload(redact_value(k, v)) for k, v in obj.items()}
    if isinstance(obj, list):
        return [redact_payload(item) for item in obj]
    return obj


class UserBulkImporter:
    def __init__(self, cfg: UserImportConfig, mode: str):
        if mode not in {"dry-run", "apply"}:
            raise ValueError("mode must be dry-run or apply")
        self.cfg = cfg
        self.mode = mode
        self.run_id = f"okta-user-bulk-importer-{utc_stamp()}"
        self.output_dir = Path("output") / self.run_id
        self.created_users: list[dict[str, Any]] = []
        self.updated_users: list[dict[str, Any]] = []
        self.skipped_users: list[dict[str, Any]] = []
        self.failed_users: list[dict[str, Any]] = []
        self.group_assignments: list[dict[str, Any]] = []
        self.rollback_actions: list[dict[str, Any]] = []
        self.plan_rows: list[dict[str, Any]] = []
        self.errors: list[dict[str, Any]] = []

    def run(self) -> dict[str, Any]:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        rows = self._load_csv(Path(self.cfg.inputUserCsv))
        client = None
        needs_okta = self.mode == "apply" or self.cfg.settings.performDuplicateCheckInDryRun
        if needs_okta:
            client = OktaClient(
                self.cfg.targetOrgUrl,
                self.cfg.apiToken,
                timeout=self.cfg.settings.requestTimeoutSeconds,
                max_retries=self.cfg.settings.maxRetries,
                rate_limit_sleep=self.cfg.settings.rateLimitSleepSeconds,
            )

        for index, row in enumerate(rows, start=2):
            try:
                self._process_row(index, row, client)
            except Exception as exc:
                error = {"rowNumber": index, "login": row.get("login") or row.get("email") or "", "error": str(exc)}
                self.failed_users.append(error)
                self.errors.append(error)
                if not self.cfg.settings.continueOnError:
                    break

        result = self._build_result(client)
        self._write_outputs(result)
        return result

    def _load_csv(self, path: Path) -> list[dict[str, str]]:
        if not path.exists():
            raise FileNotFoundError(f"Input CSV not found: {path}")
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            if not reader.fieldnames:
                raise ValueError("Input CSV has no header row")
            return [dict(row) for row in reader]

    def _process_row(self, row_number: int, row: dict[str, str], client: OktaClient | None) -> None:
        profile = self._build_profile(row)
        login = profile.get("login") or profile.get("email")
        validation_errors = self._validate_profile(profile)
        if validation_errors:
            self.failed_users.append({"rowNumber": row_number, "login": login or "", "errors": "; ".join(validation_errors)})
            return

        payload = {"profile": profile}
        if self.cfg.settings.allowPasswordImport and row.get(self.cfg.passwordColumn):
            payload["credentials"] = {"password": {"value": row[self.cfg.passwordColumn]}}

        groups = self._groups_for_row(row)
        existing_user = None
        duplicate_value = profile.get(self.cfg.duplicateLookupField)
        if client and duplicate_value:
            existing_user = client.get_user_by_login(str(duplicate_value))

        planned_action = "create"
        if existing_user:
            if self.cfg.settings.updateExisting:
                planned_action = "update"
            elif self.cfg.settings.skipExisting:
                planned_action = "skip_existing"
            else:
                planned_action = "duplicate_blocked"

        plan_item = {
            "rowNumber": row_number,
            "login": login,
            "email": profile.get("email"),
            "action": planned_action,
            "existingUserId": existing_user.get("id") if existing_user else "",
            "groupIds": groups,
            "payload": redact_payload(payload),
        }
        self.plan_rows.append(plan_item)

        if self.mode == "dry-run":
            if planned_action == "skip_existing":
                self.skipped_users.append({"rowNumber": row_number, "login": login, "reason": "User already exists", "existingUserId": plan_item["existingUserId"]})
            return

        if not client:
            raise RuntimeError("Okta client was not initialized")

        if planned_action == "skip_existing":
            self.skipped_users.append({"rowNumber": row_number, "login": login, "reason": "User already exists", "existingUserId": plan_item["existingUserId"]})
            return
        if planned_action == "duplicate_blocked":
            self.failed_users.append({"rowNumber": row_number, "login": login, "error": "User already exists and updateExisting=false"})
            return

        try:
            if planned_action == "update" and existing_user:
                updated = client.update_user_profile(existing_user["id"], profile)
                self.updated_users.append({"rowNumber": row_number, "id": updated.get("id"), "login": login, "status": updated.get("status")})
                user_id = updated.get("id")
            else:
                created = client.create_user(payload, activate=self.cfg.settings.activateUsers)
                self.created_users.append({"rowNumber": row_number, "id": created.get("id"), "login": login, "status": created.get("status")})
                user_id = created.get("id")
                if user_id:
                    self.rollback_actions.append({"action": "deactivate_or_delete_user", "method": "DELETE", "path": f"/api/v1/users/{user_id}", "login": login})

            if user_id and self.cfg.settings.assignGroups:
                for group_id in groups:
                    client.add_user_to_group(group_id, user_id)
                    self.group_assignments.append({"rowNumber": row_number, "userId": user_id, "login": login, "groupId": group_id, "status": "assigned"})
                    self.rollback_actions.append({"action": "remove_user_from_group", "method": "DELETE", "path": f"/api/v1/groups/{group_id}/users/{user_id}", "login": login})
        except OktaApiError as exc:
            self.failed_users.append({"rowNumber": row_number, "login": login, "statusCode": exc.status_code, "error": str(exc), "oktaError": exc.payload})
            if not self.cfg.settings.continueOnError:
                raise

    def _build_profile(self, row: dict[str, str]) -> dict[str, Any]:
        profile: dict[str, Any] = {}
        for okta_field, csv_field in self.cfg.profileFieldMap.items():
            if not csv_field:
                continue
            value = row.get(csv_field)
            if value is None:
                continue
            value = value.strip()
            if value == "":
                continue
            if okta_field == "password" or "password" in okta_field.lower():
                continue
            profile[okta_field] = value
        return profile

    def _validate_profile(self, profile: dict[str, Any]) -> list[str]:
        errors: list[str] = []
        for field in self.cfg.requiredProfileFields:
            if not profile.get(field):
                errors.append(f"Missing required profile field: {field}")
        if profile.get("login") and "@" not in str(profile["login"]):
            errors.append("login should usually be an email-style value")
        if profile.get("email") and "@" not in str(profile["email"]):
            errors.append("email must contain @")
        return errors

    def _groups_for_row(self, row: dict[str, str]) -> list[str]:
        group_ids = list(self.cfg.defaultGroupIds)
        raw = (row.get(self.cfg.perRowGroupIdsColumn) or "").strip()
        if raw:
            for item in raw.replace("|", ";").split(";"):
                item = item.strip()
                if item and item not in group_ids:
                    group_ids.append(item)
        return group_ids

    def _build_result(self, client: OktaClient | None) -> dict[str, Any]:
        return {
            "runId": self.run_id,
            "mode": self.mode,
            "targetOrgUrl": self.cfg.targetOrgUrl,
            "summary": {
                "plannedRows": len(self.plan_rows),
                "createdUsers": len(self.created_users),
                "updatedUsers": len(self.updated_users),
                "skippedUsers": len(self.skipped_users),
                "failedUsers": len(self.failed_users),
                "groupAssignments": len(self.group_assignments),
                "errors": len(self.errors),
            },
            "configuration": public_config(self.cfg),
            "createdUsers": self.created_users,
            "updatedUsers": self.updated_users,
            "skippedUsers": self.skipped_users,
            "failedUsers": redact_payload(self.failed_users),
            "groupAssignments": self.group_assignments,
            "requestSummary": self._request_summary(client),
        }

    def _request_summary(self, client: OktaClient | None) -> dict[str, Any]:
        if not client:
            return {"totalRequests": 0, "byStatus": {}}
        by_status: dict[str, int] = {}
        for item in client.request_log:
            code = str(item.get("status_code"))
            by_status[code] = by_status.get(code, 0) + 1
        return {"totalRequests": len(client.request_log), "byStatus": by_status}

    def _write_outputs(self, result: dict[str, Any]) -> None:
        self._write_json("user_import_plan.json", {"runId": self.run_id, "mode": self.mode, "targetOrgUrl": self.cfg.targetOrgUrl, "plannedUsers": self.plan_rows})
        self._write_json("user_import_result.json", result)
        self._write_json("rollback_plan.json", {"runId": self.run_id, "actions": self.rollback_actions})
        self._write_csv("created_users.csv", self.created_users)
        self._write_csv("updated_users.csv", self.updated_users)
        self._write_csv("skipped_users.csv", self.skipped_users)
        self._write_csv("failed_users.csv", self.failed_users)
        self._write_csv("group_assignments.csv", self.group_assignments)
        self._write_report(result)

    def _write_json(self, name: str, data: Any) -> None:
        with (self.output_dir / name).open("w", encoding="utf-8") as handle:
            json.dump(redact_payload(data), handle, indent=2, sort_keys=True)

    def _write_csv(self, name: str, rows: list[dict[str, Any]]) -> None:
        path = self.output_dir / name
        if not rows:
            path.write_text("", encoding="utf-8")
            return
        fieldnames = sorted({key for row in rows for key in row.keys()})
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            for row in rows:
                writer.writerow({k: json.dumps(v) if isinstance(v, (dict, list)) else v for k, v in redact_payload(row).items()})

    def _write_report(self, result: dict[str, Any]) -> None:
        summary = result["summary"]
        lines = [
            f"# Okta User Bulk Import Execution Report",
            "",
            f"Run ID: `{self.run_id}`",
            f"Mode: `{self.mode}`",
            f"Target org: `{self.cfg.targetOrgUrl}`",
            "",
            "## Summary",
            "",
            f"- Planned rows: {summary['plannedRows']}",
            f"- Created users: {summary['createdUsers']}",
            f"- Updated users: {summary['updatedUsers']}",
            f"- Skipped users: {summary['skippedUsers']}",
            f"- Failed users: {summary['failedUsers']}",
            f"- Group assignments: {summary['groupAssignments']}",
            "",
            "## Output Files",
            "",
            "- `user_import_plan.json`",
            "- `user_import_result.json`",
            "- `created_users.csv`",
            "- `updated_users.csv`",
            "- `skipped_users.csv`",
            "- `failed_users.csv`",
            "- `group_assignments.csv`",
            "- `rollback_plan.json`",
            "",
            "## Notes",
            "",
            "- Dry-run mode does not create or update users.",
            "- Password-like values are redacted from output.",
            "- Review failed and skipped CSV files before re-running in apply mode.",
        ]
        (self.output_dir / "execution_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
