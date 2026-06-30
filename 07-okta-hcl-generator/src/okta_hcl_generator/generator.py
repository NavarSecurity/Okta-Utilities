from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import csv

from .config import GeneratorConfig
from .hcl import safe_name, hcl_string, hcl_list, hcl_bool, tf_resource
from .io_utils import write_json, write_text
from .loader import BackupData, load_backup


@dataclass
class GeneratedResource:
    resource_type: str
    resource_name: str
    source_type: str
    source_id: str | None
    natural_key: str | None
    hcl_file: str
    import_id: str | None
    status: str = "generated"
    notes: str = ""


@dataclass
class GenerationResult:
    generation_id: str
    backup_dir: str
    output_dir: str
    status: str
    include: list[str]
    generated_resources: list[GeneratedResource] = field(default_factory=list)
    unsupported: list[dict[str, Any]] = field(default_factory=list)
    manual_review: list[dict[str, Any]] = field(default_factory=list)
    missing_files: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "generationId": self.generation_id,
            "backupDir": self.backup_dir,
            "outputDir": self.output_dir,
            "status": self.status,
            "include": self.include,
            "generatedResources": [r.__dict__ for r in self.generated_resources],
            "unsupported": self.unsupported,
            "manualReview": self.manual_review,
            "missingFiles": self.missing_files,
            "warnings": self.warnings,
            "counts": {
                "generated": len(self.generated_resources),
                "unsupported": len(self.unsupported),
                "manualReview": len(self.manual_review),
                "missingFiles": len(self.missing_files),
            },
        }


def now_id() -> str:
    return "okta-hcl-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def profile_name(obj: dict[str, Any]) -> str | None:
    profile = obj.get("profile") if isinstance(obj.get("profile"), dict) else {}
    return profile.get("name") or obj.get("name") or obj.get("label")


def prefixed(cfg: GeneratorConfig, base: str) -> str:
    return safe_name(f"{cfg.resource_name_prefix}_{base}")


def make_providers_tf(cfg: GeneratorConfig) -> str:
    return f'''terraform {{
  required_providers {{
    okta = {{
      source  = "okta/okta"
      version = "{cfg.provider_version_constraint}"
    }}
  }}
}}

provider "okta" {{
  org_name  = var.okta_org_name
  base_url  = var.okta_base_url
  api_token = var.okta_api_token
}}
'''


def make_variables_tf() -> str:
    return '''variable "okta_org_name" {
  description = "Okta org name, for example dev-12345678 or company-name."
  type        = string
}

variable "okta_base_url" {
  description = "Okta base URL domain segment, for example okta.com, okta-emea.com, or oktapreview.com."
  type        = string
  default     = "okta.com"
}

variable "okta_api_token" {
  description = "Okta API token used by the Terraform Okta provider."
  type        = string
  sensitive   = true
}
'''


def make_outputs_tf(resources: list[GeneratedResource]) -> str:
    lines = ["# Starter outputs. Review before using in production.\n"]
    if any(r.resource_type == "okta_group" for r in resources):
        lines.append('output "generated_group_ids" {')
        lines.append('  value = {')
        for r in resources:
            if r.resource_type == "okta_group":
                lines.append(f'    {r.resource_name} = okta_group.{r.resource_name}.id')
        lines.append('  }')
        lines.append('}\n')
    return "\n".join(lines)


def group_hcl(group: dict[str, Any], cfg: GeneratorConfig) -> tuple[str, GeneratedResource]:
    profile = group.get("profile") if isinstance(group.get("profile"), dict) else {}
    name = profile.get("name") or group.get("name") or group.get("id") or "group"
    desc = profile.get("description") or group.get("description") or ""
    res_name = prefixed(cfg, f"group_{name}")
    attrs = {
        "name": hcl_string(name),
        "description": hcl_string(desc),
    }
    hcl = tf_resource(
        "okta_group",
        res_name,
        attrs,
        comments=[f"Source group ID: {group.get('id', 'unknown')}"]
    )
    return hcl, GeneratedResource("okta_group", res_name, "groups", group.get("id"), name, "groups.tf", group.get("id"))


def trusted_origin_hcl(origin: dict[str, Any], cfg: GeneratorConfig) -> tuple[str, GeneratedResource]:
    name = origin.get("name") or origin.get("origin") or origin.get("id") or "trusted_origin"
    res_name = prefixed(cfg, f"trusted_origin_{name}")
    scopes = origin.get("scopes") or []
    scope_types = []
    for scope in scopes:
        if isinstance(scope, dict) and scope.get("type"):
            scope_types.append(scope["type"])
        elif isinstance(scope, str):
            scope_types.append(scope)
    attrs = {
        "name": hcl_string(name),
        "origin": hcl_string(origin.get("origin")),
        "scopes": hcl_list(scope_types),
        "active": hcl_bool(origin.get("status", "ACTIVE") == "ACTIVE"),
    }
    hcl = tf_resource("okta_trusted_origin", res_name, attrs, comments=[f"Source trusted origin ID: {origin.get('id', 'unknown')}"])
    return hcl, GeneratedResource("okta_trusted_origin", res_name, "trusted_origins", origin.get("id"), origin.get("origin") or name, "trusted_origins.tf", origin.get("id"))


def network_zone_hcl(zone: dict[str, Any], cfg: GeneratorConfig) -> tuple[str, GeneratedResource]:
    name = zone.get("name") or zone.get("id") or "network_zone"
    res_name = prefixed(cfg, f"network_zone_{name}")
    attrs = {
        "name": hcl_string(name),
        "type": hcl_string(zone.get("type", "IP")),
        "usage": hcl_string(zone.get("usage", "POLICY")),
    }
    if isinstance(zone.get("gateways"), list):
        attrs["gateways"] = hcl_list(zone.get("gateways"))
    if isinstance(zone.get("proxies"), list):
        attrs["proxies"] = hcl_list(zone.get("proxies"))
    hcl = tf_resource("okta_network_zone", res_name, attrs, comments=[f"Source network zone ID: {zone.get('id', 'unknown')}"])
    return hcl, GeneratedResource("okta_network_zone", res_name, "network_zones", zone.get("id"), name, "network_zones.tf", zone.get("id"))


def oauth_app_hcl(app: dict[str, Any], cfg: GeneratorConfig) -> tuple[str, GeneratedResource] | None:
    if app.get("signOnMode") != "OPENID_CONNECT" and app.get("name") != "oidc_client":
        return None
    label = app.get("label") or app.get("id") or "oidc_app"
    settings = app.get("settings") if isinstance(app.get("settings"), dict) else {}
    oauth = settings.get("oauthClient") if isinstance(settings.get("oauthClient"), dict) else {}
    app_type = oauth.get("application_type") or oauth.get("applicationType") or "web"
    grant_types = oauth.get("grant_types") or oauth.get("grantTypes") or []
    redirect_uris = oauth.get("redirect_uris") or oauth.get("redirectUris") or []
    response_types = oauth.get("response_types") or oauth.get("responseTypes") or []
    res_name = prefixed(cfg, f"app_oauth_{label}")
    attrs = {
        "label": hcl_string(label),
        "type": hcl_string(app_type),
        "grant_types": hcl_list(grant_types),
        "redirect_uris": hcl_list(redirect_uris),
        "response_types": hcl_list(response_types),
        "status": hcl_string(app.get("status", "ACTIVE")),
    }
    hcl = tf_resource(
        "okta_app_oauth",
        res_name,
        attrs,
        comments=[
            f"Source app ID: {app.get('id', 'unknown')}",
            "Starter HCL only. Review app grants, URIs, assignments, policies, and secrets before apply.",
        ],
    )
    return hcl, GeneratedResource("okta_app_oauth", res_name, "applications", app.get("id"), label, "applications.tf", app.get("id"))


def saml_app_hcl(app: dict[str, Any], cfg: GeneratorConfig) -> tuple[str, GeneratedResource] | None:
    if app.get("signOnMode") != "SAML_2_0":
        return None
    label = app.get("label") or app.get("id") or "saml_app"
    res_name = prefixed(cfg, f"app_saml_{label}")
    settings = app.get("settings") if isinstance(app.get("settings"), dict) else {}
    sign_on = settings.get("signOn") if isinstance(settings.get("signOn"), dict) else {}
    attrs = {
        "label": hcl_string(label),
        "sso_url": hcl_string(sign_on.get("ssoAcsUrl") or sign_on.get("sso_url")),
        "recipient": hcl_string(sign_on.get("recipient")),
        "destination": hcl_string(sign_on.get("destination")),
        "audience": hcl_string(sign_on.get("audience")),
        "subject_name_id_template": hcl_string(sign_on.get("subjectNameIdTemplate")),
        "subject_name_id_format": hcl_string(sign_on.get("subjectNameIdFormat")),
    }
    # Remove attrs with null values; SAML backup shapes vary significantly.
    attrs = {k: v for k, v in attrs.items() if v != "null"}
    hcl = tf_resource("okta_app_saml", res_name, attrs, comments=[f"Source SAML app ID: {app.get('id', 'unknown')}", "Review SAML settings before apply."])
    return hcl, GeneratedResource("okta_app_saml", res_name, "applications", app.get("id"), label, "applications.tf", app.get("id"))


def auth_server_hcl(server: dict[str, Any], cfg: GeneratorConfig) -> tuple[str, GeneratedResource]:
    name = server.get("name") or server.get("id") or "authorization_server"
    res_name = prefixed(cfg, f"auth_server_{name}")
    audiences = server.get("audiences") or server.get("audience") or []
    if isinstance(audiences, str):
        audiences = [audiences]
    attrs = {
        "name": hcl_string(name),
        "description": hcl_string(server.get("description", "")),
        "audiences": hcl_list(audiences),
        "status": hcl_string(server.get("status", "ACTIVE")),
    }
    hcl = tf_resource("okta_auth_server", res_name, attrs, comments=[f"Source authorization server ID: {server.get('id', 'unknown')}"])
    return hcl, GeneratedResource("okta_auth_server", res_name, "authorization_servers", server.get("id"), name, "authorization_servers.tf", server.get("id"))


def auth_server_child_resources(server: dict[str, Any], details: dict[str, Any], cfg: GeneratorConfig) -> tuple[list[str], list[GeneratedResource], list[dict[str, Any]]]:
    server_id = server.get("id")
    server_name = server.get("name") or server_id or "authorization_server"
    server_res_name = prefixed(cfg, f"auth_server_{server_name}")
    detail = details.get(server_id, {}) if isinstance(details, dict) and server_id else {}
    hcls: list[str] = []
    resources: list[GeneratedResource] = []
    manual: list[dict[str, Any]] = []

    for scope in detail.get("scopes", []) if isinstance(detail, dict) else []:
        if not isinstance(scope, dict):
            continue
        name = scope.get("name") or scope.get("id") or "scope"
        res_name = prefixed(cfg, f"scope_{server_name}_{name}")
        attrs = {
            "auth_server_id": f"okta_auth_server.{server_res_name}.id",
            "name": hcl_string(name),
            "description": hcl_string(scope.get("description", "")),
            "consent": hcl_string(scope.get("consent", "IMPLICIT")),
            "metadata_publish": hcl_string(scope.get("metadataPublish", "NO_CLIENTS")),
            "default": hcl_bool(scope.get("default", False)),
        }
        hcls.append(tf_resource("okta_auth_server_scope", res_name, attrs, comments=[f"Source scope ID: {scope.get('id', 'unknown')}" ]))
        resources.append(GeneratedResource("okta_auth_server_scope", res_name, "authorization_server_scopes", scope.get("id"), f"{server_name}::{name}", "authorization_server_scopes.tf", f"{server_id}/{scope.get('id')}" if server_id and scope.get("id") else None))

    for claim in detail.get("claims", []) if isinstance(detail, dict) else []:
        if not isinstance(claim, dict):
            continue
        name = claim.get("name") or claim.get("id") or "claim"
        res_name = prefixed(cfg, f"claim_{server_name}_{name}")
        attrs = {
            "auth_server_id": f"okta_auth_server.{server_res_name}.id",
            "name": hcl_string(name),
            "value": hcl_string(claim.get("value")),
            "claim_type": hcl_string(claim.get("claimType") or claim.get("claim_type") or "RESOURCE"),
            "value_type": hcl_string(claim.get("valueType") or claim.get("value_type") or "EXPRESSION"),
            "always_include_in_token": hcl_bool(claim.get("alwaysIncludeInToken", False)),
        }
        hcls.append(tf_resource("okta_auth_server_claim", res_name, attrs, comments=[f"Source claim ID: {claim.get('id', 'unknown')}", "Review claim value expressions before apply."]))
        resources.append(GeneratedResource("okta_auth_server_claim", res_name, "authorization_server_claims", claim.get("id"), f"{server_name}::{name}", "authorization_server_claims.tf", f"{server_id}/{claim.get('id')}" if server_id and claim.get("id") else None))

    for key in ("policies", "policyRules", "rules"):
        if isinstance(detail, dict) and detail.get(key):
            manual.append({
                "resource": "authorization_server_policy_rules" if key != "policies" else "authorization_server_policies",
                "sourceId": server_id,
                "name": server_name,
                "reason": f"Authorization server {key} require rule/order review before Terraform apply.",
            })
    return hcls, resources, manual


def generate(cfg: GeneratorConfig) -> GenerationResult:
    backup = load_backup(cfg.backup_dir, cfg.include)
    gen_id = now_id()
    output_dir = cfg.output_dir / gen_id
    output_dir.mkdir(parents=True, exist_ok=True)

    tf_files: dict[str, list[str]] = {
        "groups.tf": [],
        "applications.tf": [],
        "trusted_origins.tf": [],
        "network_zones.tf": [],
        "authorization_servers.tf": [],
        "authorization_server_scopes.tf": [],
        "authorization_server_claims.tf": [],
        "manual_review.tf": [],
    }
    generated: list[GeneratedResource] = []
    unsupported: list[dict[str, Any]] = []
    manual_review: list[dict[str, Any]] = []

    if "groups" in cfg.include:
        for group in backup.groups:
            hcl, res = group_hcl(group, cfg)
            tf_files[res.hcl_file].append(hcl)
            generated.append(res)

    if "applications" in cfg.include:
        for app in backup.applications:
            result = oauth_app_hcl(app, cfg) or saml_app_hcl(app, cfg)
            if result:
                hcl, res = result
                tf_files[res.hcl_file].append(hcl)
                generated.append(res)
            else:
                unsupported.append({
                    "resource": "applications",
                    "sourceId": app.get("id"),
                    "name": app.get("label") or app.get("name"),
                    "reason": f"Application type/signOnMode not supported for starter HCL: {app.get('name')} / {app.get('signOnMode')}",
                })

    if "trusted_origins" in cfg.include:
        for origin in backup.trusted_origins:
            hcl, res = trusted_origin_hcl(origin, cfg)
            tf_files[res.hcl_file].append(hcl)
            generated.append(res)

    if "network_zones" in cfg.include:
        for zone in backup.network_zones:
            hcl, res = network_zone_hcl(zone, cfg)
            tf_files[res.hcl_file].append(hcl)
            generated.append(res)

    if "authorization_servers" in cfg.include:
        for server in backup.authorization_servers:
            hcl, res = auth_server_hcl(server, cfg)
            tf_files[res.hcl_file].append(hcl)
            generated.append(res)
            child_hcls, child_resources, child_manual = auth_server_child_resources(server, backup.authorization_server_details, cfg)
            for child_hcl in child_hcls:
                if '"okta_auth_server_scope"' in child_hcl:
                    tf_files["authorization_server_scopes.tf"].append(child_hcl)
                elif '"okta_auth_server_claim"' in child_hcl:
                    tf_files["authorization_server_claims.tf"].append(child_hcl)
            generated.extend(child_resources)
            manual_review.extend(child_manual)

    if "policies" in cfg.include:
        for policy in backup.policies:
            manual_review.append({
                "resource": "policies",
                "sourceId": policy.get("id"),
                "name": policy.get("name"),
                "type": policy.get("type"),
                "reason": "Policy HCL generation is manual-review only because policies and rules depend on priority, groups, zones, devices, and security impact.",
            })

    if "identity_providers" in cfg.include:
        for idp in backup.identity_providers:
            manual_review.append({
                "resource": "identity_providers",
                "sourceId": idp.get("id"),
                "name": idp.get("name") or idp.get("label"),
                "type": idp.get("type"),
                "reason": "Identity provider HCL requires secret/certificate re-entry and trust validation before apply.",
            })

    write_text(output_dir / "providers.tf", make_providers_tf(cfg))
    write_text(output_dir / "variables.tf", make_variables_tf())
    write_text(output_dir / "outputs.tf", make_outputs_tf(generated))

    for filename, chunks in tf_files.items():
        if chunks:
            write_text(output_dir / filename, "\n".join(chunks))

    if cfg.generate_import_suggestions:
        write_imports(output_dir / "terraform_imports.sh", output_dir / "imports.tf", generated)
    write_mapping_csv(output_dir / "resource_mapping.csv", generated)
    write_unsupported_csv(output_dir / "unsupported_resources.csv", unsupported)
    write_manual_review_csv(output_dir / "manual_review_items.csv", manual_review)

    status = "PASS"
    warnings = []
    if backup.missing_files:
        warnings.append("One or more requested backup files were missing.")
        status = "WARN"
    if unsupported or manual_review:
        status = "WARN"
    if cfg.strict_mode and (backup.missing_files or unsupported):
        status = "FAIL"

    result = GenerationResult(
        generation_id=gen_id,
        backup_dir=str(cfg.backup_dir),
        output_dir=str(output_dir),
        status=status,
        include=cfg.include,
        generated_resources=generated,
        unsupported=unsupported,
        manual_review=manual_review,
        missing_files=backup.missing_files,
        warnings=warnings,
    )
    write_json(output_dir / "hcl_generation_plan.json", result.to_dict())
    if cfg.write_markdown:
        write_text(output_dir / "hcl_generation_report.md", make_report(result))
        write_text(output_dir / "execution_report.md", make_execution_report(result))
    return result


def write_imports(command_path: Path, block_path: Path, resources: list[GeneratedResource]) -> None:
    cmd_lines = ["#!/usr/bin/env bash", "set -euo pipefail", "", "# Review these import commands before running."]
    block_lines = ["# Terraform import blocks. Review before using."]
    for res in resources:
        if not res.import_id:
            continue
        address = f"{res.resource_type}.{res.resource_name}"
        cmd_lines.append(f"terraform import {address} {res.import_id}")
        block_lines.append("import {")
        block_lines.append(f"  to = {address}")
        block_lines.append(f"  id = \"{res.import_id}\"")
        block_lines.append("}\n")
    write_text(command_path, "\n".join(cmd_lines) + "\n")
    write_text(block_path, "\n".join(block_lines) + "\n")


def write_mapping_csv(path: Path, resources: list[GeneratedResource]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["resource_type", "resource_name", "source_type", "source_id", "natural_key", "hcl_file", "import_id", "status", "notes"])
        writer.writeheader()
        for r in resources:
            writer.writerow(r.__dict__)


def write_unsupported_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = ["resource", "sourceId", "name", "reason"]
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fields})


def write_manual_review_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = ["resource", "sourceId", "name", "type", "reason"]
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fields})


def make_report(result: GenerationResult) -> str:
    lines = [
        f"# Okta HCL Generation Report",
        "",
        f"Generation ID: `{result.generation_id}`",
        f"Status: `{result.status}`",
        f"Backup Directory: `{result.backup_dir}`",
        f"Output Directory: `{result.output_dir}`",
        "",
        "## Summary",
        "",
        f"- Generated resources: {len(result.generated_resources)}",
        f"- Unsupported resources: {len(result.unsupported)}",
        f"- Manual review items: {len(result.manual_review)}",
        f"- Missing files: {len(result.missing_files)}",
        "",
    ]
    if result.missing_files:
        lines.append("## Missing Files")
        lines.append("")
        lines.extend(f"- `{item}`" for item in result.missing_files)
        lines.append("")
    if result.unsupported:
        lines.append("## Unsupported Resources")
        lines.append("")
        for item in result.unsupported:
            lines.append(f"- {item.get('resource')} `{item.get('name')}`: {item.get('reason')}")
        lines.append("")
    if result.manual_review:
        lines.append("## Manual Review Items")
        lines.append("")
        for item in result.manual_review:
            lines.append(f"- {item.get('resource')} `{item.get('name')}`: {item.get('reason')}")
        lines.append("")
    lines.append("## Files to Review")
    lines.append("")
    lines.extend([
        "- `providers.tf`",
        "- `variables.tf`",
        "- `outputs.tf`",
        "- `*.tf` resource files",
        "- `terraform_imports.sh`",
        "- `imports.tf`",
        "- `resource_mapping.csv`",
        "- `manual_review_items.csv`",
    ])
    lines.append("")
    lines.append("WARNING: These utilities have limited testing and are provided as-is with no warranty. Use at your own risk.")
    return "\n".join(lines) + "\n"


def make_execution_report(result: GenerationResult) -> str:
    return f"""# Execution Report

Utility: okta-hcl-generator
Generation ID: `{result.generation_id}`
Status: `{result.status}`
Backup Directory: `{result.backup_dir}`
Output Directory: `{result.output_dir}`

Generated resources: {len(result.generated_resources)}
Unsupported resources: {len(result.unsupported)}
Manual review items: {len(result.manual_review)}
Missing files: {len(result.missing_files)}

WARNING: These utilities have limited testing and are provided as-is with no warranty. Use at your own risk.
"""
