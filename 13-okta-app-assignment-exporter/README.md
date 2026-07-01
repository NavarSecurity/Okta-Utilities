# WARNING

These utilities have limited testing and are provided as-is with no warranty. Use at your own risk.

# 13-okta-app-assignment-exporter

`okta-app-assignment-exporter` is a read-only CLI utility for exporting Okta application assignments. It pulls selected Okta applications, their assigned users, and their assigned groups, then writes review-ready JSON, CSV, Markdown, and execution evidence files.

This is utility 13 in the Okta utility pack.

## Purpose

Use this utility when you need to understand who or what is assigned to Okta applications before onboarding, migration, cleanup, access review, Terraform conversion, or selective restore work.

Typical uses:

- Export user assignments for selected apps.
- Export group assignments for selected apps.
- Build assignment evidence for application onboarding or migration.
- Compare assignment output before and after app changes.
- Identify apps with direct user assignments instead of group-based assignments.
- Provide CSV files that can be reviewed by application owners.

## Safety model

This utility is read-only.

It does not create apps, update apps, remove apps, assign users, assign groups, or delete anything from Okta.

The utility still supports a dry-run mode by default. Dry-run validates configuration and writes the export plan only. To call the Okta API and export assignments, use `--export`.

## What it exports

The utility can export:

- Selected Okta app metadata
- Assigned users for each selected app
- Assigned groups for each selected app
- Assignment summary by app
- Assignment errors by app and endpoint
- Optional raw assignment responses

Default output is intentionally limited to common assignment fields so exported files are easier to review and less likely to expose unnecessary profile data.

## Folder structure

```text
13-okta-app-assignment-exporter/
  README.md
  SECURITY.md
  .gitignore
  .env.example
  config.example.json
  pyproject.toml
  requirements.txt
  requirements-dev.txt
  src/okta_app_assignment_exporter/
  input/
  output/
  samples/
  tests/
```

## Setup

From the utility folder:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .
```

For tests:

```bash
python -m pip install -r requirements-dev.txt
```

## Configure environment

Copy `.env.example` to `.env`:

```bash
cp .env.example .env
```

Edit `.env`:

```text
OKTA_ORG_URL=https://your-org.okta.com
OKTA_API_TOKEN=replace-with-read-only-okta-api-token
```

Use the normal Okta org base URL. Do not use the admin URL.

Correct:

```text
https://integrator-1703705.okta.com
```

Incorrect:

```text
https://integrator-1703705-admin.okta.com
https://integrator-1703705.okta.com/admin
https://integrator-1703705.okta.com/api/v1
```

## Configure app selection

Copy the sample config into `input/`:

```bash
cp samples/app-assignment-export.config.json input/app-assignment-export.config.json
```

Edit `input/app-assignment-export.config.json`.

### Export all active apps

```json
{
  "appSelection": {
    "mode": "all",
    "statuses": ["ACTIVE"],
    "signOnModes": []
  }
}
```

### Export by app label

```json
{
  "appSelection": {
    "mode": "labels",
    "appLabels": [
      "Example OIDC App",
      "Example SAML App"
    ],
    "statuses": ["ACTIVE"]
  }
}
```

### Export by app ID

```json
{
  "appSelection": {
    "mode": "ids",
    "appIds": [
      "0oa123example"
    ],
    "statuses": []
  }
}
```

### Export only specific sign-on modes

```json
{
  "appSelection": {
    "mode": "all",
    "statuses": ["ACTIVE"],
    "signOnModes": [
      "OPENID_CONNECT",
      "SAML_2_0"
    ]
  }
}
```

## Dry-run

Dry-run is the default behavior. It validates configuration and writes the export plan. It does not call the Okta API.

```bash
okta-app-assignment-exporter --config input/app-assignment-export.config.json --dry-run
```

You can also omit `--dry-run`:

```bash
okta-app-assignment-exporter --config input/app-assignment-export.config.json
```

## Export assignments

To call Okta and export assignments:

```bash
okta-app-assignment-exporter --config input/app-assignment-export.config.json --export
```

`--apply` is also accepted as an alias for `--export` for consistency with other utilities, but this utility is read-only.

```bash
okta-app-assignment-exporter --config input/app-assignment-export.config.json --apply
```

## Output files

Each run creates a timestamped folder under `output/`.

Example:

```text
output/okta-app-assignment-exporter-20260630T200000Z/
```

Files created:

```text
app_assignment_export_plan.json
app_assignment_export_result.json
app_assignments.json
assignment_summary.csv
app_user_assignments.csv
app_group_assignments.csv
errors.csv
assignment_summary.md
execution_report.md
```

Optional when `includeRawAssignments` is true:

```text
raw_assignments.json
```

## Output file purpose

| File | Purpose |
|---|---|
| `app_assignment_export_plan.json` | Shows the run configuration, selection rules, and export options. |
| `app_assignment_export_result.json` | Full run result, counts, warnings, errors, and request summary. |
| `app_assignments.json` | Combined assignment output grouped by application. |
| `assignment_summary.csv` | One row per app with assignment counts. |
| `app_user_assignments.csv` | One row per app user assignment. |
| `app_group_assignments.csv` | One row per app group assignment. |
| `errors.csv` | API or export errors in CSV form. |
| `assignment_summary.md` | Human-readable assignment summary. |
| `execution_report.md` | Execution evidence for review. |

## Config reference

```json
{
  "targetOrgUrl": "https://your-org.okta.com",
  "outputDir": "output",
  "appSelection": {
    "mode": "all",
    "appIds": [],
    "appLabels": [],
    "statuses": ["ACTIVE"],
    "signOnModes": [],
    "excludeAppIds": [],
    "excludeAppLabels": []
  },
  "exportOptions": {
    "includeUsers": true,
    "includeGroups": true,
    "includeUserProfile": false,
    "includeGroupProfile": false,
    "includeRawAssignments": false,
    "maxApps": null,
    "failFast": false
  },
  "http": {
    "pageLimit": 200,
    "timeoutSeconds": 30,
    "maxRetries": 4,
    "retryBaseSeconds": 1.0
  }
}
```

## Selection modes

| Mode | Behavior |
|---|---|
| `all` | Lists apps and exports assignments for apps matching filters. |
| `labels` | Lists apps and exports assignments for exact matching app labels. |
| `ids` | Fetches the specific app IDs and exports assignments for those apps. |

## Export options

| Option | Default | Description |
|---|---:|---|
| `includeUsers` | `true` | Export app user assignments. |
| `includeGroups` | `true` | Export app group assignments. |
| `includeUserProfile` | `false` | Include scalar user profile fields in the user assignment CSV. |
| `includeGroupProfile` | `false` | Include scalar group profile fields in the group assignment CSV. |
| `includeRawAssignments` | `false` | Write raw API assignment responses into `raw_assignments.json`. |
| `maxApps` | `null` | Limit number of selected apps exported. Useful for testing. |
| `failFast` | `false` | Stop on first API/export error. |

## Recommended first test

Start with one app label and a low-risk sandbox org.

```json
{
  "appSelection": {
    "mode": "labels",
    "appLabels": ["OIDC Test App"],
    "statuses": ["ACTIVE"]
  },
  "exportOptions": {
    "includeUsers": true,
    "includeGroups": true,
    "includeUserProfile": false,
    "includeGroupProfile": false,
    "includeRawAssignments": false,
    "maxApps": 1,
    "failFast": false
  }
}
```

Run:

```bash
okta-app-assignment-exporter --config input/app-assignment-export.config.json --export
```

Review:

```text
assignment_summary.md
app_user_assignments.csv
app_group_assignments.csv
errors.csv
execution_report.md
```

## Troubleshooting

### Configuration error: targetOrgUrl must use the normal Okta org base URL

You used the Admin Console URL. Use the org base URL instead.

Correct:

```text
https://your-org.okta.com
```

Incorrect:

```text
https://your-org-admin.okta.com
```

### Configuration error: OKTA_API_TOKEN is required for --export

You are trying to export without a token. Add `OKTA_API_TOKEN` to `.env`.

### App label not found

The utility uses exact label matching for `mode: "labels"`. Confirm the label in Okta or use `mode: "all"` with `maxApps` for testing.

### Group assignment endpoint returns an error for a specific app

Some app integrations may not expose group assignments the same way. The utility records that endpoint failure in `errors.csv` and continues unless `failFast` is true.

### Output CSV files contain only headers

That usually means no assignments were found for the selected apps, or the selected app filters did not match anything. Check `assignment_summary.md` and `app_assignment_export_result.json`.

## Tests

Run:

```bash
python -m pytest
```

Compile check:

```bash
python -m compileall src
```
