# Security Notes

This utility handles Okta configuration data and requires an Okta API token for live backup runs.

## Required handling

- Store the Okta API token only in environment variables or a local `.env` file.
- Do not commit `.env` files or generated customer backup output without approval.
- Prefer the least-privileged admin account/token that can read the required configuration.
- Rotate the token after client delivery work if the token was created specifically for the engagement.
- Review generated backup output before sharing or committing it.

## Redaction

Default output redacts common secret-bearing fields before writing JSON files. Redaction reduces accidental exposure risk, but it does not replace internal review. Treat backup output as sensitive client configuration.

## Scope

This utility is read-only. It does not restore, import, modify, assign, deactivate, or delete Okta objects.
