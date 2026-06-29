from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SimpleResource:
    name: str
    path: str
    paginated: bool = True


SIMPLE_RESOURCES: dict[str, SimpleResource] = {
    "org": SimpleResource("org", "/api/v1/org", paginated=False),
    "applications": SimpleResource("applications", "/api/v1/apps"),
    "groups": SimpleResource("groups", "/api/v1/groups"),
    "group_rules": SimpleResource("group_rules", "/api/v1/groups/rules"),
    "identity_providers": SimpleResource("identity_providers", "/api/v1/idps"),
    "event_hooks": SimpleResource("event_hooks", "/api/v1/eventHooks"),
    "inline_hooks": SimpleResource("inline_hooks", "/api/v1/inlineHooks"),
    "network_zones": SimpleResource("network_zones", "/api/v1/zones"),
    "trusted_origins": SimpleResource("trusted_origins", "/api/v1/trustedOrigins"),
    "brands": SimpleResource("brands", "/api/v1/brands"),
    "domains": SimpleResource("domains", "/api/v1/domains"),
    "authenticators": SimpleResource("authenticators", "/api/v1/authenticators"),
    "features": SimpleResource("features", "/api/v1/features"),
    "user_schema": SimpleResource("user_schema", "/api/v1/meta/schemas/user/default", paginated=False),
}

RESOURCE_DESCRIPTIONS: dict[str, str] = {
    "org": "Org-level metadata and settings exposed by /api/v1/org.",
    "applications": "Application configuration objects from /api/v1/apps.",
    "groups": "Okta group objects from /api/v1/groups.",
    "group_rules": "Group rules from /api/v1/groups/rules.",
    "policies": "Policy objects and child policy rules by configured policy type.",
    "identity_providers": "External identity provider configuration from /api/v1/idps.",
    "authorization_servers": "Custom authorization servers, scopes, claims, access policies, and policy rules.",
    "event_hooks": "Event hook configuration from /api/v1/eventHooks.",
    "inline_hooks": "Inline hook configuration from /api/v1/inlineHooks.",
    "network_zones": "Network zone configuration from /api/v1/zones.",
    "trusted_origins": "Trusted origins from /api/v1/trustedOrigins.",
    "brands": "Brand metadata from /api/v1/brands.",
    "domains": "Custom domain metadata from /api/v1/domains.",
    "authenticators": "Authenticator metadata from /api/v1/authenticators.",
    "features": "Okta feature flags and feature metadata from /api/v1/features.",
    "user_schema": "Default Okta user profile schema from /api/v1/meta/schemas/user/default.",
}
