# Security Notes

This utility can create applications in a target Okta org when run with `--apply`.

Use a non-production org for initial testing. Use least-privilege API tokens where possible. Do not commit `.env` files, API tokens, raw backups, or output reports containing sensitive configuration.

The utility intentionally removes source-org generated IDs, timestamps, links, secrets, redacted values, and generated OAuth credentials before creating apps in the target org.

Client secrets and provisioning credentials should be generated or entered directly in the target org through an approved process.
