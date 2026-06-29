from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
import json

from .config import DiffConfig
from .loaders import load_resource, validate_backup_dir
from .normalizers import normalize_resource_records, normalize_for_compare, index_records, natural_key


@dataclass
class ResourceDiff:
    resource: str
    baseline_count: int
    comparison_count: int
    added: list[dict[str, Any]]
    removed: list[dict[str, Any]]
    changed: list[dict[str, Any]]
    unchanged: list[dict[str, Any]]
    duplicate_keys: list[dict[str, Any]]
    warnings: list[str]
    errors: list[str]

    @property
    def has_differences(self) -> bool:
        return bool(self.added or self.removed or self.changed or self.duplicate_keys or self.errors)


def _preview(value: Any, max_chars: int) -> str:
    text = json.dumps(value, indent=2, sort_keys=True, default=str)
    if len(text) > max_chars:
        return text[:max_chars] + "..."
    return text


def _changed_paths(left: Any, right: Any, path: str = "$", max_paths: int = 25) -> list[str]:
    paths: list[str] = []

    def walk(a: Any, b: Any, p: str) -> None:
        if len(paths) >= max_paths:
            return
        if type(a) is not type(b):
            paths.append(p)
            return
        if isinstance(a, dict):
            keys = set(a) | set(b)
            for key in sorted(keys):
                if len(paths) >= max_paths:
                    return
                if key not in a or key not in b:
                    paths.append(f"{p}.{key}")
                else:
                    walk(a[key], b[key], f"{p}.{key}")
        elif isinstance(a, list):
            if len(a) != len(b):
                paths.append(f"{p}[length]")
                return
            for i, (ia, ib) in enumerate(zip(a, b)):
                if len(paths) >= max_paths:
                    return
                walk(ia, ib, f"{p}[{i}]")
        elif a != b:
            paths.append(p)

    walk(left, right, path)
    return paths


def _dup_rows(resource: str, duplicates: dict[str, list[dict[str, Any]]], side: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for key, records in sorted(duplicates.items()):
        rows.append({
            "resource": resource,
            "side": side,
            "key": key,
            "count": len(records),
            "message": f"Duplicate natural key found in {side} backup: {key}",
        })
    return rows


def diff_resource(resource: str, baseline_data: Any, comparison_data: Any, config: DiffConfig) -> ResourceDiff:
    warnings: list[str] = []
    errors: list[str] = []
    ignore_fields = set(config.ignore_fields)

    baseline_records = normalize_resource_records(resource, baseline_data)
    comparison_records = normalize_resource_records(resource, comparison_data)

    baseline_index, baseline_dupes = index_records(resource, baseline_records)
    comparison_index, comparison_dupes = index_records(resource, comparison_records)

    duplicate_rows = _dup_rows(resource, baseline_dupes, "baseline") + _dup_rows(resource, comparison_dupes, "comparison")

    added: list[dict[str, Any]] = []
    removed: list[dict[str, Any]] = []
    changed: list[dict[str, Any]] = []
    unchanged: list[dict[str, Any]] = []

    for key in sorted(set(comparison_index) - set(baseline_index)):
        added.append({
            "resource": resource,
            "key": key,
            "comparisonId": comparison_index[key].get("id"),
            "comparisonPreview": _preview(comparison_index[key], config.max_diff_preview_chars),
        })

    for key in sorted(set(baseline_index) - set(comparison_index)):
        removed.append({
            "resource": resource,
            "key": key,
            "baselineId": baseline_index[key].get("id"),
            "baselinePreview": _preview(baseline_index[key], config.max_diff_preview_chars),
        })

    for key in sorted(set(baseline_index) & set(comparison_index)):
        baseline_norm = normalize_for_compare(baseline_index[key], ignore_fields)
        comparison_norm = normalize_for_compare(comparison_index[key], ignore_fields)
        if baseline_norm == comparison_norm:
            unchanged.append({
                "resource": resource,
                "key": key,
                "baselineId": baseline_index[key].get("id"),
                "comparisonId": comparison_index[key].get("id"),
            })
        else:
            changed.append({
                "resource": resource,
                "key": key,
                "baselineId": baseline_index[key].get("id"),
                "comparisonId": comparison_index[key].get("id"),
                "changedPaths": _changed_paths(baseline_norm, comparison_norm),
                "baselinePreview": _preview(baseline_norm, config.max_diff_preview_chars),
                "comparisonPreview": _preview(comparison_norm, config.max_diff_preview_chars),
            })

    return ResourceDiff(
        resource=resource,
        baseline_count=len(baseline_records),
        comparison_count=len(comparison_records),
        added=added,
        removed=removed,
        changed=changed,
        unchanged=unchanged,
        duplicate_keys=duplicate_rows,
        warnings=warnings,
        errors=errors,
    )


def run_diff(config: DiffConfig) -> dict[str, Any]:
    validate_backup_dir(config.baseline_backup_dir, "Baseline")
    validate_backup_dir(config.comparison_backup_dir, "Comparison")

    started = datetime.now(timezone.utc)
    resource_results: dict[str, Any] = {}
    all_warnings: list[dict[str, Any]] = []
    all_errors: list[dict[str, Any]] = []

    for resource in config.include:
        baseline_data, baseline_error = load_resource(config.baseline_backup_dir, resource)
        comparison_data, comparison_error = load_resource(config.comparison_backup_dir, resource)

        warnings: list[str] = []
        errors: list[str] = []
        if baseline_error:
            warnings.append(f"Baseline {baseline_error}")
        if comparison_error:
            warnings.append(f"Comparison {comparison_error}")

        if baseline_data is None:
            baseline_data = []
        if comparison_data is None:
            comparison_data = []

        diff = diff_resource(resource, baseline_data, comparison_data, config)
        diff.warnings.extend(warnings)
        diff.errors.extend(errors)

        for warning in diff.warnings:
            all_warnings.append({"resource": resource, "message": warning})
        for error in diff.errors:
            all_errors.append({"resource": resource, "message": error})

        resource_results[resource] = {
            "baselineCount": diff.baseline_count,
            "comparisonCount": diff.comparison_count,
            "added": diff.added,
            "removed": diff.removed,
            "changed": diff.changed,
            "unchanged": diff.unchanged,
            "duplicateKeys": diff.duplicate_keys,
            "warnings": diff.warnings,
            "errors": diff.errors,
            "summary": {
                "added": len(diff.added),
                "removed": len(diff.removed),
                "changed": len(diff.changed),
                "unchanged": len(diff.unchanged),
                "duplicateKeys": len(diff.duplicate_keys),
                "warnings": len(diff.warnings),
                "errors": len(diff.errors),
            },
        }

    totals = {
        "added": sum(v["summary"]["added"] for v in resource_results.values()),
        "removed": sum(v["summary"]["removed"] for v in resource_results.values()),
        "changed": sum(v["summary"]["changed"] for v in resource_results.values()),
        "unchanged": sum(v["summary"]["unchanged"] for v in resource_results.values()),
        "duplicateKeys": sum(v["summary"]["duplicateKeys"] for v in resource_results.values()),
        "warnings": len(all_warnings),
        "errors": len(all_errors),
    }

    has_differences = bool(totals["added"] or totals["removed"] or totals["changed"] or totals["duplicateKeys"])
    status = "DIFFERENCES_FOUND" if has_differences else "NO_DIFFERENCES"
    if all_errors:
        status = "ERRORS_FOUND"
    elif config.strict_mode and (all_warnings or has_differences):
        status = "STRICT_MODE_BLOCKED"

    finished = datetime.now(timezone.utc)
    return {
        "utility": "okta-org-diff",
        "version": "0.1.0",
        "generatedAt": finished.isoformat(),
        "startedAt": started.isoformat(),
        "elapsedSeconds": round((finished - started).total_seconds(), 3),
        "baselineBackupDir": str(config.baseline_backup_dir),
        "comparisonBackupDir": str(config.comparison_backup_dir),
        "requestedResources": config.include,
        "ignoreFields": config.ignore_fields,
        "status": status,
        "hasDifferences": has_differences,
        "totals": totals,
        "resources": resource_results,
        "warnings": all_warnings,
        "errors": all_errors,
    }
