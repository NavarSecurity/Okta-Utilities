from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from dotenv import load_dotenv


class ConfigError(ValueError):
    pass


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def iso_z(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def parse_iso_datetime(value: str) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise ConfigError("Date values must be non-empty ISO 8601 strings.")
    normalized = value.strip().replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise ConfigError(f"Invalid ISO 8601 datetime: {value}") from exc
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def as_list(value: Any, field_name: str) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise ConfigError(f"{field_name} must be a list.")
    for item in value:
        if not isinstance(item, str):
            raise ConfigError(f"{field_name} must contain only strings.")
    return [item.strip() for item in value if item.strip()]


@dataclass
class ExportConfig:
    output_directory: str = "output"
    relative_hours: int | None = 24
    since: str | None = None
    until: str | None = None
    limit: int = 1000
    max_events: int = 5000
    sort_order: str = "ASCENDING"
    filter: str | None = None
    q: str | None = None
    event_types: list[str] = field(default_factory=list)
    actor_ids: list[str] = field(default_factory=list)
    actor_logins: list[str] = field(default_factory=list)
    target_ids: list[str] = field(default_factory=list)
    target_types: list[str] = field(default_factory=list)
    outcomes: list[str] = field(default_factory=list)
    include_raw_events: bool = True
    write_events_by_type: bool = True
    redact_sensitive_values: bool = True
    timeout_seconds: int = 30

    @property
    def resolved_since(self) -> str:
        if self.since:
            return iso_z(parse_iso_datetime(self.since))
        hours = self.relative_hours if self.relative_hours is not None else 24
        return iso_z(utc_now() - timedelta(hours=hours))

    @property
    def resolved_until(self) -> str | None:
        if self.until:
            return iso_z(parse_iso_datetime(self.until))
        return None


def load_config(config_path: str | Path) -> ExportConfig:
    path = Path(config_path)
    if not path.exists():
        raise ConfigError(f"Config file not found: {path}")
    with path.open("r", encoding="utf-8") as handle:
        raw = json.load(handle)
    if not isinstance(raw, dict):
        raise ConfigError("Config file must contain a JSON object.")

    cfg = ExportConfig(
        output_directory=str(raw.get("outputDirectory", "output")),
        relative_hours=raw.get("relativeHours", 24),
        since=raw.get("since"),
        until=raw.get("until"),
        limit=int(raw.get("limit", 1000)),
        max_events=int(raw.get("maxEvents", 5000)),
        sort_order=str(raw.get("sortOrder", "ASCENDING")).upper(),
        filter=raw.get("filter"),
        q=raw.get("q"),
        event_types=as_list(raw.get("eventTypes", []), "eventTypes"),
        actor_ids=as_list(raw.get("actorIds", []), "actorIds"),
        actor_logins=as_list(raw.get("actorLogins", []), "actorLogins"),
        target_ids=as_list(raw.get("targetIds", []), "targetIds"),
        target_types=as_list(raw.get("targetTypes", []), "targetTypes"),
        outcomes=as_list(raw.get("outcomes", []), "outcomes"),
        include_raw_events=bool(raw.get("includeRawEvents", True)),
        write_events_by_type=bool(raw.get("writeEventsByType", True)),
        redact_sensitive_values=bool(raw.get("redactSensitiveValues", True)),
        timeout_seconds=int(raw.get("timeoutSeconds", 30)),
    )
    validate_config(cfg)
    return cfg


def validate_config(cfg: ExportConfig) -> None:
    if cfg.relative_hours is not None and int(cfg.relative_hours) <= 0:
        raise ConfigError("relativeHours must be greater than 0 when provided.")
    if cfg.since and cfg.until and parse_iso_datetime(cfg.since) >= parse_iso_datetime(cfg.until):
        raise ConfigError("since must be earlier than until.")
    if not 1 <= cfg.limit <= 1000:
        raise ConfigError("limit must be between 1 and 1000.")
    if cfg.max_events <= 0:
        raise ConfigError("maxEvents must be greater than 0.")
    if cfg.sort_order not in {"ASCENDING", "DESCENDING"}:
        raise ConfigError("sortOrder must be ASCENDING or DESCENDING.")
    if cfg.filter is not None and not isinstance(cfg.filter, str):
        raise ConfigError("filter must be a string or null.")
    if cfg.q is not None and not isinstance(cfg.q, str):
        raise ConfigError("q must be a string or null.")
    if cfg.timeout_seconds <= 0:
        raise ConfigError("timeoutSeconds must be greater than 0.")


def load_env() -> tuple[str, str]:
    load_dotenv()
    org_url = os.getenv("OKTA_ORG_URL", "").strip().rstrip("/")
    token = os.getenv("OKTA_API_TOKEN", "").strip()
    if not org_url:
        raise ConfigError("OKTA_ORG_URL is required in .env or environment variables.")
    if not token:
        raise ConfigError("OKTA_API_TOKEN is required in .env or environment variables.")
    if org_url.endswith("/api/v1"):
        raise ConfigError("OKTA_ORG_URL should be the org root URL, not a /api/v1 URL.")
    return org_url, token


def config_summary(cfg: ExportConfig) -> dict[str, Any]:
    return {
        "outputDirectory": cfg.output_directory,
        "relativeHours": cfg.relative_hours,
        "since": cfg.resolved_since,
        "until": cfg.resolved_until,
        "limit": cfg.limit,
        "maxEvents": cfg.max_events,
        "sortOrder": cfg.sort_order,
        "filterProvided": bool(cfg.filter),
        "qProvided": bool(cfg.q),
        "eventTypes": cfg.event_types,
        "actorIds": cfg.actor_ids,
        "actorLogins": cfg.actor_logins,
        "targetIds": cfg.target_ids,
        "targetTypes": cfg.target_types,
        "outcomes": cfg.outcomes,
        "includeRawEvents": cfg.include_raw_events,
        "writeEventsByType": cfg.write_events_by_type,
        "redactSensitiveValues": cfg.redact_sensitive_values,
        "timeoutSeconds": cfg.timeout_seconds,
    }
