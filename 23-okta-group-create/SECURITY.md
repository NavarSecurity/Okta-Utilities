# Security Notes

This utility can create Okta groups. Treat all apply-mode runs as changes to the target Okta org.

## Secrets

Do not commit or share:

```text
.env
Okta API tokens
Unreviewed output that may contain org-specific data
```

## Recommended use

```text
Run dry-run before apply
Use a non-production Okta org for first testing
Keep maxGroupsPerRun low until the input file is reviewed
Use requireApproved for production-facing changes
Review rollback_plan.json after apply
```

## Token permissions

Use the least-privileged token that can read and create groups for the intended environment.

## URL safety

The utility rejects Admin Console URLs such as:

```text
https://your-org-admin.okta.com
```

Use the base Okta org URL:

```text
https://your-org.okta.com
```
