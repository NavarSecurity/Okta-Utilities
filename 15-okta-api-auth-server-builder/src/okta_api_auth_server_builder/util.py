from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List


def utc_timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def normalize_org_url(url: str) -> str:
    if not url:
        raise ValueError("targetOrgUrl is required. Provide it in config or OKTA_TARGET_ORG_URL.")
    clean = url.strip().rstrip("/")
    clean = re.sub(r"/admin.*$", "", clean)
    clean = re.sub(r"/api/v1.*$", "", clean)
    clean = re.sub(r"/oauth2.*$", "", clean)
    lowered = clean.lower()
    if "-admin.okta.com" in lowered or "-admin.oktapreview.com" in lowered or "-admin.okta-emea.com" in lowered:
        raise ValueError(
            "Use the normal Okta org URL, not the Admin Console URL. "
            "Example: https://your-org.okta.com"
        )
    if not lowered.startswith("https://"):
        raise ValueError("targetOrgUrl must start with https://")
    return clean


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def write_json(path: Path, data: Any) -> None:
    ensure_dir(path.parent)
    path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def safe_get(obj: Dict[str, Any], *keys: str, default: Any = None) -> Any:
    current: Any = obj
    for key in keys:
        if not isinstance(current, dict) or key not in current:
            return default
        current = current[key]
    return current


def rows_to_csv(path: Path, rows: Iterable[Dict[str, Any]], fieldnames: List[str]) -> None:
    import csv

    ensure_dir(path.parent)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def redact_headers(headers: Dict[str, str]) -> Dict[str, str]:
    redacted = dict(headers)
    for key in list(redacted.keys()):
        if key.lower() == "authorization":
            redacted[key] = "[REDACTED]"
    return redacted
