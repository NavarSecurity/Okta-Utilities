# Security Notes

This utility can create authorization server objects that affect OAuth/OIDC token issuance.

## Token handling

- Store Okta API tokens in `.env` or environment variables only.
- Do not commit `.env` files.
- Rotate tokens if they are shared, uploaded, or exposed.
- Prefer short-lived testing tokens in sandbox environments.

## Operational safety

- Run `--dry-run` first.
- Review generated payloads before `--apply`.
- Test authorization server policies and rules before production rollout.
- Keep output artifacts as change evidence.
- Treat rollback plans as manual review material, not automatic delete scripts.
