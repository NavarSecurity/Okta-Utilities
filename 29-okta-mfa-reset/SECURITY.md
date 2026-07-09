# Security Notes

This utility can reset MFA/factor/authenticator enrollments for Okta users. Treat it as a privileged administrative tool.

## Required protections

- Use a dedicated Okta API token with the minimum permissions required.
- Run dry-run before apply.
- Require row-level approval and reason values.
- Keep `.env` out of Git and shared ZIP files.
- Review output evidence after every run.
- Do not use this utility against production without change approval.

## Sensitive data handling

The utility redacts API tokens and avoids writing factor secrets or full sensitive profile values to output.

## Operational risk

MFA reset actions can lock users out until they re-enroll. Use small batches first and coordinate help desk support.
