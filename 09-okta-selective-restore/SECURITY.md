# Security Notes for okta-selective-restore

`okta-selective-restore` is a mutating Okta utility. Treat it as more sensitive than a backup/export tool.

## Core safety rules

- Always run `--dry-run` first.
- Use `--apply` only after reviewing `restore_plan.json` and `execution_report.md`.
- Never run this against production without change approval.
- Use a dedicated target-org service account where possible.
- Do not use personal admin tokens for client or production work.
- Store `.env` only on trusted machines.
- Do not commit `.env`, API tokens, raw client secrets, or unreviewed restore artifacts.

## Token handling

The utility expects the API token in one of these variables:

```text
OKTA_TARGET_API_TOKEN
OKTA_API_TOKEN
```

Do not include the literal `SSWS` prefix. The utility adds the correct authorization header internally.

## Target org validation

Use the base Okta org URL only:

```text
https://dev-12345678.okta.com
```

Do not include these suffixes:

```text
/admin
/oauth2
/api/v1
```

## Secret handling

The utility attempts to remove sensitive fields from restored payloads, including:

- API tokens
- access tokens
- refresh tokens
- client secrets
- passwords
- private keys
- shared secrets
- authorization headers

Even with sanitization, restore artifacts may expose sensitive configuration metadata. Treat all output as internal confidential material.

## Unsupported high-risk resources

This initial version intentionally skips several resource types:

- Policies
- Group rules
- Identity providers
- Event hooks
- Inline hooks
- Brands
- Domains
- Authenticators
- Org-level settings

These resources often require special ordering, manual approvals, secrets, activation steps, custom domain validation, or high-risk tenant-wide behavior.

## Rollback handling

`rollback_plan.json` is generated for created objects, but rollback is not automatic.

Before using rollback actions:

1. Confirm the object was created by this utility.
2. Confirm no user or app dependency was added after creation.
3. Review each delete action manually.
4. Execute rollback through an approved operational process.

## Recommended production control

For production use, require:

- Backup completed before restore
- Dry-run evidence reviewed
- Change ticket approved
- Target org and resource list confirmed
- Dedicated API token created and scoped appropriately
- Rollback plan reviewed
- Post-restore smoke test completed
- API token rotated or revoked after engagement if temporary
