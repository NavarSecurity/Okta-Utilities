from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any

from .redact import redact_obj
from .utils import ensure_dir, slugify, utc_timestamp, write_csv, write_json

DETECTION_FIELDS = [
    "detectionId",
    "ruleId",
    "severity",
    "category",
    "published",
    "actor",
    "actorDisplayName",
    "clientIpAddress",
    "country",
    "eventType",
    "outcomeResult",
    "outcomeReason",
    "targetNames",
    "eventUuid",
    "reason",
    "evidence",
    "count",
]


def create_run_dir(base: str | Path, prefix: str) -> Path:
    return ensure_dir(Path(base) / f"{prefix}-{utc_timestamp()}")


def write_dry_run_report(config: dict[str, Any], input_exists: bool, input_event_count: int | None = None) -> Path:
    out_dir = create_run_dir(config["outputDirectory"], "security-event-dry-run")
    report = {
        "status": "DRY_RUN",
        "wouldAnalyzeInputFile": config.get("inputFile"),
        "inputFileExists": input_exists,
        "inputEventCount": input_event_count,
        "enabledDetectionRules": _enabled_rules(config),
        "outputFilesThatWouldBeCreated": [
            "security_detections.json",
            "security_detections.csv",
            "detection_summary.json",
            "severity_summary.csv",
            "rule_summary.csv",
            "actor_risk_summary.csv",
            "ip_risk_summary.csv",
            "security_event_report.md",
            "execution_report.json",
            "manifest.json",
            "detections_by_rule/",
        ],
    }
    write_json(out_dir / "dry_run_report.json", report)
    write_json(out_dir / "config_summary.json", _config_summary(config))
    write_json(out_dir / "execution_report.json", {"status": "DRY_RUN", "warnings": [], "errors": []})
    write_json(out_dir / "manifest.json", _manifest(out_dir, config, ["dry_run_report.json", "config_summary.json", "execution_report.json", "manifest.json"]))
    return out_dir


def write_detection_outputs(
    config: dict[str, Any],
    normalized_events: list[dict[str, Any]],
    filtered_events: list[dict[str, Any]],
    detections: list[dict[str, Any]],
    warnings: list[str] | None = None,
) -> Path:
    out_dir = create_run_dir(config["outputDirectory"], "security-event-detection")
    redacted = bool(config.get("redactSensitiveValues", True))
    detections_for_json = redact_obj(detections) if redacted else detections
    write_json(out_dir / "security_detections.json", detections_for_json)
    write_csv(out_dir / "security_detections.csv", detections, DETECTION_FIELDS)

    summary = build_summary(normalized_events, filtered_events, detections, warnings or [])
    write_json(out_dir / "detection_summary.json", summary)
    write_csv(out_dir / "severity_summary.csv", _counter_rows(summary["countsBySeverity"], "severity"), ["severity", "count"])
    write_csv(out_dir / "rule_summary.csv", _counter_rows(summary["countsByRule"], "ruleId"), ["ruleId", "count"])
    write_csv(out_dir / "actor_risk_summary.csv", actor_summary(detections), ["actor", "detectionCount", "highestSeverity", "ruleIds", "ipAddresses"])
    write_csv(out_dir / "ip_risk_summary.csv", ip_summary(detections), ["clientIpAddress", "detectionCount", "highestSeverity", "actors", "countries", "ruleIds"])
    write_markdown_report(out_dir / "security_event_report.md", summary, detections)

    by_rule_dir = ensure_dir(out_dir / "detections_by_rule")
    for rule_id in sorted({d["ruleId"] for d in detections}):
        rows = [d for d in detections if d["ruleId"] == rule_id]
        write_csv(by_rule_dir / f"{slugify(rule_id)}.csv", rows, DETECTION_FIELDS)

    execution_report = {
        "status": "SUCCESS" if not warnings else "SUCCESS_WITH_WARNINGS",
        "inputFile": config.get("inputFile"),
        "eventsLoaded": len(normalized_events),
        "eventsAnalyzedAfterFilters": len(filtered_events),
        "detections": len(detections),
        "highestSeverity": summary["highestSeverity"],
        "warnings": warnings or [],
        "errors": [],
    }
    write_json(out_dir / "execution_report.json", execution_report)
    files = [
        "security_detections.json",
        "security_detections.csv",
        "detection_summary.json",
        "severity_summary.csv",
        "rule_summary.csv",
        "actor_risk_summary.csv",
        "ip_risk_summary.csv",
        "security_event_report.md",
        "execution_report.json",
        "manifest.json",
        "detections_by_rule/",
    ]
    write_json(out_dir / "manifest.json", _manifest(out_dir, config, files))
    return out_dir


def build_summary(
    normalized_events: list[dict[str, Any]],
    filtered_events: list[dict[str, Any]],
    detections: list[dict[str, Any]],
    warnings: list[str],
) -> dict[str, Any]:
    severity_counts = Counter(d.get("severity", "info") for d in detections)
    rule_counts = Counter(d.get("ruleId", "UNKNOWN") for d in detections)
    actor_counts = Counter(d.get("actor", "unknown") for d in detections)
    highest = _highest([d.get("severity", "info") for d in detections])
    return {
        "eventsLoaded": len(normalized_events),
        "eventsAnalyzedAfterFilters": len(filtered_events),
        "detections": len(detections),
        "highestSeverity": highest,
        "countsBySeverity": dict(sorted(severity_counts.items())),
        "countsByRule": dict(sorted(rule_counts.items())),
        "topActors": dict(actor_counts.most_common(10)),
        "warnings": warnings,
    }


def actor_summary(detections: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for detection in detections:
        grouped.setdefault(detection.get("actor") or "unknown", []).append(detection)
    rows = []
    for actor, items in grouped.items():
        rows.append(
            {
                "actor": actor,
                "detectionCount": len(items),
                "highestSeverity": _highest([i.get("severity", "info") for i in items]),
                "ruleIds": "; ".join(sorted({i.get("ruleId", "") for i in items if i.get("ruleId")})),
                "ipAddresses": "; ".join(sorted({i.get("clientIpAddress", "") for i in items if i.get("clientIpAddress")})),
            }
        )
    return sorted(rows, key=lambda item: (-int(item["detectionCount"]), item["actor"]))


def ip_summary(detections: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for detection in detections:
        grouped.setdefault(detection.get("clientIpAddress") or "unknown", []).append(detection)
    rows = []
    for ip, items in grouped.items():
        rows.append(
            {
                "clientIpAddress": ip,
                "detectionCount": len(items),
                "highestSeverity": _highest([i.get("severity", "info") for i in items]),
                "actors": "; ".join(sorted({i.get("actor", "") for i in items if i.get("actor")})),
                "countries": "; ".join(sorted({i.get("country", "") for i in items if i.get("country")})),
                "ruleIds": "; ".join(sorted({i.get("ruleId", "") for i in items if i.get("ruleId")})),
            }
        )
    return sorted(rows, key=lambda item: (-int(item["detectionCount"]), item["clientIpAddress"]))


def write_markdown_report(path: str | Path, summary: dict[str, Any], detections: list[dict[str, Any]]) -> None:
    lines = [
        "# Okta Security Event Detection Report",
        "",
        "## Summary",
        "",
        f"- Events loaded: {summary['eventsLoaded']}",
        f"- Events analyzed after filters: {summary['eventsAnalyzedAfterFilters']}",
        f"- Detections: {summary['detections']}",
        f"- Highest severity: {summary['highestSeverity']}",
        "",
        "## Counts by Severity",
        "",
        "| Severity | Count |",
        "|---|---:|",
    ]
    for severity, count in summary["countsBySeverity"].items():
        lines.append(f"| {severity} | {count} |")
    lines.extend(["", "## Top Detections", "", "| Detection | Severity | Rule | Actor | IP | Reason |", "|---|---|---|---|---|---|"])
    for detection in detections[:25]:
        reason = str(detection.get("reason", "")).replace("|", "\\|")
        lines.append(
            f"| {detection.get('detectionId')} | {detection.get('severity')} | {detection.get('ruleId')} | "
            f"{detection.get('actor')} | {detection.get('clientIpAddress')} | {reason} |"
        )
    Path(path).write_text("\n".join(lines) + "\n", encoding="utf-8")


def _counter_rows(counter: dict[str, int], key_name: str) -> list[dict[str, Any]]:
    return [{key_name: key, "count": count} for key, count in sorted(counter.items())]


def _highest(severities: list[str]) -> str:
    order = {"info": 0, "low": 1, "medium": 2, "high": 3, "critical": 4}
    if not severities:
        return "none"
    return max(severities, key=lambda item: order.get(item, 0))


def _enabled_rules(config: dict[str, Any]) -> list[str]:
    rules = config.get("detections", {}) or {}
    return sorted([key for key, value in rules.items() if isinstance(value, dict) and value.get("enabled", True)])


def _config_summary(config: dict[str, Any]) -> dict[str, Any]:
    return {
        "inputFile": config.get("inputFile"),
        "outputDirectory": config.get("outputDirectory"),
        "includeLowSeverity": config.get("includeLowSeverity"),
        "includeInformationalFindings": config.get("includeInformationalFindings"),
        "filters": config.get("filters", {}),
        "enabledDetectionRules": _enabled_rules(config),
    }


def _manifest(out_dir: Path, config: dict[str, Any], files: list[str]) -> dict[str, Any]:
    return {
        "utility": "okta-security-event-detector",
        "createdAt": utc_timestamp(),
        "outputDirectory": str(out_dir),
        "inputFile": config.get("inputFile"),
        "files": files,
    }
