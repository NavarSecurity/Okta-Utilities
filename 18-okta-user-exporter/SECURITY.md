# Security Notes

`okta-user-exporter` is read-only, but its outputs can contain sensitive identity data.

## Do not commit

Do not commit or share:

```text
.env
API tokens
raw user exports
unreviewed output folders
```

## Token handling

Store the Okta API token in `.env` only. The utility does not write the token to output files.

## Output handling

Treat these files as sensitive:

```text
users.csv
users.json
user_groups.csv
user_app_links.csv
raw_*.json
```

They may include names, emails, group membership, app context, and other profile attributes.

## Raw output

`saveRawResponses` is disabled by default. Enable it only when you need full Okta API response evidence and have an approved secure storage location.
