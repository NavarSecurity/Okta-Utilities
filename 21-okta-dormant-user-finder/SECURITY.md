# Security Notes

This utility is designed for read-only dormant account discovery.

## Secrets

Do not commit or share:

- `.env`
- Okta API tokens
- exported raw user data
- output files containing user profile data

## Data Handling

User exports can contain personal data. Store output files only in approved internal locations and delete temporary files when review is complete.

## Permissions

Use the least-privilege Okta admin/API token that can read users and, if enabled, read app links and group membership.

## Review Before Action

Dormant-account findings are candidates for review. Do not suspend, deactivate, or delete accounts solely based on this report without approval from the appropriate owner or source-of-truth process.
