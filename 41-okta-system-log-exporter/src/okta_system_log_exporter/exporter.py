from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Any

from .config import ExportConfig, config_summary
from .filters import build_filter, build_query_params
from .normalize import (
    actor_summary,
    event_type_summary,
    normalize_events,
    outcome_summary,
    safe_filename,
    target_summary,
)
from .okta_client import OktaClient
from .redact import redact_event
from .reports import create_run_dir, make_manifest, write_csv, write_json

EVENT_CSV_FIELDS = [
    "uuid",
    "published",
    "eventType",
    "displayMessage",
    "severity",
    "actorId",
    "actorType",
    "actorAlternateId",
    "actorDisplayName",
    "clientIpAddress",
    "clientCountry",
    "clientState",
    "clientCity",
    "outcomeResult",
    "outcomeReason",
    "transactionId",
    "requestId",
    "targetCount",
    "targets",
]


def dry_run(config_path: str, cfg: ExportConfig) -> Path:
    run_dir = create_run_dir(cfg.output_directory, "system-log-dry-run")
    params = build_query_params(cfg)
    generated_filter = build_filter(cfg)
    warnings: list[str] = []
    if cfg.max_events < cfg.limit:
        warnings.append("maxEvents is lower than limit; the export will stop before a full first page can be retained.")
    dry_run_report = {
        "mode": "dry-run",
        "wouldCallOkta": False,
        "endpoint": "/api/v1/logs",
        "queryParams": params,
        "generatedFilter": generated_filter,
        "notes": [
            "Dry run validates configuration and writes planned query parameters.",
            "No HTTP request is sent to Okta during dry run.",
        ],
    }
    output_files = []
    write_json(run_dir / "dry_run_report.json", dry_run_report)
    output_files.append("dry_run_report.json")
    write_json(run_dir / "config_summary.json", config_summary(cfg))
    output_files.append("config_summary.json")
    execution_report = {
        "status": "DRY_RUN",
        "eventsExported": 0,
        "pagesFetched": 0,
        "warnings": warnings,
        "errors": [],
    }
    write_json(run_dir / "execution_report.json", execution_report)
    output_files.append("execution_report.json")
    manifest = make_manifest(
        operation="dry-run",
        config_path=config_path,
        output_files=output_files,
        warnings=warnings,
        errors=[],
    )
    write_json(run_dir / "manifest.json", manifest)
    return run_dir


def export_logs(config_path: str, cfg: ExportConfig, client: OktaClient) -> Path:
    run_dir = create_run_dir(cfg.output_directory, "system-log-export")
    params = build_query_params(cfg)
    events: list[dict[str, Any]] = []
    request_urls: list[str] = []
    warnings: list[str] = []
    errors: list[str] = []
    page_count = 0
    next_url: str | None = None

    while len(events) < cfg.max_events:
        page = client.list_logs_page(params=params, next_url=next_url)
        page_count += 1
        request_urls.append(page.request_url)
        if not page.events:
            break
        remaining = cfg.max_events - len(events)
        events.extend(page.events[:remaining])
        if len(page.events) > remaining:
            warnings.append("maxEvents reached before all returned events were retained.")
            break
        if not page.next_url:
            break
        next_url = page.next_url

    if len(events) >= cfg.max_events:
        warnings.append("maxEvents limit reached. Export may be incomplete for the selected time range or filter.")

    if cfg.redact_sensitive_values:
        output_events = [redact_event(event) for event in events]
    else:
        output_events = events

    normalized = normalize_events(output_events)
    output_files: list[str] = []

    if cfg.include_raw_events:
        write_json(run_dir / "system_log_events_full.json", output_events)
        output_files.append("system_log_events_full.json")

    write_csv(run_dir / "system_log_events.csv", normalized, EVENT_CSV_FIELDS)
    output_files.append("system_log_events.csv")

    write_csv(run_dir / "event_type_summary.csv", event_type_summary(output_events), ["eventType", "count"])
    output_files.append("event_type_summary.csv")

    write_csv(
        run_dir / "actor_summary.csv",
        actor_summary(output_events),
        ["actorId", "actorAlternateId", "actorDisplayName", "actorType", "count"],
    )
    output_files.append("actor_summary.csv")

    write_csv(
        run_dir / "target_summary.csv",
        target_summary(output_events),
        ["targetId", "targetAlternateId", "targetDisplayName", "targetType", "count"],
    )
    output_files.append("target_summary.csv")

    write_csv(run_dir / "outcome_summary.csv", outcome_summary(output_events), ["outcomeResult", "count"])
    output_files.append("outcome_summary.csv")

    if cfg.write_events_by_type:
        by_type: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for event in output_events:
            by_type[str(event.get("eventType") or "unknown")].append(event)
        events_by_type_dir = run_dir / "events_by_type"
        events_by_type_dir.mkdir(exist_ok=True)
        for event_type, event_group in by_type.items():
            file_name = f"{safe_filename(event_type)}.json"
            write_json(events_by_type_dir / file_name, event_group)
        output_files.append("events_by_type/")

    execution_report = {
        "status": "SUCCESS" if not errors else "COMPLETED_WITH_FAILURES",
        "eventsExported": len(events),
        "pagesFetched": page_count,
        "maxEvents": cfg.max_events,
        "limit": cfg.limit,
        "queryParams": params,
        "requestUrls": request_urls,
        "warnings": warnings,
        "errors": errors,
    }
    write_json(run_dir / "execution_report.json", execution_report)
    output_files.append("execution_report.json")

    manifest = make_manifest(
        operation="export",
        config_path=config_path,
        output_files=output_files,
        warnings=warnings,
        errors=errors,
    )
    write_json(run_dir / "manifest.json", manifest)
    return run_dir
