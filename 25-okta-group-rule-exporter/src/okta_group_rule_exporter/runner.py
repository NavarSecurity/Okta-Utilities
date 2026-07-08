from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from . import __version__
from .config import AppConfig
from .okta_client import OktaClient
from .transform import action_rows, condition_rows, filter_rules, rule_summary_row, target_group_rows
from .writer import write_csv, write_execution_report, write_json, write_markdown_summary


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def run_export(config: AppConfig, mode: str) -> dict[str, Any]:
    started = utc_now()
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_dir = config.output_dir / f"okta-group-rule-exporter-{timestamp}"
    run_dir.mkdir(parents=True, exist_ok=True)

    errors: list[str] = []
    requests: list[dict[str, Any]] = []
    rules: list[dict[str, Any]] = []
    raw_pages: list[list[dict[str, Any]]] = []

    if mode == "export":
        client = OktaClient(
            config.target_org_url,
            config.api_token,
            timeout=config.settings.request_timeout_seconds,
            max_retries=config.settings.max_retries,
        )
        try:
            rules, raw_pages = client.list_group_rules(
                limit=config.settings.page_limit,
                expand_group_names=config.export.expand_group_names,
            )
        except Exception as exc:  # pragma: no cover - covered by integration behavior
            errors.append(str(exc))
            if not config.settings.continue_on_error:
                requests = getattr(client, "request_log", [])
                return _write_outputs(config, run_dir, mode, started, errors, requests, [], [], raw_pages)
        requests = client.request_log
    else:
        # Dry-run is intentionally local-only. It validates config and creates the output folder.
        rules = []

    filtered = filter_rules(
        rules,
        rule_ids=config.export.rule_ids,
        statuses=config.export.statuses,
        name_contains=config.export.rule_name_contains,
    )
    return _write_outputs(config, run_dir, mode, started, errors, requests, rules, filtered, raw_pages)


def _write_outputs(
    config: AppConfig,
    run_dir: Path,
    mode: str,
    started: str,
    errors: list[str],
    requests: list[dict[str, Any]],
    all_rules: list[dict[str, Any]],
    filtered_rules: list[dict[str, Any]],
    raw_pages: list[list[dict[str, Any]]],
) -> dict[str, Any]:
    summary_rows = [rule_summary_row(r) for r in filtered_rules]
    conditions = [row for rule in filtered_rules for row in condition_rows(rule)]
    targets = [row for rule in filtered_rules for row in target_group_rows(rule)]
    actions = [row for rule in filtered_rules for row in action_rows(rule)]

    output_files: list[str] = []

    write_json(run_dir / "group_rules.json", filtered_rules)
    output_files.append("group_rules.json")

    write_csv(run_dir / "group_rules.csv", summary_rows, [
        "id", "name", "status", "priority", "created", "lastUpdated", "expressionType", "expressionValue",
        "targetGroupIds", "targetGroupNames", "sourceGroupInclude", "sourceGroupExclude", "conditionsJson", "actionsJson",
    ])
    output_files.append("group_rules.csv")

    write_csv(run_dir / "group_rule_conditions.csv", conditions, ["ruleId", "ruleName", "conditionType", "conditionKey", "conditionValue"])
    output_files.append("group_rule_conditions.csv")

    write_csv(run_dir / "group_rule_group_targets.csv", targets, ["ruleId", "ruleName", "targetGroupId", "targetGroupName"])
    output_files.append("group_rule_group_targets.csv")

    write_csv(run_dir / "group_rule_actions.csv", actions, ["ruleId", "ruleName", "actionType", "actionJson"])
    output_files.append("group_rule_actions.csv")

    if config.export.save_raw_responses:
        write_json(run_dir / "raw_group_rules.json", raw_pages)
        output_files.append("raw_group_rules.json")

    result = {
        "utility": "okta-group-rule-exporter",
        "version": __version__,
        "mode": mode,
        "startedAt": started,
        "finishedAt": utc_now(),
        "targetOrgUrl": config.target_org_url,
        "rulesReturned": len(all_rules),
        "rulesExported": len(filtered_rules),
        "statusCounts": dict(Counter(str(r.get("status", "UNKNOWN")) for r in filtered_rules)),
        "filters": {
            "ruleIds": config.export.rule_ids,
            "ruleNameContains": config.export.rule_name_contains,
            "statuses": config.export.statuses,
            "includeInactive": config.export.include_inactive,
        },
        "requests": requests,
        "errors": errors,
        "outputFiles": output_files,
        "runDirectory": str(run_dir),
    }

    write_json(run_dir / "group_rule_export_result.json", result)
    output_files.append("group_rule_export_result.json")
    result["outputFiles"] = output_files
    write_markdown_summary(run_dir / "group_rule_summary.md", result)
    output_files.append("group_rule_summary.md")
    result["outputFiles"] = output_files
    write_execution_report(run_dir / "execution_report.md", result)
    output_files.append("execution_report.md")
    result["outputFiles"] = output_files
    write_json(run_dir / "group_rule_export_result.json", result)
    return result
