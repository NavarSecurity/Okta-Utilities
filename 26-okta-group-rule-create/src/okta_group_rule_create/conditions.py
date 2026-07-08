from __future__ import annotations

import json
import re
from typing import Any

from .config import ConfigError

_ATTRIBUTE_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*(\.[A-Za-z_][A-Za-z0-9_]*)*$")

_OPERATOR_ALIASES = {
    "equals": "equals",
    "equal": "equals",
    "is": "equals",
    "==": "equals",
    "not_equals": "notEquals",
    "notequals": "notEquals",
    "not equals": "notEquals",
    "is_not": "notEquals",
    "is not": "notEquals",
    "!=": "notEquals",
    "contains": "contains",
    "does_not_contain": "notContains",
    "does not contain": "notContains",
    "not_contains": "notContains",
    "notcontains": "notContains",
    "starts_with": "startsWith",
    "starts with": "startsWith",
    "startswith": "startsWith",
    "ends_with": "endsWith",
    "ends with": "endsWith",
    "endswith": "endsWith",
    "is_present": "isPresent",
    "is present": "isPresent",
    "present": "isPresent",
    "exists": "isPresent",
    "is_blank": "isBlank",
    "is blank": "isBlank",
    "blank": "isBlank",
    "empty": "isBlank",
    "greater_than": "greaterThan",
    "greater than": "greaterThan",
    ">": "greaterThan",
    "greater_than_or_equals": "greaterThanOrEquals",
    "greater than or equals": "greaterThanOrEquals",
    ">=": "greaterThanOrEquals",
    "less_than": "lessThan",
    "less than": "lessThan",
    "<": "lessThan",
    "less_than_or_equals": "lessThanOrEquals",
    "less than or equals": "lessThanOrEquals",
    "<=": "lessThanOrEquals",
}


def _normalize_operator(value: Any) -> str:
    raw = str(value or "").strip()
    if not raw:
        raise ConfigError("Basic condition is missing operator.")
    key = raw.replace("-", "_").strip().lower()
    operator = _OPERATOR_ALIASES.get(key)
    if not operator:
        allowed = sorted(set(_OPERATOR_ALIASES.values()))
        raise ConfigError(f"Unsupported basic condition operator {raw!r}. Supported normalized operators: {', '.join(allowed)}.")
    return operator


def _attribute_ref(attribute: Any) -> str:
    raw = str(attribute or "").strip()
    if not raw:
        raise ConfigError("Basic condition is missing attribute.")
    if raw.startswith("user."):
        path = raw[5:]
        prefix = "user."
    else:
        path = raw
        prefix = "user."
    if not _ATTRIBUTE_RE.match(path):
        raise ConfigError(
            f"Invalid basic condition attribute {raw!r}. Use simple Okta profile fields such as department, email, title, or user.department."
        )
    return f"{prefix}{path}"


def _literal(value: Any, *, value_type: str = "string") -> str:
    normalized_type = str(value_type or "string").strip().lower()
    if value is None:
        return "null"
    if normalized_type in {"number", "integer", "float"}:
        try:
            float(value)
        except (TypeError, ValueError) as exc:
            raise ConfigError(f"Basic condition numeric value {value!r} is not a valid number.") from exc
        return str(value)
    if normalized_type in {"boolean", "bool"}:
        if isinstance(value, bool):
            return "true" if value else "false"
        lowered = str(value).strip().lower()
        if lowered in {"true", "1", "yes", "y"}:
            return "true"
        if lowered in {"false", "0", "no", "n"}:
            return "false"
        raise ConfigError(f"Basic condition boolean value {value!r} is not valid.")
    return json.dumps(str(value))


def _value_required(condition: dict[str, Any], operator: str) -> Any:
    if operator in {"isPresent", "isBlank"}:
        return None
    if "value" not in condition:
        raise ConfigError(f"Basic condition operator {operator!r} requires a value.")
    return condition.get("value")


def build_basic_condition_expression(condition: dict[str, Any]) -> str:
    if not isinstance(condition, dict):
        raise ConfigError("basicCondition entries must be objects.")
    attribute = _attribute_ref(condition.get("attribute") or condition.get("field") or condition.get("profileField"))
    operator = _normalize_operator(condition.get("operator"))
    value = _value_required(condition, operator)
    value_type = str(condition.get("valueType", "string"))
    literal = _literal(value, value_type=value_type)

    if operator == "equals":
        return f"{attribute} == {literal}"
    if operator == "notEquals":
        return f"{attribute} != {literal}"
    if operator == "contains":
        return f"String.stringContains({attribute}, {literal})"
    if operator == "notContains":
        return f"!String.stringContains({attribute}, {literal})"
    if operator == "startsWith":
        return f"String.startsWith({attribute}, {literal})"
    if operator == "endsWith":
        return f"String.endsWith({attribute}, {literal})"
    if operator == "isPresent":
        return f"({attribute} != null && {attribute} != \"\")"
    if operator == "isBlank":
        return f"({attribute} == null || {attribute} == \"\")"
    if operator == "greaterThan":
        return f"{attribute} > {literal}"
    if operator == "greaterThanOrEquals":
        return f"{attribute} >= {literal}"
    if operator == "lessThan":
        return f"{attribute} < {literal}"
    if operator == "lessThanOrEquals":
        return f"{attribute} <= {literal}"
    raise ConfigError(f"Unsupported basic condition operator {operator!r}.")


def resolve_rule_expression(item: dict[str, Any], rule_name: str) -> tuple[str, str, Any]:
    expression = str(item.get("expression", "")).strip()
    has_basic_condition = item.get("basicCondition") not in (None, "")
    has_basic_conditions = item.get("basicConditions") not in (None, "")

    if expression and (has_basic_condition or has_basic_conditions):
        raise ConfigError(f"Rule {rule_name!r} must use either expression or basicCondition/basicConditions, not both.")
    if expression:
        return expression, "expression", None

    if has_basic_condition:
        basic = item.get("basicCondition")
        return build_basic_condition_expression(basic), "basicCondition", basic

    if has_basic_conditions:
        raw = item.get("basicConditions")
        match_mode = "all"
        conditions: list[Any]
        if isinstance(raw, list):
            conditions = raw
        elif isinstance(raw, dict):
            match_mode = str(raw.get("match", raw.get("matchType", "all"))).strip().lower()
            conditions = raw.get("conditions") or []
        else:
            raise ConfigError(f"Rule {rule_name!r} basicConditions must be a list or object.")

        if match_mode not in {"all", "any"}:
            raise ConfigError(f"Rule {rule_name!r} basicConditions.match must be either all or any.")
        if not isinstance(conditions, list) or not conditions:
            raise ConfigError(f"Rule {rule_name!r} basicConditions must include at least one condition.")

        joiner = " && " if match_mode == "all" else " || "
        expressions = [build_basic_condition_expression(condition) for condition in conditions]
        joined = joiner.join(f"({expr})" for expr in expressions)
        return joined, "basicConditions", raw

    raise ConfigError(f"Rule {rule_name!r} must include expression, basicCondition, or basicConditions.")
