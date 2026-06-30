from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .io_utils import read_json
from .normalizers import (
    normalize_applications,
    normalize_authorization_servers,
    normalize_groups,
    normalize_identity_providers,
    normalize_network_zones,
    normalize_policies,
    normalize_trusted_origins,
)


@dataclass
class BackupData:
    backup_dir: Path
    manifest: dict[str, Any] = field(default_factory=dict)
    groups: list[dict[str, Any]] = field(default_factory=list)
    applications: list[dict[str, Any]] = field(default_factory=list)
    trusted_origins: list[dict[str, Any]] = field(default_factory=list)
    network_zones: list[dict[str, Any]] = field(default_factory=list)
    authorization_servers: list[dict[str, Any]] = field(default_factory=list)
    authorization_server_details: dict[str, Any] = field(default_factory=dict)
    policies: list[dict[str, Any]] = field(default_factory=list)
    identity_providers: list[dict[str, Any]] = field(default_factory=list)
    missing_files: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def optional_read_json(backup_dir: Path, filename: str, missing: list[str]) -> Any | None:
    path = backup_dir / filename
    if not path.exists():
        missing.append(filename)
        return None
    return read_json(path)


def load_backup(backup_dir: Path, include: list[str]) -> BackupData:
    if not backup_dir.exists():
        raise FileNotFoundError(f"Backup directory not found: {backup_dir}")
    data = BackupData(backup_dir=backup_dir)

    manifest_path = backup_dir / "manifest.json"
    if manifest_path.exists():
        data.manifest = read_json(manifest_path)

    if "groups" in include:
        raw = optional_read_json(backup_dir, "groups.json", data.missing_files)
        if raw is not None:
            data.groups = normalize_groups(raw)

    if "applications" in include:
        raw = optional_read_json(backup_dir, "applications.json", data.missing_files)
        if raw is not None:
            data.applications = normalize_applications(raw)

    if "trusted_origins" in include:
        raw = optional_read_json(backup_dir, "trusted_origins.json", data.missing_files)
        if raw is not None:
            data.trusted_origins = normalize_trusted_origins(raw)

    if "network_zones" in include:
        raw = optional_read_json(backup_dir, "network_zones.json", data.missing_files)
        if raw is not None:
            data.network_zones = normalize_network_zones(raw)

    auth_related = {
        "authorization_servers",
        "authorization_server_scopes",
        "authorization_server_claims",
        "authorization_server_policies",
        "authorization_server_policy_rules",
    }
    if auth_related.intersection(include):
        raw = optional_read_json(backup_dir, "authorization_servers.json", data.missing_files)
        if raw is not None:
            data.authorization_servers, data.authorization_server_details = normalize_authorization_servers(raw)

    if "policies" in include:
        raw = optional_read_json(backup_dir, "policies.json", data.missing_files)
        if raw is not None:
            data.policies = normalize_policies(raw)

    if "identity_providers" in include:
        raw = optional_read_json(backup_dir, "identity_providers.json", data.missing_files)
        if raw is not None:
            data.identity_providers = normalize_identity_providers(raw)

    return data
