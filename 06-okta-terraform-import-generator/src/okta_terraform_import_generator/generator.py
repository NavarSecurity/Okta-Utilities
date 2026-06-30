from __future__ import annotations

import csv
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

from .loader import BackupLoader
from .models import GeneratorConfig, ImportRecord, UnsupportedRecord, GenerationResult
from .utils import slugify, unique_name, write_json

DEFAULT_APP_MAPPINGS = {
    "oidc_client": "okta_app_oauth",
    "saml2": "okta_app_saml",
    "bookmark": "okta_app_bookmark",
    "auto_login": "okta_app_auto_login",
    "basic_auth": "okta_app_basic_auth",
    "secure_password_store": "okta_app_secure_password_store",
    "browser_plugin": "okta_app_browser_plugin",
}

DEFAULT_IDP_MAPPINGS = {
    "SAML2": "okta_idp_saml",
    "OIDC": "okta_idp_oidc",
    "SOCIAL": "okta_idp_social",
    "GOOGLE": "okta_idp_social",
    "FACEBOOK": "okta_idp_social",
    "MICROSOFT": "okta_idp_social",
    "LINKEDIN": "okta_idp_social",
}

DEFAULT_POLICY_MAPPINGS = {
    "OKTA_SIGN_ON": "okta_policy_signon",
    "PASSWORD": "okta_policy_password",
    "MFA_ENROLL": "okta_policy_mfa",
    "IDP_DISCOVERY": "okta_policy_idp_discovery",
}

STATIC_RESOURCE_MAPPINGS = {
    "groups": "okta_group",
    "trusted_origins": "okta_trusted_origin",
    "network_zones": "okta_network_zone",
    "authorization_servers": "okta_auth_server",
    "authorization_server_scopes": "okta_auth_server_scope",
    "authorization_server_claims": "okta_auth_server_claim",
    "authorization_server_policies": "okta_auth_server_policy",
    "authorization_server_policy_rules": "okta_auth_server_policy_rule",
}

HIGH_RISK_RESOURCES = {"policies", "identity_providers", "authorization_server_policies", "authorization_server_policy_rules"}


class TerraformImportGenerator:
    def __init__(self, config: GeneratorConfig):
        self.config = config
        self.loader = BackupLoader(config.backup_dir)
        self.imports: List[ImportRecord] = []
        self.unsupported: List[UnsupportedRecord] = []
        self.warnings: List[str] = []
        self.errors: List[str] = []
        self._seen_names: Dict[str, int] = {}

    def generate(self) -> GenerationResult:
        if not self.config.backup_dir.exists():
            raise FileNotFoundError(f"Backup directory not found: {self.config.backup_dir}")
        run_dir = self._run_dir()
        run_dir.mkdir(parents=True, exist_ok=True)

        for resource in self.config.include:
            handler = getattr(self, f"_handle_{resource}", None)
            if handler is None:
                self.warnings.append(f"Unsupported include resource requested: {resource}")
                continue
            handler()

        counts: Dict[str, int] = {}
        for rec in self.imports:
            counts[rec.resource] = counts.get(rec.resource, 0) + 1

        self._write_outputs(run_dir, counts)
        status = "PASS"
        if self.errors:
            status = "FAIL"
        elif self.unsupported or self.warnings:
            status = "WARN"
        if self.config.strict_mode and (self.unsupported or self.warnings):
            status = "FAIL"

        result = GenerationResult(
            status=status,
            output_dir=str(run_dir),
            backup_dir=str(self.config.backup_dir),
            total_imports=len(self.imports),
            total_unsupported=len(self.unsupported),
            counts_by_resource=counts,
            imports=[asdict(x) for x in self.imports],
            unsupported=[asdict(x) for x in self.unsupported],
            warnings=self.warnings,
            errors=self.errors,
        )
        write_json(run_dir / "terraform_import_plan.json", asdict(result))
        return result

    def _run_dir(self) -> Path:
        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        return self.config.output_dir / f"okta-terraform-imports-{ts}"

    def _resource_address(self, terraform_type: str, object_name: str) -> Tuple[str, str]:
        base = slugify(f"{self.config.resource_name_prefix}{object_name}", self.config.max_resource_name_length)
        tf_name = unique_name(base, self._seen_names)
        prefix = self.config.module_prefix.strip()
        address = f"{terraform_type}.{tf_name}"
        if prefix:
            address = f"{prefix}.{address}" if not prefix.endswith(".") else f"{prefix}{address}"
        return tf_name, address

    def _add_import(
        self,
        resource: str,
        source_file: str,
        obj: Dict[str, Any],
        terraform_type: str,
        object_name: str,
        import_id: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        if not import_id:
            self._add_unsupported(resource, source_file, obj.get("id", ""), object_name, "Missing object ID", metadata or {})
            return
        tf_name, address = self._resource_address(terraform_type, object_name or import_id)
        command = f"terraform import {address} {import_id}"
        block = f'import {{\n  to = {address}\n  id = "{import_id}"\n}}'
        self.imports.append(
            ImportRecord(
                resource=resource,
                source_file=source_file,
                object_id=str(obj.get("id", import_id)),
                object_name=str(object_name or obj.get("name") or obj.get("label") or import_id),
                terraform_type=terraform_type,
                terraform_name=tf_name,
                terraform_address=address,
                import_id=str(import_id),
                command=command,
                block=block,
                metadata=metadata or {},
            )
        )

    def _add_unsupported(self, resource: str, source_file: str, object_id: str, object_name: str, reason: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        self.unsupported.append(
            UnsupportedRecord(
                resource=resource,
                source_file=source_file,
                object_id=str(object_id or ""),
                object_name=str(object_name or ""),
                reason=reason,
                metadata=metadata or {},
            )
        )

    def _skip_system(self, obj: Dict[str, Any]) -> bool:
        return bool(self.config.skip_system_objects and obj.get("system") is True)

    def _handle_groups(self) -> None:
        for obj in self.loader.groups():
            if self._skip_system(obj):
                continue
            name = obj.get("profile", {}).get("name") or obj.get("name") or obj.get("id")
            self._add_import("groups", "groups.json", obj, "okta_group", name, obj.get("id", ""))

    def _handle_applications(self) -> None:
        mappings = {**DEFAULT_APP_MAPPINGS, **self.config.app_resource_mappings, **self.config.custom_resource_mappings}
        for obj in self.loader.applications():
            if self._skip_system(obj):
                continue
            app_type = obj.get("name") or obj.get("signOnMode")
            tf_type = mappings.get(str(app_type))
            label = obj.get("label") or obj.get("name") or obj.get("id")
            if not tf_type:
                self._add_unsupported("applications", "applications.json", obj.get("id", ""), label, f"No Terraform resource mapping for Okta app type/name '{app_type}'", {"appType": app_type})
                continue
            self._add_import("applications", "applications.json", obj, tf_type, label, obj.get("id", ""), {"appType": app_type})

    def _handle_trusted_origins(self) -> None:
        for obj in self.loader.trusted_origins():
            name = obj.get("name") or obj.get("origin") or obj.get("id")
            self._add_import("trusted_origins", "trusted_origins.json", obj, "okta_trusted_origin", name, obj.get("id", ""))

    def _handle_network_zones(self) -> None:
        for obj in self.loader.network_zones():
            name = obj.get("name") or obj.get("id")
            self._add_import("network_zones", "network_zones.json", obj, "okta_network_zone", name, obj.get("id", ""))

    def _handle_authorization_servers(self) -> None:
        servers, _details = self.loader.authorization_server_bundle()
        for obj in servers:
            name = obj.get("name") or obj.get("id")
            self._add_import("authorization_servers", "authorization_servers.json", obj, "okta_auth_server", name, obj.get("id", ""))

    def _handle_authorization_server_scopes(self) -> None:
        _servers, details = self.loader.authorization_server_bundle()
        for auth_server_id, detail in details.items():
            for scope in detail.get("scopes", []) or []:
                if not isinstance(scope, dict):
                    continue
                name = scope.get("name") or scope.get("id")
                import_id = f"{auth_server_id}/{scope.get('id', '')}" if scope.get("id") else ""
                self._add_import("authorization_server_scopes", "authorization_servers.json", scope, "okta_auth_server_scope", f"{auth_server_id}_{name}", import_id, {"authServerId": auth_server_id})

    def _handle_authorization_server_claims(self) -> None:
        _servers, details = self.loader.authorization_server_bundle()
        for auth_server_id, detail in details.items():
            for claim in detail.get("claims", []) or []:
                if not isinstance(claim, dict):
                    continue
                name = claim.get("name") or claim.get("id")
                import_id = f"{auth_server_id}/{claim.get('id', '')}" if claim.get("id") else ""
                self._add_import("authorization_server_claims", "authorization_servers.json", claim, "okta_auth_server_claim", f"{auth_server_id}_{name}", import_id, {"authServerId": auth_server_id})

    def _handle_authorization_server_policies(self) -> None:
        _servers, details = self.loader.authorization_server_bundle()
        for auth_server_id, detail in details.items():
            for policy in detail.get("policies", []) or []:
                if not isinstance(policy, dict):
                    continue
                name = policy.get("name") or policy.get("id")
                import_id = f"{auth_server_id}/{policy.get('id', '')}" if policy.get("id") else ""
                self._add_import("authorization_server_policies", "authorization_servers.json", policy, "okta_auth_server_policy", f"{auth_server_id}_{name}", import_id, {"authServerId": auth_server_id, "manualReview": True})

    def _handle_authorization_server_policy_rules(self) -> None:
        _servers, details = self.loader.authorization_server_bundle()
        for auth_server_id, detail in details.items():
            rules_by_policy = detail.get("rulesByPolicyId", {}) or {}
            if not isinstance(rules_by_policy, dict):
                continue
            for policy_id, rules in rules_by_policy.items():
                for rule in rules or []:
                    if not isinstance(rule, dict):
                        continue
                    name = rule.get("name") or rule.get("id")
                    import_id = f"{auth_server_id}/{policy_id}/{rule.get('id', '')}" if rule.get("id") else ""
                    self._add_import("authorization_server_policy_rules", "authorization_servers.json", rule, "okta_auth_server_policy_rule", f"{auth_server_id}_{policy_id}_{name}", import_id, {"authServerId": auth_server_id, "policyId": policy_id, "manualReview": True})

    def _handle_policies(self) -> None:
        mappings = {**DEFAULT_POLICY_MAPPINGS, **self.config.policy_resource_mappings, **self.config.custom_resource_mappings}
        for obj in self.loader.policies():
            if self._skip_system(obj):
                continue
            policy_type = obj.get("type")
            tf_type = mappings.get(str(policy_type))
            name = f"{policy_type}_{obj.get('name') or obj.get('id')}"
            if not tf_type:
                self._add_unsupported("policies", "policies.json", obj.get("id", ""), name, f"No Terraform resource mapping for Okta policy type '{policy_type}'", {"policyType": policy_type, "manualReview": True})
                continue
            self._add_import("policies", "policies.json", obj, tf_type, name, obj.get("id", ""), {"policyType": policy_type, "manualReview": True})

    def _handle_identity_providers(self) -> None:
        mappings = {**DEFAULT_IDP_MAPPINGS, **self.config.idp_resource_mappings, **self.config.custom_resource_mappings}
        for obj in self.loader.identity_providers():
            if self._skip_system(obj):
                continue
            idp_type = obj.get("type")
            tf_type = mappings.get(str(idp_type))
            name = obj.get("name") or obj.get("id")
            if not tf_type:
                self._add_unsupported("identity_providers", "identity_providers.json", obj.get("id", ""), name, f"No Terraform resource mapping for Okta IdP type '{idp_type}'", {"idpType": idp_type, "manualReview": True})
                continue
            self._add_import("identity_providers", "identity_providers.json", obj, tf_type, name, obj.get("id", ""), {"idpType": idp_type, "manualReview": True})

    def _write_outputs(self, run_dir: Path, counts: Dict[str, int]) -> None:
        if self.config.mode in {"commands", "both"}:
            commands = ["#!/usr/bin/env bash", "set -euo pipefail", ""]
            commands.extend(rec.command for rec in self.imports)
            (run_dir / "terraform_imports.sh").write_text("\n".join(commands) + "\n", encoding="utf-8")
        if self.config.mode in {"blocks", "both"}:
            blocks = []
            for rec in self.imports:
                blocks.append(rec.block)
                blocks.append("")
            (run_dir / "imports.tf").write_text("\n".join(blocks), encoding="utf-8")
        if self.config.write_csv:
            self._write_csv(run_dir / "resource_mapping.csv", [asdict(x) for x in self.imports], ["resource", "source_file", "object_id", "object_name", "terraform_type", "terraform_name", "terraform_address", "import_id", "command"])
            self._write_csv(run_dir / "unsupported_resources.csv", [asdict(x) for x in self.unsupported], ["resource", "source_file", "object_id", "object_name", "reason"])
        if self.config.write_markdown:
            (run_dir / "import_summary.md").write_text(self._markdown_summary(counts), encoding="utf-8")
        (run_dir / "execution_report.md").write_text(self._execution_report(counts), encoding="utf-8")

    def _write_csv(self, path: Path, rows: List[Dict[str, Any]], fields: List[str]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
            writer.writeheader()
            for row in rows:
                writer.writerow(row)

    def _markdown_summary(self, counts: Dict[str, int]) -> str:
        lines = [
            "# Terraform Import Summary",
            "",
            f"Backup directory: `{self.config.backup_dir}`",
            f"Total import records: **{len(self.imports)}**",
            f"Unsupported records: **{len(self.unsupported)}**",
            "",
            "## Counts by Resource",
            "",
            "| Resource | Import Records |",
            "|---|---:|",
        ]
        for k in sorted(counts):
            lines.append(f"| `{k}` | {counts[k]} |")
        lines.extend(["", "## Notes", ""])
        if self.unsupported:
            lines.append("Some objects could not be mapped to Terraform resource types. Review `unsupported_resources.csv`.")
        else:
            lines.append("No unsupported objects were found.")
        lines.extend(["", "WARNING: These utilities have limited testing and are provided as-is with no warranty. Use at your own risk.", ""])
        return "\n".join(lines)

    def _execution_report(self, counts: Dict[str, int]) -> str:
        lines = [
            "# Execution Report",
            "",
            f"Utility: `okta-terraform-import-generator`",
            f"Backup directory: `{self.config.backup_dir}`",
            f"Mode: `{self.config.mode}`",
            f"Total import records: `{len(self.imports)}`",
            f"Unsupported records: `{len(self.unsupported)}`",
            f"Warnings: `{len(self.warnings)}`",
            f"Errors: `{len(self.errors)}`",
            "",
            "## Generated Files",
            "",
            "- `terraform_import_plan.json`",
            "- `terraform_imports.sh` when command output is enabled",
            "- `imports.tf` when import block output is enabled",
            "- `resource_mapping.csv`",
            "- `unsupported_resources.csv`",
            "- `import_summary.md`",
            "- `execution_report.md`",
            "",
        ]
        if self.warnings:
            lines.extend(["## Warnings", ""])
            lines.extend(f"- {w}" for w in self.warnings)
            lines.append("")
        if self.errors:
            lines.extend(["## Errors", ""])
            lines.extend(f"- {e}" for e in self.errors)
            lines.append("")
        return "\n".join(lines)
