# Security Notes

This utility is read-only and is intended to use the least-privileged Okta API token that can read applications and app assignments.

Do not commit `.env`, API tokens, exported assignment evidence, user lists, group lists, or raw assignment output.

Recommended handling:

- Use a non-production Okta org for initial testing.
- Use a dedicated service account where possible.
- Store API tokens in `.env` or a secret manager, not in JSON config files.
- Rotate any token that is accidentally shared, uploaded, or committed.
- Review output files before sharing because app assignments may reveal user, group, and application access information.
