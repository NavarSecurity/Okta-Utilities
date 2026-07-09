# Security Notes

This utility is read-only, but it can still produce sensitive user and authenticator reporting data.

## Secrets

Do not commit `.env` files, API tokens, local config files with secrets, or output reports from real client environments.

## Output handling

MFA enrollment reports can contain sensitive user security posture information. Store generated reports in an approved internal location only.

## Redaction

Keep `redactSensitiveProfileValues` enabled unless there is a controlled reason to include raw factor profile data.

## API token scope

Use a least-privilege Okta API token that can read users and factor enrollment information.
