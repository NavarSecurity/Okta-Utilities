from __future__ import annotations

import csv
import json
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .config import AppConfig
from .okta_client import OktaClient


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def parse_okta_datetime(value: Any) -> datetime | None:
    if value in (None, "", "null"):
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    text = str(value).strip()
    if not text:
        return None
    try:
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        return datetime.fromisoformat(text).astimezone(timezone.utc)
    except ValueError:
        return None


def days_since(value: Any, now: datetime | None = None) -> int | None:
    dt = parse_okta_datetime(value)
    if not dt:
        return None
    current = now or utc_now()
    return max(0, (current - dt).days)


def first_present(*values: Any) -> Any:
    for value in values:
        if value not in (None, ""):
            return value
    return ""


def flatten_user(user: dict[str, Any]) -> dict[str, Any]:
    profile = user.get("profile") if isinstance(user.get("profile"), dict) else {}
    row = {
        "id": first_present(user.get("id"), user.get("user_id")),
        "status": first_present(user.get("status"), user.get("user_status")),
        "created": first_present(user.get("created"), user.get("created_at")),
        "activated": user.get("activated", ""),
        "statusChanged": first_present(user.get("statusChanged"), user.get("status_changed")),
        "lastLogin": first_present(user.get("lastLogin"), user.get("last_login")),
        "lastUpdated": first_present(user.get("lastUpdated"), user.get("last_updated")),
        "passwordChanged": first_present(user.get("passwordChanged"), user.get("password_changed")),
        "login": first_present(user.get("login"), user.get("profile.login"), profile.get("login")),
        "email": first_present(user.get("email"), user.get("profile.email"), profile.get("email")),
        "firstName": first_present(user.get("firstName"), user.get("profile.firstName"), profile.get("firstName")),
        "lastName": first_present(user.get("lastName"), user.get("profile.lastName"), profile.get("lastName")),
        "appLinkCount": int(user.get("appLinkCount", user.get("app_link_count", 0)) or 0),
        "groupCount": int(user.get("groupCount", user.get("group_count", 0)) or 0),
    }
    return row


def read_users_file(path: str | Path) -> list[dict[str, Any]]:
    file_path = Path(path)
    if not file_path.exists():
        raise FileNotFoundError(f"Users file not found: {file_path}")
    if file_path.suffix.lower() == ".json":
        data = json.loads(file_path.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            for key in ("users", "items", "data"):
                if isinstance(data.get(key), list):
                    return data[key]
            return [data]
        if isinstance(data, list):
            return data
        raise ValueError("JSON users file must contain an array or object with users/items/data array.")
    with file_path.open("r", encoding="utf-8-sig", newline="") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def should_exclude(row: dict[str, Any], config: AppConfig) -> bool:
    user_id = str(row.get("id", ""))
    login = str(row.get("login", "")).lower()
    email = str(row.get("email", "")).lower()
    if user_id in set(config.filters.exclude_user_ids):
        return True
    if login in set(config.filters.exclude_logins) or email in set(config.filters.exclude_logins):
        return True
    for domain in config.filters.exclude_login_domains:
        if login.endswith("@" + domain) or email.endswith("@" + domain):
            return True
    return False


def analyze_user(user: dict[str, Any], config: AppConfig, now: datetime | None = None) -> dict[str, Any]:
    current = now or utc_now()
    row = flatten_user(user)
    rules = config.dormancy_rules
    reasons: list[str] = []
    evidence: list[str] = []

    status = str(row.get("status", "")).upper()
    created_days = days_since(row.get("created"), current)
    last_login_days = days_since(row.get("lastLogin"), current)
    password_changed_days = days_since(row.get("passwordChanged"), current)

    if status in set(rules.inactive_statuses):
        reasons.append("INACTIVE_STATUS")
        evidence.append(f"status={status}")

    if row.get("lastLogin"):
        if last_login_days is not None and last_login_days >= rules.stale_login_days:
            reasons.append("STALE_LOGIN")
            evidence.append(f"lastLoginDays={last_login_days}")
    else:
        if created_days is not None and created_days >= rules.never_logged_in_after_days:
            reasons.append("NEVER_LOGGED_IN")
            evidence.append(f"createdDays={created_days}; lastLogin is blank")

    if rules.flag_unassigned_to_apps and int(row.get("appLinkCount") or 0) == 0:
        reasons.append("NO_APP_LINKS")
        evidence.append("appLinkCount=0")

    if rules.flag_no_group_membership and int(row.get("groupCount") or 0) == 0:
        reasons.append("NO_GROUP_MEMBERSHIP")
        evidence.append("groupCount=0")

    if rules.flag_password_not_changed_days is not None and password_changed_days is not None:
        if password_changed_days >= rules.flag_password_not_changed_days:
            reasons.append("PASSWORD_NOT_CHANGED")
            evidence.append(f"passwordChangedDays={password_changed_days}")

    risk_score = 0
    weights = {
        "INACTIVE_STATUS": 35,
        "STALE_LOGIN": 30,
        "NEVER_LOGGED_IN": 30,
        "NO_APP_LINKS": 15,
        "NO_GROUP_MEMBERSHIP": 10,
        "PASSWORD_NOT_CHANGED": 10,
    }
    for reason in set(reasons):
        risk_score += weights.get(reason, 5)
    risk_score = min(100, risk_score)
    if risk_score >= 60:
        review_priority = "HIGH"
    elif risk_score >= 30:
        review_priority = "MEDIUM"
    elif risk_score > 0:
        review_priority = "LOW"
    else:
        review_priority = "NONE"

    return {
        **row,
        "createdDays": created_days if created_days is not None else "",
        "lastLoginDays": last_login_days if last_login_days is not None else "",
        "passwordChangedDays": password_changed_days if password_changed_days is not None else "",
        "isDormantCandidate": bool(reasons),
        "reasons": ";".join(sorted(set(reasons))),
        "evidence": " | ".join(evidence),
        "riskScore": risk_score,
        "reviewPriority": review_priority,
    }


class DormantUserFinder:
    def __init__(self, config: AppConfig):
        self.config = config

    def collect_users(self) -> tuple[list[dict[str, Any]], list[str]]:
        warnings: list[str] = []
        if self.config.source.mode == "file":
            return read_users_file(self.config.source.users_file), warnings

        client = OktaClient(
            self.config.org_url,
            self.config.api_token,
            timeout=self.config.api_options.request_timeout_seconds,
            max_retries=self.config.api_options.max_retries,
        )
        users = client.list_users(self.config.filters.statuses, limit=self.config.api_options.limit)

        if self.config.api_options.fetch_app_links or self.config.api_options.fetch_groups:
            for user in users:
                user_id = user.get("id")
                if not user_id:
                    continue
                if self.config.api_options.fetch_app_links:
                    try:
                        user["appLinkCount"] = len(client.list_user_app_links(user_id))
                    except Exception as exc:  # noqa: BLE001
                        user["appLinkCount"] = 0
                        warnings.append(f"Could not fetch app links for {user_id}: {exc}")
                if self.config.api_options.fetch_groups:
                    try:
                        user["groupCount"] = len(client.list_user_groups(user_id))
                    except Exception as exc:  # noqa: BLE001
                        user["groupCount"] = 0
                        warnings.append(f"Could not fetch groups for {user_id}: {exc}")
        return users, warnings

    def build_plan(self) -> dict[str, Any]:
        return {
            "mode": "dry-run",
            "sourceMode": self.config.source.mode,
            "orgUrl": self.config.org_url,
            "rules": asdict(self.config.dormancy_rules),
            "filters": asdict(self.config.filters),
            "apiOptions": asdict(self.config.api_options),
            "plannedOutputs": [
                "dormant_users.csv",
                "all_users_analyzed.csv",
                "summary_by_reason.csv",
                "dormant_user_report.md",
                "finder_result.json",
                "execution_report.md",
            ],
            "note": "Dry-run validates configuration and writes the plan only. Use --find to analyze users.",
        }

    def run(self) -> dict[str, Any]:
        users, warnings = self.collect_users()
        analyzed: list[dict[str, Any]] = []
        for user in users:
            row = analyze_user(user, self.config)
            if should_exclude(row, self.config):
                continue
            if self.config.filters.statuses and str(row.get("status", "")).upper() not in set(self.config.filters.statuses):
                continue
            analyzed.append(row)

        dormant = [row for row in analyzed if row["isDormantCandidate"]]
        reason_counts: dict[str, int] = {}
        for row in dormant:
            for reason in str(row.get("reasons", "")).split(";"):
                if reason:
                    reason_counts[reason] = reason_counts.get(reason, 0) + 1

        return {
            "mode": "find",
            "sourceMode": self.config.source.mode,
            "orgUrl": self.config.org_url,
            "counts": {
                "usersAnalyzed": len(analyzed),
                "dormantCandidates": len(dormant),
                "nonDormantUsers": len(analyzed) - len(dormant),
            },
            "summaryByReason": reason_counts,
            "warnings": warnings,
            "dormantUsers": dormant,
            "allUsersAnalyzed": analyzed,
            "rawUsers": users if self.config.output.include_raw_users else [],
        }
