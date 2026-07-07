# Security Notes

This utility can modify Okta group membership in apply mode.

## Sensitive files

Do not commit or share:

```text
.env
input files containing real users or groups
output folders from real runs
rollback plans from real runs
```

## API token handling

Use `.env` for the Okta API token. Do not place tokens directly in config files, CSV files, README files, or tickets.

## Operational safety

Run dry-run first. Review planned changes, skipped records, and failed records before applying. Be especially careful with remove and replace actions because they can remove user access.
