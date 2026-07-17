from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from .config import ConfigError, get_okta_env, load_config
from .exporter import run_monitor
from .okta_client import OktaClient
from .reports import create_output_dir, severity_counts, utc_timestamp, write_csv, write_json, write_markdown


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Monitor Okta API rate-limit risk.")
    parser.add_argument("--config", default="config.json", help="Path to config JSON file.")
    parser.add_argument("--dry-run", action="store_true", help="Validate configuration and write a dry-run report without calling Okta.")
    return parser


def write_dry_run(config_path: str, config: Any) -> Path:
    output_dir = create_output_dir(config.output_directory, "rate-limit-monitor-dry-run")
    config_summary = {
        "configPath": config_path,
        "includeHeaderProbes": config.include_header_probes,
        "includeSystemLogEvents": config.include_system_log_events,
        "includePlannedOperationEstimate": config.include_planned_operation_estimate,
        "lookbackHours": config.lookback_hours,
        "probeEndpointCount": len(config.probe_endpoints),
        "systemLogFilterCount": len(config.system_log_filters),
        "plannedOperationCount": len(config.planned_operations),
        "outputDirectory": config.output_directory,
    }
    execution_report = {
        "timestamp": utc_timestamp(),
        "status": "DRY_RUN_SUCCESS",
        "message": "Configuration loaded successfully. No Okta API calls were made.",
        **config_summary,
    }
    write_json(output_dir / "dry_run_report.json", execution_report)
    write_json(output_dir / "config_summary.json", config_summary)
    write_json(output_dir / "execution_report.json", execution_report)
    write_json(output_dir / "manifest.json", {
        "utility": "okta-rate-limit-monitor",
        "mode": "dry-run",
        "configPath": config_path,
        "files": [
            "dry_run_report.json",
            "config_summary.json",
            "execution_report.json",
            "manifest.json",
        ],
    })
    return output_dir


def write_results(config_path: str, config: Any, result: dict[str, Any]) -> Path:
    output_dir = create_output_dir(config.output_directory, "rate-limit-monitor")
    header_probes = result.get("headerProbes", [])
    system_log_events = result.get("systemLogEvents", [])
    planned_estimates = result.get("plannedOperationEstimates", [])
    findings = result.get("riskFindings", [])
    failures = result.get("requestFailures", [])
    event_counts = result.get("systemLogEventCounts", {})

    write_json(output_dir / "rate_limit_headers.json", header_probes)
    write_csv(output_dir / "rate_limit_headers.csv", header_probes, [
        "name", "method", "path", "statusCode", "rateLimitLimit", "rateLimitRemaining", "rateLimitResetEpoch", "rateLimitResetUtc", "remainingPercent"
    ])
    write_json(output_dir / "system_log_rate_limit_events.json", system_log_events)
    write_csv(output_dir / "system_log_rate_limit_events.csv", system_log_events, [
        "uuid", "published", "eventType", "displayMessage", "severity", "actorId", "actorAlternateId", "actorDisplayName", "actorType", "clientIp", "userAgent", "requestUri", "outcomeResult", "outcomeReason"
    ])
    write_json(output_dir / "system_log_event_counts.json", event_counts)
    write_json(output_dir / "planned_operation_estimates.json", planned_estimates)
    write_csv(output_dir / "planned_operation_estimates.csv", planned_estimates, [
        "name", "endpoint", "estimatedRequests", "windowMinutes", "estimatedRequestsPerMinute", "matchedRateLimit", "estimatedUsagePercent"
    ])
    write_json(output_dir / "rate_limit_findings.json", findings)
    write_csv(output_dir / "rate_limit_findings.csv", findings, [
        "severity", "category", "objectName", "endpoint", "message"
    ])
    write_json(output_dir / "request_failures.json", failures)
    write_csv(output_dir / "request_failures.csv", failures, ["endpoint", "status_code", "message", "context"])

    execution_report = {
        "timestamp": utc_timestamp(),
        "status": "SUCCESS" if not failures else "SUCCESS_WITH_WARNINGS",
        "configPath": config_path,
        "headerProbes": len(header_probes),
        "systemLogEvents": len(system_log_events),
        "plannedOperations": len(planned_estimates),
        "riskFindings": len(findings),
        "findingCounts": severity_counts(findings),
        "requestFailures": len(failures),
        "outputDirectory": str(output_dir),
    }
    write_json(output_dir / "execution_report.json", execution_report)
    write_markdown(output_dir / "rate_limit_monitor_report.md", execution_report)
    write_json(output_dir / "manifest.json", {
        "utility": "okta-rate-limit-monitor",
        "mode": "export",
        "configPath": config_path,
        "files": sorted([path.name for path in output_dir.iterdir() if path.is_file()]),
    })
    return output_dir


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        config = load_config(args.config)
        if args.dry_run:
            output_dir = write_dry_run(args.config, config)
            print(f"Dry-run completed successfully. Output written to: {output_dir}")
            return 0

        org_url, api_token = get_okta_env()
        client = OktaClient(org_url=org_url, api_token=api_token, timeout_seconds=config.timeout_seconds)
        result = run_monitor(client, config)
        output_dir = write_results(args.config, config, result)
        print(f"Rate-limit monitor completed. Output written to: {output_dir}")
        return 0
    except ConfigError as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        return 2
    except Exception as exc:
        print(f"Execution failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
