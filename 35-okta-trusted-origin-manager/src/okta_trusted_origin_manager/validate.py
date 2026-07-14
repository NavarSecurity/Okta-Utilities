from __future__ import annotations

from collections import Counter
from typing import Any
from urllib.parse import urlsplit

from .normalize import ALLOWED_SCOPE_TYPES, canonical_origin_url, extract_trusted_origins, scope_types


LOCALHOST_NAMES = {"localhost", "127.0.0.1", "::1"}


def _finding(index: int, severity: str, code: str, message: str, origin: dict[str, Any]) -> dict[str, Any]:
    return {
        "index": index,
        "severity": severity,
        "code": code,
        "message": message,
        "name": origin.get("name", ""),
        "origin": origin.get("origin", ""),
        "scopes": ",".join(scope_types(origin)),
    }


def _is_localhost(hostname: str | None) -> bool:
    if not hostname:
        return False
    return hostname.lower() in LOCALHOST_NAMES


def validate_trusted_origins(payload: Any, options: dict[str, Any] | None = None) -> dict[str, Any]:
    options = options or {}
    allow_http_localhost = bool(options.get("allowHttpLocalhost", True))
    allow_wildcard_for_iframe_only = bool(options.get("allowWildcardForIframeOnly", True))

    origins = extract_trusted_origins(payload)
    findings: list[dict[str, Any]] = []

    canonical_counts = Counter(canonical_origin_url(item.get("origin")) for item in origins)

    for index, item in enumerate(origins):
        origin_value = str(item.get("origin") or "").strip()
        scopes = scope_types(item)

        if not item.get("name"):
            findings.append(_finding(index, "WARNING", "MISSING_NAME", "Trusted origin has no name.", item))

        if not origin_value:
            findings.append(_finding(index, "ERROR", "MISSING_ORIGIN", "Trusted origin has no origin URL.", item))
            continue

        split = urlsplit(origin_value)
        if not split.scheme or not split.netloc:
            findings.append(_finding(index, "ERROR", "INVALID_ORIGIN_URL", "Origin must be an absolute URL with scheme and host.", item))
            continue

        if split.scheme.lower() not in {"http", "https"}:
            findings.append(_finding(index, "ERROR", "INVALID_SCHEME", "Origin scheme must be http or https.", item))

        if split.scheme.lower() == "http":
            if not (allow_http_localhost and _is_localhost(split.hostname)):
                findings.append(_finding(index, "WARNING", "HTTP_ORIGIN", "HTTP origin should be reviewed and avoided outside localhost development use.", item))

        if split.path not in {"", "/"} or split.query or split.fragment:
            findings.append(_finding(index, "WARNING", "ORIGIN_HAS_PATH_QUERY_OR_FRAGMENT", "Trusted origin should normally be scheme, host, and optional port only.", item))

        if "*" in origin_value:
            if any(scope in {"CORS", "REDIRECT"} for scope in scopes):
                findings.append(_finding(index, "ERROR", "WILDCARD_WITH_CORS_OR_REDIRECT", "Wildcard origins should not be used for CORS or redirect scopes.", item))
            elif "IFRAME_EMBED" in scopes and allow_wildcard_for_iframe_only:
                findings.append(_finding(index, "WARNING", "WILDCARD_IFRAME_REVIEW", "Wildcard iFrame origins should be reviewed before production use.", item))
            else:
                findings.append(_finding(index, "WARNING", "WILDCARD_ORIGIN", "Wildcard origin should be reviewed.", item))

        if not scopes:
            findings.append(_finding(index, "ERROR", "NO_SCOPES", "Trusted origin has no scopes.", item))

        for scope in scopes:
            if scope not in ALLOWED_SCOPE_TYPES:
                findings.append(_finding(index, "ERROR", "INVALID_SCOPE", f"Unsupported trusted origin scope: {scope}", item))

        canonical = canonical_origin_url(origin_value)
        if canonical and canonical_counts[canonical] > 1:
            findings.append(_finding(index, "WARNING", "DUPLICATE_ORIGIN", "Duplicate origin value found in input.", item))

    errors = [item for item in findings if item["severity"] == "ERROR"]
    warnings = [item for item in findings if item["severity"] == "WARNING"]
    return {
        "totalOrigins": len(origins),
        "errorCount": len(errors),
        "warningCount": len(warnings),
        "findings": findings,
    }
