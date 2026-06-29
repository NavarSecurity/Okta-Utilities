from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Literal

Severity = Literal["PASS", "WARN", "FAIL"]


@dataclass
class CheckResult:
    severity: Severity
    code: str
    message: str
    resource: str | None = None
    file: str | None = None
    details: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        return {key: value for key, value in data.items() if value not in (None, {}, [])}


class CheckRecorder:
    def __init__(self) -> None:
        self.results: list[CheckResult] = []

    def pass_(self, code: str, message: str, *, resource: str | None = None, file: str | None = None, details: dict[str, Any] | None = None) -> None:
        self.results.append(CheckResult("PASS", code, message, resource, file, details))

    def warn(self, code: str, message: str, *, resource: str | None = None, file: str | None = None, details: dict[str, Any] | None = None) -> None:
        self.results.append(CheckResult("WARN", code, message, resource, file, details))

    def fail(self, code: str, message: str, *, resource: str | None = None, file: str | None = None, details: dict[str, Any] | None = None) -> None:
        self.results.append(CheckResult("FAIL", code, message, resource, file, details))

    def counts(self) -> dict[str, int]:
        summary = {"PASS": 0, "WARN": 0, "FAIL": 0}
        for item in self.results:
            summary[item.severity] += 1
        return summary

    def overall_status(self, fail_on_warnings: bool = False) -> str:
        counts = self.counts()
        if counts["FAIL"]:
            return "FAIL"
        if counts["WARN"]:
            return "FAIL" if fail_on_warnings else "WARN"
        return "PASS"
