# Security Notes

This utility is read-only, but it still uses an Okta API token and exports security configuration.

Do not commit or share:

```text
.env
Okta API tokens
Raw unreviewed export output
Client secrets
Private keys
Authorization headers
```

The `.gitignore` is configured to exclude common local and sensitive files.

Treat authorization server exports as sensitive IAM configuration data. Scopes, claims, audiences, policy names, and rule names can reveal API design and access-control details.
