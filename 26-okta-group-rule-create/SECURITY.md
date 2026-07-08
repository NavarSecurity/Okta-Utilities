# Security Notes

This utility can create Okta group rules that automatically assign users to groups. Group rules can indirectly grant application access, policy access, or downstream authorization depending on how groups are used in the org.

Use dry-run first, review all expressions and target groups, and test in a non-production Okta org before using with production data.

Do not commit or share:

```text
.env
Okta API tokens
Output files containing client or tenant data
Local input configs with production group names or IDs
```

Use a least-privilege API token where possible.
