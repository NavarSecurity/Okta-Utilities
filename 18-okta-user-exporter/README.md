# WARNING

These utilities have limited testing and are provided as-is with no warranty. Use at your own risk.

# 18-okta-user-exporter

`okta-user-exporter` is a read-only utility for exporting Okta users to CSV and JSON with optional group and app-link context.

It is intended for user migration discovery, access review preparation, lifecycle cleanup analysis, and evidence collection before bulk user import or reconciliation work.

## What this utility does

```text
Exports Okta users
Exports selected user profile fields
Exports user status and lifecycle timestamps
Optionally exports user group memberships
Optionally exports user app-link context
Writes CSV, JSON, Markdown, and execution evidence
Handles pagination, retries, and partial failures
Rejects Okta Admin Console URLs
```

## What this utility does not do

```text
Does not create users
Does not update users
Does not deactivate users
Does not assign users to groups or apps
Does not change Okta state
```

This utility is read-only. The `--apply` flag is accepted only as an alias for `--export` to stay consistent with the rest of the toolkit.

## Folder structure

```text
18-okta-user-exporter/
  README.md
  SECURITY.md
  .gitignore
  .env.example
  config.example.json
  pyproject.toml
  requirements.txt
  requirements-dev.txt
  src/okta_user_exporter/
  input/
  output/
  samples/
  tests/
```

## Setup

Create and activate a Python virtual environment.

macOS/Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Install the utility:

```bash
python -m pip install --upgrade pip
python -m pip install -e .
```

Confirm the command is available:

```bash
okta-user-exporter --help
```

## Configure Okta access

Copy the example environment file:

```bash
cp .env.example .env
```

Edit `.env`:

```env
OKTA_ORG_URL=https://your-org.okta.com
OKTA_API_TOKEN=replace-with-okta-api-token
```

Use the normal Okta org URL.

Correct:

```text
https://integrator-1703705.okta.com
```

Incorrect:

```text
https://integrator-1703705-admin.okta.com
https://integrator-1703705.okta.com/admin
https://integrator-1703705.okta.com/api/v1
https://integrator-1703705.okta.com/oauth2/default
```

The token should have enough read access to list users and, if enabled, read user groups and app links.

Do not commit or share `.env`.

## Create the input config

Copy the sample config:

```bash
cp samples/user-export.sample.json input/user-export.config.json
```

Edit:

```text
input/user-export.config.json
```

Example:

```json
{
  "orgUrl": "https://your-org.okta.com",
  "settings": {
    "requestTimeoutSeconds": 30,
    "maxRetries": 3,
    "pageLimit": 200,
    "maxUsers": 100,
    "continueOnError": true,
    "saveRawResponses": false,
    "redactSensitiveProfileFields": true
  },
  "filters": {
    "statuses": ["ACTIVE", "PROVISIONED"],
    "query": "",
    "search": "",
    "filter": "",
    "userIds": [],
    "loginContains": "",
    "profileFields": ["login", "email", "firstName", "lastName", "department", "title"],
    "includeProfileAll": false
  },
  "include": {
    "groups": true,
    "appLinks": true
  },
  "output": {
    "usersCsv": "users.csv",
    "usersJson": "users.json",
    "userGroupsCsv": "user_groups.csv",
    "userAppLinksCsv": "user_app_links.csv",
    "summaryCsv": "user_export_summary.csv",
    "resultJson": "user_export_result.json",
    "reportMarkdown": "user_export_report.md"
  }
}
```

## Config explanation

### `settings.maxUsers`

Limits how many users are exported. This is useful for first tests.

```json
"maxUsers": 100
```

Use `null` to export all matching users.

### `filters.statuses`

Only exports users with the listed statuses.

```json
"statuses": ["ACTIVE", "PROVISIONED"]
```

Use an empty list to include all statuses returned by Okta.

### `filters.query`

Uses Okta's `q` parameter for simple user lookup.

```json
"query": "jacob"
```

### `filters.search`

Passes an Okta user search expression to the Users API.

Example:

```json
"search": "profile.department eq \"Finance\""
```

### `filters.filter`

Passes an Okta user filter expression to the Users API.

Example:

```json
"filter": "status eq \"ACTIVE\""
```

### `filters.userIds`

Exports only specific users by ID.

```json
"userIds": ["00uabc123", "00udef456"]
```

### `filters.profileFields`

Controls which profile fields are included in the user CSV.

```json
"profileFields": ["login", "email", "firstName", "lastName", "department", "title"]
```

### `filters.includeProfileAll`

Exports all profile fields from the user profile object.

```json
"includeProfileAll": true
```

Use this carefully. User profile data can contain sensitive or client-specific attributes.

### `include.groups`

When true, the utility calls:

```text
GET /api/v1/users/{userId}/groups
```

and writes:

```text
user_groups.csv
```

### `include.appLinks`

When true, the utility calls:

```text
GET /api/v1/users/{userId}/appLinks
```

and writes:

```text
user_app_links.csv
```

App links provide useful app context, but they are not always a complete substitute for a full application assignment export. Use Utility 13 when you need app-centric assignment evidence.

## Run a dry-run

```bash
okta-user-exporter --config input/user-export.config.json --dry-run
```

Dry-run does not call Okta. It writes a plan to:

```text
output/okta-user-exporter-YYYYMMDDTHHMMSSZ/user_export_plan.json
output/okta-user-exporter-YYYYMMDDTHHMMSSZ/user_export_report.md
```

Review the target org, filters, includes, and planned output files.

## Run the export

```bash
okta-user-exporter --config input/user-export.config.json --export
```

`--apply` is also accepted, but the utility remains read-only:

```bash
okta-user-exporter --config input/user-export.config.json --apply
```

## Output files

Each export creates a timestamped folder:

```text
output/okta-user-exporter-YYYYMMDDTHHMMSSZ/
```

Main outputs:

```text
users.csv
users.json
user_groups.csv
user_app_links.csv
user_export_summary.csv
user_export_result.json
user_export_report.md
```

Optional raw outputs, only if `saveRawResponses` is true:

```text
raw_users.json
raw_groups_by_user.json
raw_app_links_by_user.json
```

Treat all outputs as sensitive identity data.

## Recommended first test

Start with a small export:

```json
"settings": {
  "maxUsers": 10
},
"include": {
  "groups": true,
  "appLinks": false
}
```

Then run:

```bash
okta-user-exporter --config input/user-export.config.json --export
```

After confirming the CSV format, increase `maxUsers` or set it to `null`.

## Typical workflow

```text
1. Run dry-run
2. Confirm org URL and filters
3. Export a small sample
4. Review CSV/JSON outputs
5. Export full user set
6. Use results for migration, reconciliation, access review, or cleanup analysis
```

## How this fits with other utilities

```text
Utility 18 = Export users from Okta
Utility 19 = Import users into Okta
Utility 20 = Reconcile Okta users against another source
Utility 21 = Find dormant or stale users
Utility 22 = Deactivate approved users
Utility 24 = Load group memberships
```

## Troubleshooting

### `Configuration error: Use the normal Okta org URL`

The configured URL is probably the Admin Console URL.

Change:

```text
https://your-org-admin.okta.com
```

to:

```text
https://your-org.okta.com
```

### `OKTA_API_TOKEN is required for --export mode`

Create or update `.env`:

```env
OKTA_API_TOKEN=replace-with-okta-api-token
```

### `403 Forbidden`

The API token likely does not have enough admin permissions to read users, groups, or app links.

Use an admin/service account with the minimum read permissions needed for the export.

### Exports are too large

Set a temporary maximum:

```json
"maxUsers": 100
```

or use filters such as `statuses`, `search`, `filter`, or `userIds`.

## Security notes

Do not commit or share:

```text
.env
API tokens
Raw user exports
Unreviewed output folders
```

Even CSV exports can contain sensitive identity data. Store outputs only in approved client/project locations.
