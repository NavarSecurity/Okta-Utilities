from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

# Use exact/key-canonical matching instead of loose substring matching.
# Loose matching caused false positives for normal Okta config keys such as
# authorizationServers, detailsByAuthorizationServerId, passwordChange, and
# selfServicePasswordReset.
SENSITIVE_CANONICAL_KEYS = {
    "apikey",
    "apitoken",
    "authorization",
    "authheader",
    "bearer",
    "bearertoken",
    "clientsecret",
    "idtoken",
    "password",
    "passwd",
    "passphrase",
    "privatekey",
    "refreshtoken",
    "secret",
    "secretkey",
    "sharedsecret",
    "token",
    "accesstoken",
}

REDACTED_VALUES = {
    "",
    "***",
    "***REDACTED***",
    "REDACTED",
    "<redacted>",
    "[REDACTED]",
    "null",
}


@dataclass
class SensitiveFinding:
    file: str
    path: str
    key: str
    value: str
    value_preview: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def canonical_key(key: str) -> str:
    return "".join(ch for ch in str(key).lower() if ch.isalnum())


def is_sensitive_key(key: str) -> bool:
    return canonical_key(key) in SENSITIVE_CANONICAL_KEYS


def is_scalar(value: Any) -> bool:
    return value is None or isinstance(value, str | bool | int | float)


def looks_redacted(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, bool | int | float):
        return True
    text = str(value).strip()
    if text in REDACTED_VALUES:
        return True
    if "REDACT" in text.upper() or text in {"*****", "********"}:
        return True
    return False


def exact_value(value: Any) -> str:
    return str(value).replace("\n", " ").strip()


def preview(value: Any, max_len: int = 24) -> str:
    text = exact_value(value)
    if len(text) <= max_len:
        return text
    return f"{text[:8]}...{text[-4:]}"


def scan_json_for_sensitive_values(data: Any, file_label: str, max_findings: int = 50) -> list[SensitiveFinding]:
    findings: list[SensitiveFinding] = []

    def walk(value: Any, path: str) -> None:
        if len(findings) >= max_findings:
            return
        if isinstance(value, dict):
            for key, child in value.items():
                child_path = f"{path}.{key}" if path else str(key)

                # Only flag exact sensitive key names when the value is scalar.
                # If a sensitive-looking key holds a dict/list, keep walking; a real
                # secret inside that object should be detected at the leaf value.
                if is_sensitive_key(str(key)) and is_scalar(child) and not looks_redacted(child):
                    findings.append(
                        SensitiveFinding(
                            file=file_label,
                            path=child_path,
                            key=str(key),
                            value=exact_value(child),
                            value_preview=preview(child),
                        )
                    )
                    if len(findings) >= max_findings:
                        return
                walk(child, child_path)
        elif isinstance(value, list):
            for idx, child in enumerate(value):
                walk(child, f"{path}[{idx}]")
                if len(findings) >= max_findings:
                    return

    walk(data, "")
    return findings


def scan_backup_files(backup_dir: Path, json_data_by_file: dict[str, Any], max_findings: int = 50) -> list[SensitiveFinding]:
    findings: list[SensitiveFinding] = []
    for file_name, data in json_data_by_file.items():
        if file_name == "manifest.json":
            continue
        remaining = max_findings - len(findings)
        if remaining <= 0:
            break
        findings.extend(scan_json_for_sensitive_values(data, file_name, remaining))
    return findings
