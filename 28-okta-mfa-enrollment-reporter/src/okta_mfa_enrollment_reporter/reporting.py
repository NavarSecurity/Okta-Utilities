from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from .config import AppConfig
from .redaction import maybe_redact


def user_profile(user: dict[str, Any]) -> dict[str, Any]:
    return user.get("profile") or {}


def user_login(user: dict[str, Any]) -> str:
    profile = user_profile(user)
    return profile.get("login") or user.get("login") or ""


def user_email(user: dict[str, Any]) -> str:
    profile = user_profile(user)
    return profile.get("email") or user.get("email") or ""


def factor_type(factor: dict[str, Any]) -> str:
    return str(factor.get("factorType") or "")


def is_factor_active(factor: dict[str, Any]) -> bool:
    return str(factor.get("status") or "").upper() in {"ACTIVE", "ENROLLED", "VERIFIED"}


def build_user_summary_rows(
    users: list[dict[str, Any]],
    factor_map: dict[str, list[dict[str, Any]]],
    group_context: dict[str, list[dict[str, str]]],
    required_factor_types: list[str],
) -> list[dict[str, Any]]:
    required_set = set(required_factor_types)
    rows: list[dict[str, Any]] = []
    for user in users:
        user_id = user.get("id", "")
        factors = factor_map.get(user_id, [])
        all_types = sorted({factor_type(f) for f in factors if factor_type(f)})
        active_types = sorted({factor_type(f) for f in factors if factor_type(f) and is_factor_active(f)})
        missing_required = sorted(required_set - set(all_types)) if required_set else []
        groups = group_context.get(user_id, [])
        rows.append({
            "user_id": user_id,
            "login": user_login(user),
            "email": user_email(user),
            "status": user.get("status", ""),
            "group_ids": ";".join(sorted({g.get("id", "") for g in groups if g.get("id")})),
            "group_names": ";".join(sorted({g.get("name", "") for g in groups if g.get("name")})),
            "factor_count": len(factors),
            "active_factor_count": sum(1 for f in factors if is_factor_active(f)),
            "factor_types": ";".join(all_types),
            "active_factor_types": ";".join(active_types),
            "has_any_factor": str(bool(factors)).lower(),
            "has_active_factor": str(bool(active_types)).lower(),
            "missing_required_factor_types": ";".join(missing_required),
            "factor_fetch_status": "ok",
        })
    return rows


def build_factor_rows(
    users: list[dict[str, Any]],
    factor_map: dict[str, list[dict[str, Any]]],
    cfg: AppConfig,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    include_types = set(cfg.reporting.factor_types)
    for user in users:
        user_id = user.get("id", "")
        for factor in factor_map.get(user_id, []):
            ftype = factor_type(factor)
            if include_types and ftype not in include_types:
                continue
            profile = maybe_redact(factor.get("profile") or {}, cfg.settings.redact_sensitive_profile_values)
            row = {
                "user_id": user_id,
                "login": user_login(user),
                "email": user_email(user),
                "user_status": user.get("status", ""),
                "factor_id": factor.get("id", ""),
                "factor_type": ftype,
                "provider": factor.get("provider", ""),
                "status": factor.get("status", ""),
                "created": factor.get("created", ""),
                "last_updated": factor.get("lastUpdated", ""),
            }
            if cfg.reporting.include_factor_profile:
                row["factor_profile_json"] = json.dumps(profile, sort_keys=True)
            rows.append(row)
    return rows


def build_group_summary_rows(user_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    group_users: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in user_rows:
        group_ids = [x for x in str(row.get("group_ids", "")).split(";") if x]
        group_names = [x for x in str(row.get("group_names", "")).split(";") if x]
        for idx, group_id in enumerate(group_ids):
            name = group_names[idx] if idx < len(group_names) else ""
            group_users[(group_id, name)].append(row)
    out: list[dict[str, Any]] = []
    for (group_id, group_name), rows in sorted(group_users.items(), key=lambda x: (x[0][1], x[0][0])):
        total = len(rows)
        with_any = sum(1 for r in rows if r.get("has_any_factor") == "true")
        with_active = sum(1 for r in rows if r.get("has_active_factor") == "true")
        out.append({
            "group_id": group_id,
            "group_name": group_name,
            "total_users": total,
            "users_with_any_factor": with_any,
            "users_with_active_factor": with_active,
            "users_without_factor": total - with_any,
            "coverage_percent": round((with_any / total * 100), 2) if total else 0,
        })
    return out


def build_factor_summary_rows(factor_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    counts = Counter((row.get("factor_type", ""), row.get("provider", ""), row.get("status", "")) for row in factor_rows)
    return [
        {"factor_type": factor_type, "provider": provider, "status": status, "count": count}
        for (factor_type, provider, status), count in sorted(counts.items())
    ]


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str] | None = None) -> None:
    if fieldnames is None:
        keys: list[str] = []
        for row in rows:
            for key in row.keys():
                if key not in keys:
                    keys.append(key)
        fieldnames = keys
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_json(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")


def write_execution_report(path: Path, title: str, mode: str, result: dict[str, Any]) -> None:
    lines = [
        f"# {title}",
        "",
        f"Mode: `{mode}`",
        "",
        "## Summary",
        "",
    ]
    for key, value in result.get("summary", {}).items():
        lines.append(f"- {key}: {value}")
    if result.get("warnings"):
        lines.extend(["", "## Warnings", ""])
        for warning in result["warnings"]:
            lines.append(f"- {warning}")
    if result.get("errors"):
        lines.extend(["", "## Errors", ""])
        for error in result["errors"]:
            lines.append(f"- {error}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
