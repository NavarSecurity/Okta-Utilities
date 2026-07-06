from __future__ import annotations

import csv
import json
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .jwt_utils import JwtValidationResult
from .tester import TokenTestResult, result_to_dict


def create_run_dir(base_dir: Path) -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_dir = base_dir / f"okta-token-tester-{stamp}"
    run_dir.mkdir(parents=True, exist_ok=False)
    return run_dir


def write_json(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, indent=2, sort_keys=True, default=str), encoding="utf-8")


def write_plan(run_dir: Path, plan: dict[str, Any]) -> None:
    write_json(run_dir / "token_test_plan.json", plan)
    write_execution_report(run_dir / "execution_report.md", "dry-run", plan.get("orgUrl", ""), plan.get("issuerUrl", ""), {"plannedTests": _count_planned_tests(plan), "errors": 0})


def write_results(run_dir: Path, result: TokenTestResult) -> None:
    write_json(run_dir / "token_test_result.json", result_to_dict(result))
    if result.discovery:
        write_json(run_dir / "discovery_metadata.json", result.discovery)
    write_jwks_summary(run_dir / "jwks_summary.csv", result.jwks_summary)
    write_token_claims_summary(run_dir / "token_claims_summary.csv", result.jwt_validation_results)
    write_findings_csv(run_dir / "validation_findings.csv", result)
    write_markdown_report(run_dir / "token_test_report.md", result)
    write_execution_report(run_dir / "execution_report.md", "test", result.org_url, result.issuer_url, result.summary())


def write_jwks_summary(path: Path, rows: list[dict[str, Any]]) -> None:
    fields = ["kid", "kty", "alg", "use", "key_ops"]
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fields})


def write_token_claims_summary(path: Path, validations: list[JwtValidationResult]) -> None:
    fields = ["test_name", "passed", "token_source", "token_type", "issuer", "subject", "audience", "scopes", "expires_at", "issued_at", "kid", "alg"]
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for item in validations:
            claims = item.claims or {}
            header = item.header or {}
            scopes = claims.get("scp", claims.get("scope", []))
            if isinstance(scopes, list):
                scopes_text = ";".join(str(s) for s in scopes)
            else:
                scopes_text = str(scopes or "")
            writer.writerow(
                {
                    "test_name": item.test_name,
                    "passed": item.passed,
                    "token_source": item.token_source,
                    "token_type": item.token_type,
                    "issuer": claims.get("iss", ""),
                    "subject": claims.get("sub", ""),
                    "audience": claims.get("aud", ""),
                    "scopes": scopes_text,
                    "expires_at": claims.get("exp", ""),
                    "issued_at": claims.get("iat", ""),
                    "kid": header.get("kid", ""),
                    "alg": header.get("alg", ""),
                }
            )


def write_findings_csv(path: Path, result: TokenTestResult) -> None:
    fields = ["area", "test_name", "severity", "check", "message"]
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for validation in result.jwt_validation_results:
            for finding in validation.findings:
                writer.writerow({"area": "jwt_validation", "test_name": finding.test_name, "severity": finding.severity, "check": finding.check, "message": finding.message})
        for flow in result.client_credentials_results + result.authorization_code_results:
            if not flow.passed:
                writer.writerow({"area": flow.flow_type, "test_name": flow.test_name, "severity": "error", "check": "flow", "message": flow.error or "Flow failed"})
        for item in result.introspection_results:
            if not item.passed:
                writer.writerow({"area": "introspection", "test_name": item.test_name, "severity": "error", "check": "introspection", "message": item.error or f"Unexpected active={item.active}"})
        for err in result.errors:
            writer.writerow({"area": err.get("stage", "error"), "test_name": "", "severity": "error", "check": err.get("stage", "error"), "message": err.get("message", "")})


def write_markdown_report(path: Path, result: TokenTestResult) -> None:
    summary = result.summary()
    lines = [
        "# Okta Token Test Report",
        "",
        f"Mode: `{result.mode}`",
        f"Org URL: `{result.org_url}`",
        f"Issuer URL: `{result.issuer_url}`",
        "",
        "## Summary",
        "",
        f"- Flows tested: {summary['flowsTested']}",
        f"- JWT validations: {summary['jwtValidations']}",
        f"- Introspection tests: {summary['introspectionTests']}",
        f"- JWKS keys found: {summary['jwksKeys']}",
        f"- Findings: {summary['findings']}",
        f"- Errors: {summary['errors']}",
        f"- Failed checks: {summary['failedChecks']}",
        "",
        "## Flow Results",
        "",
    ]
    flows = result.client_credentials_results + result.authorization_code_results
    if not flows:
        lines.append("No token flow tests were run.")
    else:
        lines.extend(["| Test | Flow | Passed | Error |", "|---|---|---:|---|"])
        for flow in flows:
            lines.append(f"| {flow.test_name} | {flow.flow_type} | {flow.passed} | {flow.error or ''} |")
    lines.extend(["", "## JWT Validation Results", ""])
    if not result.jwt_validation_results:
        lines.append("No JWT validation tests were run.")
    else:
        lines.extend(["| Test | Token Source | Passed | Findings |", "|---|---|---:|---:|"])
        for validation in result.jwt_validation_results:
            lines.append(f"| {validation.test_name} | {validation.token_source} | {validation.passed} | {len(validation.findings)} |")
    lines.extend(["", "## Introspection Results", ""])
    if not result.introspection_results:
        lines.append("No introspection tests were run.")
    else:
        lines.extend(["| Test | Passed | Active | Error |", "|---|---:|---:|---|"])
        for item in result.introspection_results:
            lines.append(f"| {item.test_name} | {item.passed} | {item.active} | {item.error or ''} |")
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def write_execution_report(path: Path, mode: str, org_url: str, issuer_url: str, summary: dict[str, Any]) -> None:
    lines = [
        "# Execution Report",
        "",
        f"Mode: `{mode}`",
        f"Generated at UTC: `{datetime.now(timezone.utc).isoformat()}`",
        f"Org URL: `{org_url}`",
        f"Issuer URL: `{issuer_url}`",
        "",
        "## Summary",
        "",
    ]
    for key, value in summary.items():
        lines.append(f"- {key}: {value}")
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def _count_planned_tests(plan: dict[str, Any]) -> int:
    return sum(len(plan.get(key, [])) for key in ["clientCredentialsTests", "authorizationCodeTests", "jwtValidationTests", "introspectionTests"])
