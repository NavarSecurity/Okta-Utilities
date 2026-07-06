from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
import json
import os
from urllib.parse import urlparse

from dotenv import load_dotenv


DEFAULT_PROFILE_FIELD_MAP = {
    "login": "login",
    "email": "email",
    "firstName": "firstName",
    "lastName": "lastName",
    "displayName": "displayName",
    "primaryPhone": "primaryPhone",
    "mobilePhone": "mobilePhone",
    "department": "department",
    "title": "title",
    "employeeNumber": "employeeNumber",
}


@dataclass
class ImportSettings:
    skipExisting: bool = True
    updateExisting: bool = False
    activateUsers: bool = False
    continueOnError: bool = True
    performDuplicateCheckInDryRun: bool = True
    allowPasswordImport: bool = False
    assignGroups: bool = False
    requestTimeoutSeconds: int = 30
    maxRetries: int = 3
    rateLimitSleepSeconds: int = 5


@dataclass
class UserImportConfig:
    targetOrgUrl: str
    apiToken: str
    inputUserCsv: str = "input/users.csv"
    profileFieldMap: dict[str, str] = field(default_factory=lambda: DEFAULT_PROFILE_FIELD_MAP.copy())
    requiredProfileFields: list[str] = field(default_factory=lambda: ["login", "email", "firstName", "lastName"])
    duplicateLookupField: str = "login"
    defaultGroupIds: list[str] = field(default_factory=list)
    perRowGroupIdsColumn: str = "groupIds"
    passwordColumn: str = "password"
    settings: ImportSettings = field(default_factory=ImportSettings)


def _normalize_org_url(url: str) -> str:
    value = (url or "").strip().rstrip("/")
    if not value:
        raise ValueError("targetOrgUrl is required. Set it in config or OKTA_TARGET_ORG_URL.")
    parsed = urlparse(value)
    if parsed.scheme != "https" or not parsed.netloc:
        raise ValueError("targetOrgUrl must be a full HTTPS URL, for example https://your-org.okta.com")
    host = parsed.netloc.lower()
    if "-admin.okta" in host or "-admin.oktapreview" in host or host.endswith(".admin.okta.com"):
        raise ValueError("Use the normal Okta org URL, not the Admin Console URL with -admin.")
    if parsed.path and parsed.path not in ("", "/"):
        raise ValueError("targetOrgUrl must not include /admin, /api/v1, /oauth2, or other path segments.")
    return value


def _read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def load_config(config_path: str | Path) -> UserImportConfig:
    load_dotenv()
    path = Path(config_path)
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")

    raw = _read_json(path)
    target_org_url = os.getenv("OKTA_TARGET_ORG_URL") or raw.get("targetOrgUrl", "")
    api_token = os.getenv("OKTA_API_TOKEN") or raw.get("apiToken", "")
    target_org_url = _normalize_org_url(target_org_url)
    if not api_token:
        raise ValueError("Okta API token is required. Set OKTA_API_TOKEN in .env.")

    settings_raw = raw.get("settings", {}) or {}
    settings = ImportSettings(**{k: v for k, v in settings_raw.items() if k in ImportSettings.__annotations__})

    profile_map = DEFAULT_PROFILE_FIELD_MAP.copy()
    profile_map.update(raw.get("profileFieldMap", {}) or {})

    cfg = UserImportConfig(
        targetOrgUrl=target_org_url,
        apiToken=api_token,
        inputUserCsv=raw.get("inputUserCsv", "input/users.csv"),
        profileFieldMap=profile_map,
        requiredProfileFields=raw.get("requiredProfileFields", ["login", "email", "firstName", "lastName"]),
        duplicateLookupField=raw.get("duplicateLookupField", "login"),
        defaultGroupIds=raw.get("defaultGroupIds", []) or [],
        perRowGroupIdsColumn=raw.get("perRowGroupIdsColumn", "groupIds"),
        passwordColumn=raw.get("passwordColumn", "password"),
        settings=settings,
    )
    validate_config(cfg)
    return cfg


def validate_config(cfg: UserImportConfig) -> None:
    if cfg.duplicateLookupField not in ("login", "email"):
        raise ValueError("duplicateLookupField must be login or email")
    if cfg.settings.skipExisting is False and cfg.settings.updateExisting is False:
        raise ValueError("Unsafe config: skipExisting=false and updateExisting=false would duplicate users. Enable skipExisting or updateExisting.")
    if cfg.settings.activateUsers and cfg.settings.allowPasswordImport:
        # This combination is supported by Okta, but it is risky for a starter importer because it can activate real accounts.
        raise ValueError("Unsafe config: activateUsers=true with allowPasswordImport=true is blocked. Use staged import first.")


def public_config(cfg: UserImportConfig) -> dict[str, Any]:
    return {
        "targetOrgUrl": cfg.targetOrgUrl,
        "inputUserCsv": cfg.inputUserCsv,
        "profileFieldMap": cfg.profileFieldMap,
        "requiredProfileFields": cfg.requiredProfileFields,
        "duplicateLookupField": cfg.duplicateLookupField,
        "defaultGroupIds": cfg.defaultGroupIds,
        "perRowGroupIdsColumn": cfg.perRowGroupIdsColumn,
        "settings": cfg.settings.__dict__,
    }
