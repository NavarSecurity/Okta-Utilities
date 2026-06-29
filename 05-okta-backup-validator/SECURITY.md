# Security Notes for okta-backup-validator

`okta-backup-validator` is a local validation utility. It does not call Okta APIs and does not require an Okta API token.

## Sensitive data handling

Even when a backup was produced with redaction enabled, treat every Okta backup as sensitive internal configuration.

Do not commit backup output to public repositories. Do not paste full backup files into public tools. Do not send raw backup folders to people who do not need access.

## What the validator scans for

The validator performs an exact/canonical key-name scan for potentially unredacted scalar fields such as:

```text
apiToken
access_token
refresh_token
client_secret
password
privateKey
authorization
sharedSecret
bearer
```

This scan is useful but not perfect. It can catch common unredacted fields, but it is not a full data loss prevention engine. Normal Okta structural keys such as `authorizationServers`, `detailsByAuthorizationServerId`, `passwordChange`, and `selfServicePasswordReset` are not treated as secrets by themselves.

## Sensitive finding output

When `SENSITIVE_VALUES_FOUND` is raised, `validation_result.json` and `validation_report.md` include the exact detected value that should be redacted. This is intentional so operators can locate and remove the value quickly, but it means validation reports can contain secrets. Do not commit or broadly share validation reports that contain sensitive findings.

## Recommended handling

Use this workflow before sharing or using a backup:

```text
1. Run okta-config-backup with redaction enabled.
2. Run okta-backup-validator.
3. Review validation_report.md.
4. Review any sensitive-value findings manually.
5. Share only approved, required files.
```

## Prohibited storage

Do not store these in the repository:

```text
.env files
Okta API tokens
Unredacted backup exports
Production secrets
Customer-specific configuration outside approved storage
```

## Restore and migration safety

A backup that validates cleanly is still not automatically safe to restore into another org. Validate the backup first, then use dry-run mode in any restore or migration utility before applying changes.
