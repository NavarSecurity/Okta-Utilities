from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
import json

DEFAULT_INCLUDE = [
    "groups",
    "applications",
    "trusted_origins",
    "network_zones",
    "authorization_servers",
    "authorization_server_scopes",
    "authorization_server_claims",
    "policies",
    "identity_providers",
]

SUPPORTED_INCLUDE = set(DEFAULT_INCLUDE)


@dataclass
class GeneratorConfig:
    backup_dir: Path = Path("input/source-backup")
    output_dir: Path = Path("output")
    include: list[str] = field(default_factory=lambda: DEFAULT_INCLUDE.copy())
    resource_name_prefix: str = "okta"
    provider_version_constraint: str = "~> 4.0"
    module_mode: bool = False
    generate_import_suggestions: bool = True
    generate_manual_review_file: bool = True
    write_markdown: bool = True
    strict_mode: bool = False
    max_json_preview_chars: int = 300

    @classmethod
    def from_file(cls, path: str | Path | None) -> "GeneratorConfig":
        if not path:
            return cls()
        p = Path(path)
        if not p.exists():
            raise FileNotFoundError(f"Config file not found: {p}")
        raw = json.loads(p.read_text(encoding="utf-8"))
        return cls.from_dict(raw)

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "GeneratorConfig":
        cfg = cls()
        if "backupDir" in raw:
            cfg.backup_dir = Path(raw["backupDir"])
        if "outputDir" in raw:
            cfg.output_dir = Path(raw["outputDir"])
        if "include" in raw:
            cfg.include = list(raw["include"])
        if "resourceNamePrefix" in raw:
            cfg.resource_name_prefix = str(raw["resourceNamePrefix"])
        if "providerVersionConstraint" in raw:
            cfg.provider_version_constraint = str(raw["providerVersionConstraint"])
        if "moduleMode" in raw:
            cfg.module_mode = bool(raw["moduleMode"])
        if "generateImportSuggestions" in raw:
            cfg.generate_import_suggestions = bool(raw["generateImportSuggestions"])
        if "generateManualReviewFile" in raw:
            cfg.generate_manual_review_file = bool(raw["generateManualReviewFile"])
        if "writeMarkdown" in raw:
            cfg.write_markdown = bool(raw["writeMarkdown"])
        if "strictMode" in raw:
            cfg.strict_mode = bool(raw["strictMode"])
        if "maxJsonPreviewChars" in raw:
            cfg.max_json_preview_chars = int(raw["maxJsonPreviewChars"])
        cfg.validate()
        return cfg

    def apply_overrides(
        self,
        backup_dir: str | None = None,
        output_dir: str | None = None,
        include: str | None = None,
        resource_name_prefix: str | None = None,
        strict: bool | None = None,
    ) -> "GeneratorConfig":
        if backup_dir:
            self.backup_dir = Path(backup_dir)
        if output_dir:
            self.output_dir = Path(output_dir)
        if include:
            self.include = [item.strip() for item in include.split(",") if item.strip()]
        if resource_name_prefix:
            self.resource_name_prefix = resource_name_prefix
        if strict is not None and strict:
            self.strict_mode = True
        self.validate()
        return self

    def validate(self) -> None:
        if not self.include:
            raise ValueError("At least one resource type must be included.")
        unknown = sorted(set(self.include) - SUPPORTED_INCLUDE)
        if unknown:
            raise ValueError(f"Unsupported include value(s): {', '.join(unknown)}")
