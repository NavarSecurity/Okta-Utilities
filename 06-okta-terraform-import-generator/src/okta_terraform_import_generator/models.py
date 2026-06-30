from __future__ import annotations

from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class GeneratorConfig:
    backup_dir: Path
    output_dir: Path = Path("output")
    include: List[str] = field(default_factory=lambda: [
        "groups",
        "applications",
        "trusted_origins",
        "network_zones",
        "authorization_servers",
        "authorization_server_scopes",
        "authorization_server_claims",
        "authorization_server_policies",
        "authorization_server_policy_rules",
        "policies",
        "identity_providers",
    ])
    mode: str = "both"  # commands, blocks, both
    module_prefix: str = ""
    resource_name_prefix: str = ""
    max_resource_name_length: int = 80
    skip_system_objects: bool = False
    strict_mode: bool = False
    write_csv: bool = True
    write_markdown: bool = True
    include_unsupported: bool = True
    custom_resource_mappings: Dict[str, str] = field(default_factory=dict)
    app_resource_mappings: Dict[str, str] = field(default_factory=dict)
    idp_resource_mappings: Dict[str, str] = field(default_factory=dict)
    policy_resource_mappings: Dict[str, str] = field(default_factory=dict)

    def to_safe_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["backup_dir"] = str(self.backup_dir)
        data["output_dir"] = str(self.output_dir)
        return data


@dataclass
class ImportRecord:
    resource: str
    source_file: str
    object_id: str
    object_name: str
    terraform_type: str
    terraform_name: str
    terraform_address: str
    import_id: str
    command: str
    block: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class UnsupportedRecord:
    resource: str
    source_file: str
    object_id: str
    object_name: str
    reason: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class GenerationResult:
    status: str
    output_dir: str
    backup_dir: str
    total_imports: int
    total_unsupported: int
    counts_by_resource: Dict[str, int]
    imports: List[Dict[str, Any]]
    unsupported: List[Dict[str, Any]]
    warnings: List[str]
    errors: List[str]
