# WARNING

These utilities have limited testing and are provided as-is with no warranty. Use at your own risk.

# okta-profile-schema-exporter

Python utility for exporting Okta Universal Directory user profile schemas and app user profile schemas.

This utility is intended for Okta discovery, migration planning, profile cleanup, Universal Directory reviews, app onboarding analysis, and evidence collection before schema or profile mapping changes.

---

## What This Utility Does

The `okta-profile-schema-exporter` utility exports profile schema definitions from an Okta org.

| Export area | Purpose |
|---|---|
| User profile schemas | Export default or specified Okta user profile schemas. |
| App user profile schemas | Export profile schemas for Okta applications. |
| Group profile schema | Optionally export the default Okta group profile schema. |
| Attribute summaries | Produce CSV summaries of schema attributes, types, mutability, permissions, enums, and required fields. |
| Individual schema files | Optionally write one JSON file per exported user schema or app schema. |

Universal Directory schemas are important because they define which profile attributes exist, how they are typed, which attributes are required, and how profile data can be used by applications, directories, mappings, and identity workflows.

---

## Safety Model

This utility is read-only.

It does not create, update, or delete Okta schemas or profile attributes.

Dry-run mode validates configuration without calling Okta:

```bash
okta-profile-schema-exporter --config config.json --dry-run
```

Export mode calls Okta read-only APIs and writes local output files:

```bash
okta-profile-schema-exporter --config config.json
```

The utility should not write API tokens, authorization headers, or secrets to output reports.

---

## Folder Structure

```text
36-okta-profile-schema-exporter/
  README.md
  pyproject.toml
  .env.example
  .gitignore
  config.example.json
  src/
    okta_profile_schema_exporter/
      __init__.py
      __main__.py
      cli.py
      config.py
      okta_client.py
      exporter.py
      normalize.py
      redact.py
      reports.py
  samples/
    config.export.sample.json
    config.user-only.sample.json
    config.selected-apps.sample.json
    apps.txt
    sample-user-schema.json
    sample-app-schema.json
  tests/
    test_config.py
    test_exporter.py
    test_normalize.py
    test_redact.py
    test_okta_client.py
  input/
    apps.txt
  output/
    .gitkeep
```

---

## Requirements

- Python 3.10 or newer
- Okta admin API token
- Okta org URL
- Network access to the Okta tenant

The Okta API token should be generated from an account with permission to read users, applications, and profile schemas.

---

## Setup

Run these commands from the utility folder.

Create a virtual environment:

```bash
python3 -m venv .venv
```

Activate the virtual environment on macOS or Linux:

```bash
source .venv/bin/activate
```

Activate the virtual environment on Windows PowerShell:

```powershell
.venv\Scripts\Activate.ps1
```

Install the utility:

```bash
python -m pip install -e .
```

Copy the environment example:

```bash
cp .env.example .env
```

Copy a sample configuration file:

```bash
cp samples/config.export.sample.json config.json
```

Open `.env` and update the Okta values.

---

## Environment Variables

Create a `.env` file using `.env.example`.

Example:

```env
OKTA_ORG_URL=https://your-org.okta.com
OKTA_API_TOKEN=replace-with-okta-api-token
```

Do not commit `.env` files.

The `.gitignore` file should exclude generated output while keeping the output folder present:

```gitignore
.env
.venv/
__pycache__/
*.pyc
.pytest_cache/

# Keep output directory, ignore generated contents
output/*
!output/.gitkeep
```

---

## Configuration

The utility is driven by `config.json`.

Example full export configuration:

```json
{
  "outputDirectory": "output",
  "includeUserSchemas": true,
  "userSchemaIds": ["default"],
  "includeGroupSchema": false,
  "includeAppSchemas": true,
  "appSelection": {
    "mode": "all",
    "appIds": [],
    "appNames": [],
    "appFile": "input/apps.txt"
  },
  "includeInactiveApps": false,
  "skipOktaSystemApps": true,
  "excludedAppNames": [
    "saasure",
    "okta_enduser",
    "okta_browser_plugin",
    "okta_oin_submission_tester_app",
    "okta_iga_reviewer"
  ],
  "continueOnAppSchemaError": true,
  "writeIndividualSchemaFiles": true,
  "redactSensitiveValues": true,
  "timeoutSeconds": 30,
  "maxRetries": 3
}
```

Example user-schema-only configuration:

```json
{
  "outputDirectory": "output",
  "includeUserSchemas": true,
  "userSchemaIds": ["default"],
  "includeGroupSchema": false,
  "includeAppSchemas": false,
  "appSelection": {
    "mode": "none"
  },
  "writeIndividualSchemaFiles": true,
  "redactSensitiveValues": true
}
```

Example selected app configuration:

```json
{
  "outputDirectory": "output",
  "includeUserSchemas": true,
  "userSchemaIds": ["default"],
  "includeGroupSchema": false,
  "includeAppSchemas": true,
  "appSelection": {
    "mode": "names",
    "appIds": [],
    "appNames": ["Sample SAML App", "Sample OIDC App"],
    "appFile": "input/apps.txt"
  },
  "includeInactiveApps": true,
  "skipOktaSystemApps": true,
  "excludedAppNames": [
    "saasure",
    "okta_enduser",
    "okta_browser_plugin",
    "okta_oin_submission_tester_app",
    "okta_iga_reviewer"
  ],
  "continueOnAppSchemaError": true,
  "writeIndividualSchemaFiles": true,
  "redactSensitiveValues": true
}
```

---

## App Selection Modes

The `appSelection.mode` value controls which app schemas are exported.

| Mode | Behavior |
|---|---|
| `all` | Export app schemas for all discovered apps. |
| `ids` | Export only apps listed in `appSelection.appIds`. |
| `names` | Export only apps listed in `appSelection.appNames`. Matching uses app label or app name. |
| `file` | Export apps listed in `appSelection.appFile`. One app ID, label, or name per line. |
| `none` | Do not export app schemas. |

Example app file:

```text
# Add app IDs, app labels, or app names. One value per line.
Sample SAML App
0oa123example
```

---

## Okta System App Exclusion

By default, the utility skips known Okta-owned system and internal apps that do not expose useful app user profile schemas through the app schema endpoint. This prevents avoidable 404 warnings for apps such as:

```text
Okta Admin Console
Okta Dashboard
Okta Browser Plugin
Okta OIN Submission Tester
Okta Access Certification Reviews
```

The default exclusion is controlled by these settings:

```json
{
  "skipOktaSystemApps": true,
  "excludedAppNames": [
    "saasure",
    "okta_enduser",
    "okta_browser_plugin",
    "okta_oin_submission_tester_app",
    "okta_iga_reviewer"
  ]
}
```

When `skipOktaSystemApps` is true, these apps are not selected for app schema export. The utility writes them to `skipped_apps.json` and `skipped_apps.csv` for evidence, but it does not call the app schema endpoint for them.

Set `skipOktaSystemApps` to false only if you intentionally want to test schema retrieval against Okta internal apps.

---

## Run a Dry Run

Run a dry run first:

```bash
okta-profile-schema-exporter --config config.json --dry-run
```

Expected output:

```text
output/profile-schema-export-<timestamp>/
  execution_report.json
  manifest.json
```

Dry-run mode validates the configuration and writes a report. It does not call Okta.

---

## Export Profile Schemas

Run the export:

```bash
okta-profile-schema-exporter --config config.json
```

Expected output:

```text
output/profile-schema-export-<timestamp>/
  user_schemas_full.json
  app_schemas_full.json
  apps_inventory.json
  skipped_apps.json
  skipped_apps.csv
  selected_apps.json
  profile_schema_attributes.csv
  schema_summary.csv
  execution_report.json
  manifest.json
  schemas_by_user_type/
  schemas_by_app/
```

If `includeGroupSchema` is enabled, the utility also writes:

```text
group_schema_full.json
```

If app schema export fails for some apps and `continueOnAppSchemaError` is enabled, the utility writes:

```text
app_schema_failures.csv
```

---

## Output Reports

Each run creates timestamped output.

| File | Purpose |
|---|---|
| `user_schemas_full.json` | Full exported user profile schemas. |
| `group_schema_full.json` | Optional full exported group profile schema. |
| `apps_inventory.json` | Exportable apps discovered during the run after system/internal app exclusion. |
| `skipped_apps.json` | Okta-owned system/internal apps skipped from app schema export. |
| `skipped_apps.csv` | CSV version of skipped app evidence. |
| `selected_apps.json` | Apps selected for app schema export. |
| `app_schemas_full.json` | Full exported app user profile schemas. |
| `profile_schema_attributes.csv` | Flattened attribute inventory across exported schemas. |
| `schema_summary.csv` | Attribute counts by schema/app. |
| `app_schema_failures.csv` | App schema export failures and warnings. |
| `execution_report.json` | Counts, warnings, errors, and run metadata. |
| `manifest.json` | Operation metadata and output file list. |
| `schemas_by_user_type/` | Individual user schema files. |
| `schemas_by_app/` | Individual app schema files. |

Execution reports should not include API tokens or sensitive headers.

---

## Recommended Workflow

For client work, start with a default user and active app schema export:

```bash
cp samples/config.export.sample.json config.json
okta-profile-schema-exporter --config config.json --dry-run
okta-profile-schema-exporter --config config.json
```

Review the attribute inventory:

```text
output/profile-schema-export-<timestamp>/profile_schema_attributes.csv
```

Review schema-level counts:

```text
output/profile-schema-export-<timestamp>/schema_summary.csv
```

For a smaller export focused only on user profile schema:

```bash
cp samples/config.user-only.sample.json config.json
okta-profile-schema-exporter --config config.json --dry-run
okta-profile-schema-exporter --config config.json
```

For a selected app export:

```bash
cp samples/config.selected-apps.sample.json config.json
okta-profile-schema-exporter --config config.json --dry-run
okta-profile-schema-exporter --config config.json
```

---

## Testing

Install test dependencies:

```bash
python -m pip install -e ".[dev]"
```

Run tests:

```bash
pytest
```

Run tests with verbose output:

```bash
pytest -v
```

---

## Troubleshooting

### 401 Unauthorized

Confirm the Okta org URL and API token in `.env`.

```bash
cat .env
```

The org URL should look like:

```text
https://your-org.okta.com
```

Do not include `/api/v1` in `OKTA_ORG_URL`.

---

### 403 Forbidden

The API token may not have sufficient permissions to read apps or schemas.

Confirm the token was generated by an Okta admin account with the required permissions.

---

### App schema failures

Some app types may not expose an app user profile schema or may return an API error for schema retrieval. Known Okta system/internal apps are skipped by default before schema requests are made.

If `continueOnAppSchemaError` is true, the utility continues and writes any remaining failures to:

```text
app_schema_failures.csv
```

Review skipped system/internal apps in:

```text
skipped_apps.csv
```

---

### Too many apps exported

Use a more selective app mode.

Select apps by name:

```json
{
  "appSelection": {
    "mode": "names",
    "appNames": ["Sample SAML App"]
  }
}
```

Select apps by ID:

```json
{
  "appSelection": {
    "mode": "ids",
    "appIds": ["0oa123example"]
  }
}
```

Select apps from a file:

```json
{
  "appSelection": {
    "mode": "file",
    "appFile": "input/apps.txt"
  }
}
```

---

## Security Notes

- Do not commit `.env`.
- Do not commit raw client exports unless they have been reviewed and approved.
- Treat schema data as sensitive because it may reveal HR attributes, employee identifiers, internal naming conventions, app-specific profile fields, or provisioning design.
- Review custom attributes before using exported schemas for migration planning.
- Use output reports as evidence, not as direct import files without review.

---

## Practical Use Cases

Use this utility to:

- Export Okta Universal Directory user schema attributes.
- Identify custom user profile attributes before migration.
- Review app user profile schemas before app onboarding or app cloning.
- Compare expected attributes against what applications require.
- Support profile mapping and provisioning design.
- Collect evidence before schema cleanup.
- Build an attribute inventory for IAM assessments.
- Identify required, unique, enum-based, or read-only attributes.

---

## Notes

Profile schemas are foundational to Okta Universal Directory, provisioning, profile mappings, and app integrations. Review schema exports carefully before changing attributes, profile mappings, or lifecycle automation.

This utility exports schema data only. It does not create or update schema attributes.
