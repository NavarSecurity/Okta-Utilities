from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from . import __version__
from .checks import CheckRecorder
from .config import ValidatorConfig
from .jsonio import read_json
from .resource_rules import (
    AUTH_SERVER_REQUIRED_FIELDS,
    POLICIES_REQUIRED_FIELDS,
    RESOURCE_RULES,
    count_objects,
    missing_fields,
    normalize_resource_records,
)
from .sensitive_scan import scan_backup_files


class BackupValidator:
    def __init__(self, cfg: ValidatorConfig) -> None:
        self.cfg = cfg
        self.recorder = CheckRecorder()
        self.loaded_json: dict[str, Any] = {}

    def run(self) -> dict[str, Any]:
        validation_id = f"okta-backup-validation-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
        backup_dir = self.cfg.backup_dir

        if not backup_dir.exists() or not backup_dir.is_dir():
            self.recorder.fail(
                "BACKUP_DIR_MISSING",
                f"Backup directory does not exist or is not a directory: {backup_dir}",
            )
            return self.result(validation_id, None)

        self.recorder.pass_("BACKUP_DIR_EXISTS", f"Backup directory exists: {backup_dir}")
        manifest = self.load_manifest(backup_dir)
        if manifest is None:
            return self.result(validation_id, None)

        self.validate_manifest_shape(manifest)
        requested_resources = self.determine_resources(manifest)
        self.validate_files(backup_dir, manifest, requested_resources)
        self.validate_manifest_counts(manifest)
        self.validate_resource_shapes(requested_resources)
        self.validate_sensitive_values()

        return self.result(validation_id, manifest)

    def result(self, validation_id: str, manifest: dict[str, Any] | None) -> dict[str, Any]:
        counts = self.recorder.counts()
        overall_status = self.recorder.overall_status(self.cfg.fail_on_warnings)
        return {
            "utility": "okta-backup-validator",
            "version": __version__,
            "validationId": validation_id,
            "generatedAt": datetime.now(timezone.utc).isoformat(),
            "backupDir": str(self.cfg.backup_dir),
            "backupId": manifest.get("backupId") if isinstance(manifest, dict) else None,
            "orgUrl": manifest.get("orgUrl") if isinstance(manifest, dict) else None,
            "overallStatus": overall_status,
            "summary": {
                "passed": counts["PASS"],
                "warnings": counts["WARN"],
                "failures": counts["FAIL"],
                "totalChecks": sum(counts.values()),
            },
            "checks": [item.to_dict() for item in self.recorder.results],
        }

    def load_manifest(self, backup_dir: Path) -> dict[str, Any] | None:
        manifest_path = backup_dir / "manifest.json"
        if not manifest_path.exists():
            self.recorder.fail("MANIFEST_MISSING", "manifest.json is missing.", file="manifest.json")
            return None
        try:
            manifest = read_json(manifest_path)
        except Exception as exc:  # noqa: BLE001 - validator records exact file failure.
            self.recorder.fail("MANIFEST_INVALID_JSON", f"manifest.json is not valid JSON: {exc}", file="manifest.json")
            return None
        if not isinstance(manifest, dict):
            self.recorder.fail("MANIFEST_NOT_OBJECT", "manifest.json must contain a JSON object.", file="manifest.json")
            return None
        self.loaded_json["manifest.json"] = manifest
        self.recorder.pass_("MANIFEST_VALID_JSON", "manifest.json exists and is valid JSON.", file="manifest.json")
        return manifest

    def validate_manifest_shape(self, manifest: dict[str, Any]) -> None:
        required_manifest_fields = ["backupId", "generatedAt", "orgUrl", "redactionEnabled", "requestedResources", "files", "counts", "errors"]
        missing = [field for field in required_manifest_fields if field not in manifest]
        if missing:
            self.recorder.fail(
                "MANIFEST_REQUIRED_FIELDS_MISSING",
                f"manifest.json is missing required field(s): {', '.join(missing)}",
                file="manifest.json",
                details={"missingFields": missing},
            )
        else:
            self.recorder.pass_("MANIFEST_REQUIRED_FIELDS_PRESENT", "manifest.json contains required fields.", file="manifest.json")

        backup_id = manifest.get("backupId")
        if isinstance(backup_id, str) and backup_id.startswith("okta-config-backup-"):
            self.recorder.pass_("BACKUP_ID_VALID", f"Backup ID appears valid: {backup_id}", file="manifest.json")
        else:
            self.recorder.warn("BACKUP_ID_UNEXPECTED", "Backup ID is missing or does not follow okta-config-backup-* format.", file="manifest.json")

        generated_at = manifest.get("generatedAt")
        if isinstance(generated_at, str):
            try:
                datetime.fromisoformat(generated_at.replace("Z", "+00:00"))
                self.recorder.pass_("GENERATED_AT_VALID", "generatedAt is parseable as an ISO timestamp.", file="manifest.json")
            except ValueError:
                self.recorder.fail("GENERATED_AT_INVALID", "generatedAt is not a parseable ISO timestamp.", file="manifest.json")
        else:
            self.recorder.fail("GENERATED_AT_MISSING", "generatedAt is missing or not a string.", file="manifest.json")

        org_url = manifest.get("orgUrl")
        if isinstance(org_url, str):
            parsed = urlparse(org_url)
            if parsed.scheme == "https" and parsed.netloc and "your-org.okta.com" not in org_url:
                self.recorder.pass_("ORG_URL_VALID", "Org URL is an HTTPS URL and does not appear to be a placeholder.", file="manifest.json")
            else:
                self.recorder.fail(
                    "ORG_URL_INVALID_OR_PLACEHOLDER",
                    "Org URL is not a valid HTTPS Okta org URL or still contains the placeholder your-org.okta.com.",
                    file="manifest.json",
                    details={"orgUrl": org_url},
                )
        else:
            self.recorder.fail("ORG_URL_MISSING", "orgUrl is missing or not a string.", file="manifest.json")

        if manifest.get("redactionEnabled") is True:
            self.recorder.pass_("REDACTION_ENABLED", "Backup manifest reports redactionEnabled=true.", file="manifest.json")
        else:
            message = "Backup manifest does not report redactionEnabled=true. Treat this backup as sensitive."
            if self.cfg.require_redaction_enabled:
                self.recorder.fail("REDACTION_NOT_ENABLED", message, file="manifest.json")
            else:
                self.recorder.warn("REDACTION_NOT_ENABLED", message, file="manifest.json")

        errors = manifest.get("errors", [])
        if isinstance(errors, list) and errors:
            by_resource: dict[str, int] = {}
            for error in errors:
                resource = error.get("resource", "unknown") if isinstance(error, dict) else "unknown"
                by_resource[resource] = by_resource.get(resource, 0) + 1
            message = f"Manifest contains {len(errors)} recorded backup error(s)."
            if self.cfg.require_no_resource_errors:
                self.recorder.fail("MANIFEST_RECORDED_ERRORS", message, file="manifest.json", details={"byResource": by_resource})
            else:
                self.recorder.warn("MANIFEST_RECORDED_ERRORS", message, file="manifest.json", details={"byResource": by_resource})
        elif isinstance(errors, list):
            self.recorder.pass_("MANIFEST_NO_RECORDED_ERRORS", "Manifest contains no recorded backup errors.", file="manifest.json")
        else:
            self.recorder.fail("MANIFEST_ERRORS_NOT_LIST", "manifest.errors must be a list.", file="manifest.json")

    def determine_resources(self, manifest: dict[str, Any]) -> list[str]:
        if self.cfg.expected_resources:
            resources = self.cfg.expected_resources
            self.recorder.pass_("EXPECTED_RESOURCES_FROM_CONFIG", "Using expected resources from validator config.")
            return resources
        resources = manifest.get("requestedResources", [])
        if isinstance(resources, list) and all(isinstance(item, str) for item in resources):
            self.recorder.pass_("EXPECTED_RESOURCES_FROM_MANIFEST", "Using requestedResources from manifest.", file="manifest.json")
            return resources
        self.recorder.fail("REQUESTED_RESOURCES_INVALID", "manifest.requestedResources must be a list of strings.", file="manifest.json")
        return []

    def validate_files(self, backup_dir: Path, manifest: dict[str, Any], resources: list[str]) -> None:
        files = manifest.get("files", [])
        if not isinstance(files, list) or not all(isinstance(item, str) for item in files):
            self.recorder.fail("MANIFEST_FILES_INVALID", "manifest.files must be a list of strings.", file="manifest.json")
            files = []
        else:
            self.recorder.pass_("MANIFEST_FILES_VALID", "manifest.files is a list of file paths.", file="manifest.json")

        listed_files = set(files)
        errored_resources = self.errored_resources(manifest)
        for file_name in sorted(listed_files):
            file_path = backup_dir / file_name
            if not file_path.exists():
                self.recorder.fail("LISTED_FILE_MISSING", f"File listed in manifest does not exist: {file_name}", file=file_name)
                continue
            try:
                data = read_json(file_path)
                self.loaded_json[file_name] = data
                self.recorder.pass_("BACKUP_FILE_VALID_JSON", f"Backup file is valid JSON: {file_name}", file=file_name)
            except Exception as exc:  # noqa: BLE001
                self.recorder.fail("BACKUP_FILE_INVALID_JSON", f"Backup file is not valid JSON: {exc}", file=file_name)

        for resource in resources:
            expected_file = f"{resource}.json"
            if expected_file in listed_files:
                continue
            if resource in errored_resources and self.cfg.allow_missing_files_for_errored_resources:
                self.recorder.warn(
                    "RESOURCE_FILE_MISSING_WITH_ERROR",
                    f"{expected_file} is missing, and manifest has recorded errors for {resource}.",
                    resource=resource,
                    file=expected_file,
                )
            else:
                self.recorder.fail(
                    "RESOURCE_FILE_MISSING",
                    f"Expected backup file is missing: {expected_file}",
                    resource=resource,
                    file=expected_file,
                )

        for required in self.cfg.required_resources or []:
            if required == "manifest":
                continue
            required_file = f"{required}.json"
            if required_file not in listed_files:
                self.recorder.fail(
                    "REQUIRED_RESOURCE_FILE_MISSING",
                    f"Required resource file is missing: {required_file}",
                    resource=required,
                    file=required_file,
                )

    def validate_manifest_counts(self, manifest: dict[str, Any]) -> None:
        counts = manifest.get("counts", {})
        if not isinstance(counts, dict):
            self.recorder.fail("MANIFEST_COUNTS_INVALID", "manifest.counts must be an object.", file="manifest.json")
            return

        for file_name, data in self.loaded_json.items():
            if file_name == "manifest.json" or not file_name.endswith(".json"):
                continue
            resource = file_name.removesuffix(".json")
            actual = count_objects(data, resource)
            expected = counts.get(resource)
            if expected is None:
                self.recorder.warn(
                    "COUNT_MISSING_FROM_MANIFEST",
                    f"manifest.counts has no value for {resource}; actual count is {actual}.",
                    resource=resource,
                    file=file_name,
                    details={"actualCount": actual},
                )
            elif expected == actual:
                self.recorder.pass_(
                    "COUNT_MATCHES_MANIFEST",
                    f"Object count matches manifest for {resource}: {actual}.",
                    resource=resource,
                    file=file_name,
                    details={"count": actual},
                )
            else:
                self.recorder.fail(
                    "COUNT_MISMATCH",
                    f"Object count mismatch for {resource}: manifest={expected}, actual={actual}.",
                    resource=resource,
                    file=file_name,
                    details={"manifestCount": expected, "actualCount": actual},
                )

    def validate_resource_shapes(self, resources: list[str]) -> None:
        for resource in resources:
            file_name = f"{resource}.json"
            if file_name not in self.loaded_json:
                continue
            data = self.loaded_json[file_name]
            if resource == "policies":
                self.validate_policies(data, file_name)
            elif resource == "authorization_servers":
                self.validate_authorization_servers(data, file_name)
            else:
                self.validate_simple_resource(resource, data, file_name)

    def validate_simple_resource(self, resource: str, data: Any, file_name: str) -> None:
        rule = RESOURCE_RULES.get(resource)
        if not rule:
            self.recorder.warn("RESOURCE_RULE_NOT_DEFINED", f"No schema rule is defined for resource {resource}.", resource=resource, file=file_name)
            return
        shape = rule["shape"]
        records = normalize_resource_records(resource, data)
        if shape == "list" and not isinstance(records, list):
            self.recorder.fail("RESOURCE_SHAPE_INVALID", f"{file_name} must contain a JSON array or supported Okta wrapper object.", resource=resource, file=file_name)
            return
        if shape == "dict" and not isinstance(records, dict):
            self.recorder.fail("RESOURCE_SHAPE_INVALID", f"{file_name} must contain a JSON object.", resource=resource, file=file_name)
            return
        self.recorder.pass_("RESOURCE_SHAPE_VALID", f"{file_name} has expected JSON shape: {shape}.", resource=resource, file=file_name)

        if isinstance(records, list):
            required = rule.get("required", [])
            missing_samples = []
            for index, item in enumerate(records[:100]):
                if not isinstance(item, dict):
                    missing_samples.append({"index": index, "missing": ["<object>"]})
                    continue
                missing = missing_fields(item, required)
                if missing:
                    missing_samples.append({"index": index, "id": item.get("id"), "missing": missing})
                if len(missing_samples) >= 10:
                    break
            if missing_samples:
                self.recorder.fail(
                    "RESOURCE_REQUIRED_FIELDS_MISSING",
                    f"One or more {resource} object(s) are missing required fields.",
                    resource=resource,
                    file=file_name,
                    details={"samples": missing_samples},
                )
            else:
                self.recorder.pass_(
                    "RESOURCE_REQUIRED_FIELDS_PRESENT",
                    f"Sampled {resource} objects contain required fields.",
                    resource=resource,
                    file=file_name,
                )

    def validate_policies(self, data: Any, file_name: str) -> None:
        if not isinstance(data, dict) or not isinstance(data.get("policyTypes"), dict):
            self.recorder.fail("POLICIES_SHAPE_INVALID", "policies.json must contain a policyTypes object.", resource="policies", file=file_name)
            return
        self.recorder.pass_("POLICIES_SHAPE_VALID", "policies.json contains a policyTypes object.", resource="policies", file=file_name)
        for policy_type, record in data.get("policyTypes", {}).items():
            if not isinstance(record, dict) or not isinstance(record.get("policies", []), list):
                self.recorder.fail(
                    "POLICY_TYPE_RECORD_INVALID",
                    f"Policy type {policy_type} record must contain a policies list.",
                    resource="policies",
                    file=file_name,
                )
                continue
            for index, policy in enumerate(record.get("policies", [])[:50]):
                if not isinstance(policy, dict):
                    self.recorder.fail("POLICY_OBJECT_INVALID", f"Policy item {index} under {policy_type} is not an object.", resource="policies", file=file_name)
                    continue
                missing = missing_fields(policy, POLICIES_REQUIRED_FIELDS)
                if missing:
                    self.recorder.fail(
                        "POLICY_REQUIRED_FIELDS_MISSING",
                        f"Policy under {policy_type} is missing required fields: {', '.join(missing)}",
                        resource="policies",
                        file=file_name,
                        details={"policyType": policy_type, "id": policy.get("id"), "missing": missing},
                    )
                    return
        self.recorder.pass_("POLICY_REQUIRED_FIELDS_PRESENT", "Sampled policies contain required fields.", resource="policies", file=file_name)

    def validate_authorization_servers(self, data: Any, file_name: str) -> None:
        if not isinstance(data, dict) or not isinstance(data.get("authorizationServers"), list):
            self.recorder.fail("AUTH_SERVERS_SHAPE_INVALID", "authorization_servers.json must contain an authorizationServers list.", resource="authorization_servers", file=file_name)
            return
        self.recorder.pass_("AUTH_SERVERS_SHAPE_VALID", "authorization_servers.json contains an authorizationServers list.", resource="authorization_servers", file=file_name)
        missing_samples = []
        for index, server in enumerate(data.get("authorizationServers", [])[:100]):
            if not isinstance(server, dict):
                missing_samples.append({"index": index, "missing": ["<object>"]})
                continue
            missing = missing_fields(server, AUTH_SERVER_REQUIRED_FIELDS)
            if missing:
                missing_samples.append({"index": index, "id": server.get("id"), "missing": missing})
            if len(missing_samples) >= 10:
                break
        if missing_samples:
            self.recorder.fail(
                "AUTH_SERVER_REQUIRED_FIELDS_MISSING",
                "One or more authorization server object(s) are missing required fields.",
                resource="authorization_servers",
                file=file_name,
                details={"samples": missing_samples},
            )
        else:
            self.recorder.pass_("AUTH_SERVER_REQUIRED_FIELDS_PRESENT", "Sampled authorization servers contain required fields.", resource="authorization_servers", file=file_name)

    def validate_sensitive_values(self) -> None:
        if not self.cfg.sensitive_scan_enabled:
            self.recorder.warn("SENSITIVE_SCAN_DISABLED", "Sensitive value scan is disabled by config.")
            return
        findings = scan_backup_files(self.cfg.backup_dir, self.loaded_json, self.cfg.max_sensitive_findings)
        if findings:
            self.recorder.fail(
                "SENSITIVE_VALUES_FOUND",
                f"Found {len(findings)} potential unredacted sensitive value(s) in backup JSON.",
                details={"findings": [finding.to_dict() for finding in findings]},
            )
        else:
            self.recorder.pass_("SENSITIVE_SCAN_CLEAN", "No unredacted sensitive values were detected by key-name scan.")

    @staticmethod
    def errored_resources(manifest: dict[str, Any]) -> set[str]:
        resources: set[str] = set()
        for error in manifest.get("errors", []):
            if isinstance(error, dict) and isinstance(error.get("resource"), str):
                resource = error["resource"].split(":", 1)[0]
                resources.add(resource)
        return resources
