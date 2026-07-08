# Security Notes

This utility is read-only. It analyzes Okta groups and writes local report files.

Do not commit or share:

```text
.env
API tokens
Raw client data exports
Output reports that contain sensitive group names or membership evidence
```

Use a least-privilege read-only Okta API token where possible.

Rotate any token that is accidentally copied into a ZIP, Git repository, ticket, chat, or shared folder.
