from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any

SEVERITY_ORDER = {"info": 0, "low": 1, "medium": 2, "high": 3, "critical": 4}

EVENT_RULES = [
    {
        "ruleId": "ADMIN_PRIVILEGE_ACTIVITY",
        "configKey": "adminActivity",
        "category": "Admin",
        "severity": "high",
        "patterns": [
            "user.account.privilege",
            "user.privilege",
            "system.admin",
            "iam.role",
            "role.assignment",
            "admin.role",
        ],
        "reason": "Administrative privilege or role activity detected.",
    },
    {
        "ruleId": "POLICY_CONFIGURATION_CHANGE",
        "configKey": "policyChanges",
        "category": "Policy",
        "severity": "high",
        "patterns": ["policy.lifecycle", "policy.rule", "policy.auth", "sign_on.policy", "access.policy"],
        "reason": "Policy or policy rule configuration activity detected.",
    },
    {
        "ruleId": "FACTOR_OR_AUTHENTICATOR_CHANGE",
        "configKey": "factorChanges",
        "category": "MFA",
        "severity": "high",
        "patterns": ["factor", "authenticator", "mfa"],
        "reason": "MFA factor or authenticator lifecycle activity detected.",
        "excludeOutcomes": ["SUCCESSFUL_AUTHENTICATION"],
    },
    {
        "ruleId": "API_TOKEN_ACTIVITY",
        "configKey": "apiTokenActivity",
        "category": "API Access",
        "severity": "high",
        "patterns": ["api.token", "token.lifecycle", "client_secret", "oauth2.client.secret"],
        "reason": "API token or OAuth client secret activity detected.",
    },
    {
        "ruleId": "USER_LIFECYCLE_CHANGE",
        "configKey": "userLifecycleChanges",
        "category": "User Lifecycle",
        "severity": "medium",
        "patterns": [
            "user.lifecycle.deactivate",
            "user.lifecycle.suspend",
            "user.lifecycle.delete",
            "user.account.lock",
            "user.account.unlock",
            "user.account.reset_password",
            "user.account.update_password",
        ],
        "reason": "User lifecycle or account recovery activity detected.",
    },
    {
        "ruleId": "APP_CONFIGURATION_CHANGE",
        "configKey": "appConfigurationChanges",
        "category": "Application",
        "severity": "medium",
        "patterns": ["application.lifecycle", "app.oauth2", "app.generic", "application.user_membership"],
        "reason": "Application configuration or assignment activity detected.",
    },
    {
        "ruleId": "RATE_LIMIT_OR_THROTTLE_EVENT",
        "configKey": "rateLimitEvents",
        "category": "Operations",
        "severity": "high",
        "patterns": ["rate_limit", "rate.limit", "system.org.warning", "throttle"],
        "reason": "Rate limit, throttling, or org warning activity detected.",
    },
]


def is_enabled(config: dict[str, Any], key: str) -> bool:
    return bool((config.get("detections", {}) or {}).get(key, {}).get("enabled", True))


def configured_severity(config: dict[str, Any], key: str, default: str) -> str:
    return (config.get("detections", {}) or {}).get(key, {}).get("severity", default)


def detect(events: list[dict[str, Any]], config: dict[str, Any]) -> list[dict[str, Any]]:
    detections: list[dict[str, Any]] = []
    detections.extend(_detect_event_rules(events, config))
    detections.extend(_detect_failed_sign_in_spikes(events, config))
    detections.extend(_detect_mfa_failure_spikes(events, config))
    detections.extend(_detect_suspicious_countries(events, config))
    detections.extend(_detect_multiple_countries_per_actor(events, config))
    detections.extend(_detect_suspicious_ips(events, config))
    return _finalize(detections, config)


def _detect_event_rules(events: list[dict[str, Any]], config: dict[str, Any]) -> list[dict[str, Any]]:
    detections = []
    for event in events:
        event_type = (event.get("eventType") or "").lower()
        message = (event.get("displayMessage") or "").lower()
        combined = f"{event_type} {message}"
        for rule in EVENT_RULES:
            if not is_enabled(config, rule["configKey"]):
                continue
            if any(pattern in combined for pattern in rule["patterns"]):
                outcome_result = event.get("outcomeResult") or ""
                if outcome_result in rule.get("excludeOutcomes", []):
                    continue
                detections.append(
                    _detection(
                        rule_id=rule["ruleId"],
                        severity=configured_severity(config, rule["configKey"], rule["severity"]),
                        category=rule["category"],
                        event=event,
                        reason=rule["reason"],
                        evidence=f"eventType={event.get('eventType')} outcome={event.get('outcomeResult')}",
                    )
                )
                break
    return detections


def _detect_failed_sign_in_spikes(events: list[dict[str, Any]], config: dict[str, Any]) -> list[dict[str, Any]]:
    key = "failedSignInSpike"
    rule = config.get("detections", {}).get(key, {})
    if not rule.get("enabled", True):
        return []
    threshold = int(rule.get("threshold", 5))
    actor_counts: Counter[str] = Counter()
    ip_counts: Counter[str] = Counter()
    examples: dict[str, dict[str, Any]] = {}
    ip_examples: dict[str, dict[str, Any]] = {}
    for event in events:
        if _looks_like_signin_failure(event):
            actor = event.get("actorAlternateId") or "unknown"
            ip = event.get("clientIpAddress") or "unknown"
            actor_counts[actor] += 1
            ip_counts[ip] += 1
            examples.setdefault(actor, event)
            ip_examples.setdefault(ip, event)
    detections = []
    for actor, count in actor_counts.items():
        if count >= threshold:
            detections.append(
                _detection(
                    "FAILED_SIGN_IN_SPIKE_BY_ACTOR",
                    rule.get("severity", "medium"),
                    "Authentication",
                    examples[actor],
                    f"Actor had {count} failed sign-in related events.",
                    f"actor={actor} failedEvents={count} threshold={threshold}",
                    count=count,
                )
            )
    for ip, count in ip_counts.items():
        if count >= threshold:
            detections.append(
                _detection(
                    "FAILED_SIGN_IN_SPIKE_BY_IP",
                    rule.get("severity", "medium"),
                    "Authentication",
                    ip_examples[ip],
                    f"IP address had {count} failed sign-in related events.",
                    f"ipAddress={ip} failedEvents={count} threshold={threshold}",
                    count=count,
                )
            )
    return detections


def _detect_mfa_failure_spikes(events: list[dict[str, Any]], config: dict[str, Any]) -> list[dict[str, Any]]:
    key = "mfaFailureSpike"
    rule = config.get("detections", {}).get(key, {})
    if not rule.get("enabled", True):
        return []
    threshold = int(rule.get("threshold", 3))
    actor_counts: Counter[str] = Counter()
    examples: dict[str, dict[str, Any]] = {}
    for event in events:
        if _looks_like_mfa_failure(event):
            actor = event.get("actorAlternateId") or "unknown"
            actor_counts[actor] += 1
            examples.setdefault(actor, event)
    return [
        _detection(
            "MFA_FAILURE_SPIKE_BY_ACTOR",
            rule.get("severity", "high"),
            "MFA",
            examples[actor],
            f"Actor had {count} MFA failure related events.",
            f"actor={actor} mfaFailures={count} threshold={threshold}",
            count=count,
        )
        for actor, count in actor_counts.items()
        if count >= threshold
    ]


def _detect_suspicious_countries(events: list[dict[str, Any]], config: dict[str, Any]) -> list[dict[str, Any]]:
    key = "suspiciousCountry"
    rule = config.get("detections", {}).get(key, {})
    if not rule.get("enabled", True):
        return []
    allowed = set(rule.get("allowedCountries") or [])
    if not allowed:
        return []
    detections = []
    for event in events:
        country = event.get("country") or ""
        if country and country not in allowed:
            detections.append(
                _detection(
                    "SUSPICIOUS_COUNTRY",
                    rule.get("severity", "medium"),
                    "Geo",
                    event,
                    f"Event originated from country outside the configured allow list: {country}.",
                    f"country={country} allowedCountries={';'.join(sorted(allowed))}",
                )
            )
    return detections


def _detect_multiple_countries_per_actor(events: list[dict[str, Any]], config: dict[str, Any]) -> list[dict[str, Any]]:
    key = "multipleCountriesPerActor"
    rule = config.get("detections", {}).get(key, {})
    if not rule.get("enabled", True):
        return []
    threshold = int(rule.get("threshold", 2))
    countries_by_actor: dict[str, set[str]] = defaultdict(set)
    examples: dict[str, dict[str, Any]] = {}
    for event in events:
        actor = event.get("actorAlternateId") or "unknown"
        country = event.get("country") or ""
        if country:
            countries_by_actor[actor].add(country)
            examples.setdefault(actor, event)
    return [
        _detection(
            "MULTIPLE_COUNTRIES_PER_ACTOR",
            rule.get("severity", "medium"),
            "Geo",
            examples[actor],
            f"Actor appeared from {len(countries)} countries in the analyzed data set.",
            f"actor={actor} countries={';'.join(sorted(countries))} threshold={threshold}",
            count=len(countries),
        )
        for actor, countries in countries_by_actor.items()
        if len(countries) >= threshold
    ]


def _detect_suspicious_ips(events: list[dict[str, Any]], config: dict[str, Any]) -> list[dict[str, Any]]:
    key = "suspiciousIpAddresses"
    rule = config.get("detections", {}).get(key, {})
    if not rule.get("enabled", True):
        return []
    suspicious_ips = set(rule.get("ipAddresses") or [])
    if not suspicious_ips:
        return []
    return [
        _detection(
            "SUSPICIOUS_IP_ADDRESS",
            rule.get("severity", "high"),
            "Network",
            event,
            "Event originated from a configured suspicious IP address.",
            f"ipAddress={event.get('clientIpAddress')}",
        )
        for event in events
        if event.get("clientIpAddress") in suspicious_ips
    ]


def _looks_like_signin_failure(event: dict[str, Any]) -> bool:
    event_type = (event.get("eventType") or "").lower()
    message = (event.get("displayMessage") or "").lower()
    outcome = (event.get("outcomeResult") or "").upper()
    reason = (event.get("outcomeReason") or "").lower()
    return (
        outcome in {"FAILURE", "DENY", "CHALLENGE"}
        and any(term in f"{event_type} {message} {reason}" for term in ["authentication", "signin", "sign-in", "session", "login"])
    )


def _looks_like_mfa_failure(event: dict[str, Any]) -> bool:
    event_type = (event.get("eventType") or "").lower()
    message = (event.get("displayMessage") or "").lower()
    reason = (event.get("outcomeReason") or "").lower()
    outcome = (event.get("outcomeResult") or "").upper()
    text = f"{event_type} {message} {reason}"
    return outcome in {"FAILURE", "DENY", "CHALLENGE"} and any(term in text for term in ["factor", "authenticator", "mfa", "verify"])


def _detection(
    rule_id: str,
    severity: str,
    category: str,
    event: dict[str, Any],
    reason: str,
    evidence: str,
    count: int | None = None,
) -> dict[str, Any]:
    return {
        "detectionId": "",
        "ruleId": rule_id,
        "severity": severity,
        "category": category,
        "published": event.get("published") or "",
        "actor": event.get("actorAlternateId") or "unknown",
        "actorDisplayName": event.get("actorDisplayName") or "",
        "clientIpAddress": event.get("clientIpAddress") or "",
        "country": event.get("country") or "",
        "eventType": event.get("eventType") or "",
        "outcomeResult": event.get("outcomeResult") or "",
        "outcomeReason": event.get("outcomeReason") or "",
        "targetNames": event.get("targetNames") or "",
        "eventUuid": event.get("uuid") or "",
        "reason": reason,
        "evidence": evidence,
        "count": count or "",
        "rawEvent": event.get("rawEvent") or {},
    }


def _finalize(detections: list[dict[str, Any]], config: dict[str, Any]) -> list[dict[str, Any]]:
    include_low = bool(config.get("includeLowSeverity", True))
    include_info = bool(config.get("includeInformationalFindings", False))
    filtered = []
    seen = set()
    for detection in detections:
        severity = detection.get("severity", "info")
        if severity == "info" and not include_info:
            continue
        if severity == "low" and not include_low:
            continue
        dedupe_key = (
            detection.get("ruleId"),
            detection.get("eventUuid"),
            detection.get("actor"),
            detection.get("clientIpAddress"),
            detection.get("evidence"),
        )
        if dedupe_key in seen:
            continue
        seen.add(dedupe_key)
        filtered.append(detection)
    filtered.sort(key=lambda item: (-SEVERITY_ORDER.get(item.get("severity", "info"), 0), item.get("published", "")))
    for index, detection in enumerate(filtered, start=1):
        detection["detectionId"] = f"DET-{index:05d}"
    return filtered
