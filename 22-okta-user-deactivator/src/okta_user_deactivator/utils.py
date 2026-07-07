from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def utc_timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def read_json(path: str | Path) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"Expected JSON object in {path}")
    return data


def write_json(path: str | Path, data: Any) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2, sort_keys=True, default=str)
        handle.write("\n")


def normalize_okta_url(url: str) -> str:
    value = (url or "").strip().rstrip("/")
    if not value:
        raise ValueError("Okta org URL is required")
    if not value.startswith("https://"):
        raise ValueError("Okta org URL must start with https://")
    lowered = value.lower()
    if "-admin.okta.com" in lowered or "-admin.oktapreview.com" in lowered:
        raise ValueError("Use the normal Okta org URL, not the -admin Admin Console URL")
    forbidden_path_patterns = ["/admin", "/api/v1", "/oauth2", "/login"]
    for pattern in forbidden_path_patterns:
        if pattern in lowered.replace("https://", ""):
            raise ValueError("Okta org URL must be the base org URL only, such as https://your-org.okta.com")
    return value


def safe_slug(value: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9_.-]+", "-", value.strip())
    return slug.strip("-") or "value"


def truthy(value: Any, approved_values: list[str] | None = None) -> bool:
    if isinstance(value, bool):
        return value
    values = approved_values or ["true", "yes", "y", "approved"]
    return str(value or "").strip().lower() in {v.lower() for v in values}


def redact(value: Any) -> str:
    if value is None:
        return ""
    s = str(value)
    if not s:
        return ""
    if len(s) <= 8:
        return "[REDACTED]"
    return f"{s[:4]}...[REDACTED]...{s[-4:]}"
