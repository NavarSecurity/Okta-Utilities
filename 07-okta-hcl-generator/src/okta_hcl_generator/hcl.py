from __future__ import annotations

import re
import json
from typing import Any


def safe_name(value: str | None, fallback: str = "resource") -> str:
    raw = (value or fallback).strip().lower()
    raw = re.sub(r"[^a-z0-9_]+", "_", raw)
    raw = re.sub(r"_+", "_", raw).strip("_")
    if not raw:
        raw = fallback
    if re.match(r"^[0-9]", raw):
        raw = f"r_{raw}"
    return raw[:80]


def hcl_string(value: Any) -> str:
    if value is None:
        return "null"
    return json.dumps(str(value))


def hcl_bool(value: Any) -> str:
    return "true" if bool(value) else "false"


def hcl_list(values: list[Any] | None) -> str:
    if not values:
        return "[]"
    return "[" + ", ".join(json.dumps(v) for v in values) + "]"


def compact_comment(text: str) -> str:
    return "# " + str(text).replace("\n", " ")


def tf_resource(resource_type: str, name: str, attrs: dict[str, str], comments: list[str] | None = None) -> str:
    lines: list[str] = []
    if comments:
        lines.extend(compact_comment(c) for c in comments)
    lines.append(f'resource "{resource_type}" "{name}" {{')
    for key, value in attrs.items():
        if value is None:
            continue
        lines.append(f"  {key} = {value}")
    lines.append("}")
    return "\n".join(lines) + "\n"
