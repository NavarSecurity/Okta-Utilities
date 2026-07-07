from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from .utils import normalize_okta_url, read_json


def normalize_action(action: str) -> str:
    value = (action or "").strip().lower().replace("-", "_")
    aliases = {
        "deactivate": "deprovision",
        "deactivation": "deprovision",
        "deprovision_user": "deprovision",
        "delete_user": "delete",
        "delete_deprovisioned": "delete",
        "remove": "delete",
    }
    return aliases.get(value, value)


@dataclass
class Settings:
    default_action: str = "suspend"
    require_approved: bool = True
    approved_values: list[str] = field(default_factory=lambda: ["true", "yes", "y", "approved"])
    require_reason: bool = True
    continue_on_error: bool = False
    max_users_per_run: int = 100
    verify_users_on_dry_run: bool = False
    send_deactivation_email: bool = False
    send_deprovision_email: bool = False
    send_delete_email: bool = False
    skip_already_in_target_state: bool = True
    allow_delete_deprovisioned_users: bool = False
    require_deprovisioned_before_delete: bool = True
    request_timeout_seconds: int = 30
    max_retries: int = 3


@dataclass
class Safety:
    require_confirmation_phrase_for_apply: bool = True
    confirmation_phrase: str = "APPLY APPROVED USER LIFECYCLE ACTIONS"
    prevent_self_deactivation_login: str = ""
    blocked_login_patterns: list[str] = field(default_factory=lambda: ["admin", "breakglass", "break-glass", "service-account", "svc-"])
    blocked_user_ids: list[str] = field(default_factory=list)


@dataclass
class Columns:
    user_id: str = "id"
    login: str = "login"
    email: str = "email"
    action: str = "action"
    approved: str = "approved"
    reason: str = "reason"


@dataclass
class AppConfig:
    target_org_url: str
    api_token: str
    input_file: str
    output_dir: str = "output"
    settings: Settings = field(default_factory=Settings)
    safety: Safety = field(default_factory=Safety)
    columns: Columns = field(default_factory=Columns)


def _settings(data: dict[str, Any]) -> Settings:
    send_deactivation_email = bool(data.get("sendDeactivationEmail", False))
    return Settings(
        default_action=normalize_action(str(data.get("defaultAction", "suspend"))),
        require_approved=bool(data.get("requireApproved", True)),
        approved_values=list(data.get("approvedValues", ["true", "yes", "y", "approved"])),
        require_reason=bool(data.get("requireReason", True)),
        continue_on_error=bool(data.get("continueOnError", False)),
        max_users_per_run=int(data.get("maxUsersPerRun", 100)),
        verify_users_on_dry_run=bool(data.get("verifyUsersOnDryRun", False)),
        send_deactivation_email=send_deactivation_email,
        send_deprovision_email=bool(data.get("sendDeprovisionEmail", send_deactivation_email)),
        send_delete_email=bool(data.get("sendDeleteEmail", False)),
        skip_already_in_target_state=bool(data.get("skipAlreadyInTargetState", True)),
        allow_delete_deprovisioned_users=bool(data.get("allowDeleteDeprovisionedUsers", False)),
        require_deprovisioned_before_delete=bool(data.get("requireDeprovisionedBeforeDelete", True)),
        request_timeout_seconds=int(data.get("requestTimeoutSeconds", 30)),
        max_retries=int(data.get("maxRetries", 3)),
    )


def _safety(data: dict[str, Any]) -> Safety:
    return Safety(
        require_confirmation_phrase_for_apply=bool(data.get("requireConfirmationPhraseForApply", True)),
        confirmation_phrase=str(data.get("confirmationPhrase", "APPLY APPROVED USER LIFECYCLE ACTIONS")),
        prevent_self_deactivation_login=str(data.get("preventSelfDeactivationLogin", "")),
        blocked_login_patterns=list(data.get("blockedLoginPatterns", ["admin", "breakglass", "break-glass", "service-account", "svc-"])),
        blocked_user_ids=list(data.get("blockedUserIds", [])),
    )


def _columns(data: dict[str, Any]) -> Columns:
    return Columns(
        user_id=str(data.get("userId", "id")),
        login=str(data.get("login", "login")),
        email=str(data.get("email", "email")),
        action=str(data.get("action", "action")),
        approved=str(data.get("approved", "approved")),
        reason=str(data.get("reason", "reason")),
    )


def load_config(path: str | Path) -> AppConfig:
    load_dotenv()
    raw = read_json(path)
    target_org_url = os.getenv("OKTA_TARGET_ORG_URL") or raw.get("targetOrgUrl") or ""
    api_token = os.getenv("OKTA_API_TOKEN") or raw.get("apiToken") or ""
    target_org_url = normalize_okta_url(target_org_url)
    if not api_token:
        raise ValueError("Okta API token is required. Set OKTA_API_TOKEN in .env or environment variables.")
    settings = _settings(raw.get("settings", {}))
    if settings.default_action not in {"suspend", "deprovision", "delete"}:
        raise ValueError("settings.defaultAction must be suspend, deprovision, deactivate, or delete")
    if settings.max_users_per_run < 1:
        raise ValueError("settings.maxUsersPerRun must be at least 1")
    return AppConfig(
        target_org_url=target_org_url,
        api_token=api_token,
        input_file=str(raw.get("inputFile", "input/users-to-deprovision.csv")),
        output_dir=str(raw.get("outputDir", "output")),
        settings=settings,
        safety=_safety(raw.get("safety", {})),
        columns=_columns(raw.get("columns", {})),
    )
