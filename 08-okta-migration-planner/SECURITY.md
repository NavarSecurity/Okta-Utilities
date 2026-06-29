# Security Notes

`okta-migration-planner` is a read-only local analysis utility. It does not call Okta APIs and does not require Okta API tokens. It reads exported backup JSON from a source and target folder, compares objects, and writes local planning artifacts.

## Handling backup data

Okta backup exports may contain sensitive configuration metadata. Treat all backup files and generated reports as internal/confidential unless they have been reviewed and approved for sharing.

Do not commit the following without review:

- Raw backup folders
- Generated migration plans
- Object mappings
- Conflict reports
- Files containing tenant URLs, app labels, policy names, group names, IdP metadata, authorization server information, hooks, domains, or other client-specific details

## Safe behavior

This utility does not create, update, delete, assign, activate, or deactivate Okta objects. It is intended to support migration planning only. Any follow-on restore, import, or creation work should be performed through separate tools with explicit dry-run and apply controls.
