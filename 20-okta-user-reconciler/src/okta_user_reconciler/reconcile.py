from __future__ import annotations

from collections import defaultdict
from typing import Any

from .config import ReconcileConfig


def normalize_value(value: Any, *, trim: bool, lower: bool) -> str:
    if value is None:
        text = ""
    else:
        text = str(value)
    if trim:
        text = text.strip()
    if lower:
        text = text.lower()
    return text


def get_value(row: dict[str, Any], field: str) -> Any:
    if field in row:
        return row.get(field)
    # Support rows where nested profile fields were flattened differently.
    if field.startswith("profile."):
        alt = field.replace("profile.", "", 1)
        return row.get(alt, "")
    return row.get(field, "")


def build_match_key(row: dict[str, Any], config: ReconcileConfig) -> tuple[str, str]:
    fields = [config.match_rules.primary_match_field] + list(config.match_rules.fallback_match_fields)
    for field in fields:
        raw = get_value(row, field)
        normalized = normalize_value(
            raw,
            trim=config.match_rules.trim_whitespace,
            lower=config.match_rules.case_insensitive,
        )
        if normalized:
            return normalized, field
    return "", ""


def index_users(rows: list[dict[str, Any]], config: ReconcileConfig, side: str) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    grouped: dict[str, list[tuple[dict[str, Any], str]]] = defaultdict(list)
    missing: list[dict[str, Any]] = []
    for row in rows:
        key, field = build_match_key(row, config)
        if not key:
            missing.append({
                "side": side,
                "row_number": row.get("__row_number", ""),
                "reason": "No match key found",
            })
            continue
        grouped[key].append((row, field))

    index: dict[str, dict[str, Any]] = {}
    duplicates: list[dict[str, Any]] = []
    for key, values in grouped.items():
        if len(values) > 1:
            for row, field in values:
                duplicates.append({
                    "side": side,
                    "match_key": key,
                    "match_field": field,
                    "row_number": row.get("__row_number", ""),
                    "login": get_value(row, "login") or get_value(row, "profile.login"),
                    "email": get_value(row, "email") or get_value(row, "profile.email"),
                    "firstName": get_value(row, "firstName") or get_value(row, "profile.firstName"),
                    "lastName": get_value(row, "lastName") or get_value(row, "profile.lastName"),
                })
        # Keep first row for reconciliation; duplicate report tells user to review.
        index[key] = values[0][0]
        index[key]["__match_field"] = values[0][1]
    return index, duplicates, missing


def values_differ(source_value: Any, target_value: Any, config: ReconcileConfig) -> bool:
    source_norm = normalize_value(source_value, trim=True, lower=False)
    target_norm = normalize_value(target_value, trim=True, lower=False)
    if config.settings.ignore_blank_source_values and not source_norm:
        return False
    if config.settings.ignore_blank_target_values and not target_norm:
        return False
    return source_norm != target_norm


def reconcile_users(source_rows: list[dict[str, Any]], target_rows: list[dict[str, Any]], config: ReconcileConfig) -> dict[str, Any]:
    source_index, source_dupes, source_missing_keys = index_users(source_rows, config, "source")
    target_index, target_dupes, target_missing_keys = index_users(target_rows, config, "target")

    source_keys = set(source_index)
    target_keys = set(target_index)
    common_keys = sorted(source_keys & target_keys)
    source_only_keys = sorted(source_keys - target_keys)
    target_only_keys = sorted(target_keys - source_keys)

    matched: list[dict[str, Any]] = []
    material_diffs: list[dict[str, Any]] = []

    ignored = set(config.settings.ignored_fields)
    compare_fields = [f for f in config.profile_fields_to_compare if f not in ignored]

    for key in common_keys:
        s = source_index[key]
        t = target_index[key]
        diff_count = 0
        for field in compare_fields:
            source_value = get_value(s, field)
            target_value = get_value(t, field)
            if values_differ(source_value, target_value, config):
                diff_count += 1
                material_diffs.append({
                    "match_key": key,
                    "match_field": s.get("__match_field", ""),
                    "field": field,
                    "source_value": source_value,
                    "target_value": target_value,
                    "source_login": get_value(s, "login") or get_value(s, "profile.login"),
                    "target_login": get_value(t, "login") or get_value(t, "profile.login"),
                    "source_email": get_value(s, "email") or get_value(s, "profile.email"),
                    "target_email": get_value(t, "email") or get_value(t, "profile.email"),
                })
        matched.append({
            "match_key": key,
            "match_field": s.get("__match_field", ""),
            "source_login": get_value(s, "login") or get_value(s, "profile.login"),
            "target_login": get_value(t, "login") or get_value(t, "profile.login"),
            "source_email": get_value(s, "email") or get_value(s, "profile.email"),
            "target_email": get_value(t, "email") or get_value(t, "profile.email"),
            "material_difference_count": diff_count,
            "status": "DIFFERENT" if diff_count else "MATCHED",
        })

    def side_only_row(key: str, row: dict[str, Any], side: str) -> dict[str, Any]:
        return {
            "match_key": key,
            "side": side,
            "login": get_value(row, "login") or get_value(row, "profile.login"),
            "email": get_value(row, "email") or get_value(row, "profile.email"),
            "firstName": get_value(row, "firstName") or get_value(row, "profile.firstName"),
            "lastName": get_value(row, "lastName") or get_value(row, "profile.lastName"),
            "status": get_value(row, "status"),
        }

    source_only = [side_only_row(k, source_index[k], "source") for k in source_only_keys]
    target_only = [side_only_row(k, target_index[k], "target") for k in target_only_keys]
    duplicates = source_dupes + target_dupes + source_missing_keys + target_missing_keys

    summary = {
        "sourceUserCount": len(source_rows),
        "targetUserCount": len(target_rows),
        "matchedUserCount": len(matched),
        "matchedWithoutDifferences": sum(1 for row in matched if row["status"] == "MATCHED"),
        "matchedWithMaterialDifferences": sum(1 for row in matched if row["status"] == "DIFFERENT"),
        "materialDifferenceCount": len(material_diffs),
        "sourceOnlyUserCount": len(source_only),
        "targetOnlyUserCount": len(target_only),
        "duplicateOrMissingKeyCount": len(duplicates),
    }

    return {
        "summary": summary,
        "matchedUsers": matched,
        "sourceOnlyUsers": source_only,
        "targetOnlyUsers": target_only,
        "materialDifferences": material_diffs,
        "duplicateUsers": duplicates,
    }
