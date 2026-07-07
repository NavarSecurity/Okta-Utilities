# WARNING

These utilities have limited testing and are provided as-is with no warranty. Use at your own risk.

# 23-okta-group-create

`okta-group-create` creates Okta groups from CSV, JSON, or YAML input.

It is intended for controlled group creation during Okta onboarding, migration preparation, user/group management cleanup, and environment buildout.

## Purpose

Use this utility when you need to create multiple Okta groups in a repeatable way instead of manually creating each group in the Admin Console.

The utility can help with:

```text
Creating standard access groups
Creating migration target groups
Creating application assignment groups
Creating test groups for user and assignment utilities
Creating groups from reviewed CSV, JSON, or YAML input
Producing evidence of what was planned, created, skipped, or failed
```

## What this utility does

```text
Reads group definitions from CSV, JSON, or YAML
Builds Okta group creation payloads
Runs dry-run mode by default
Creates groups only when --apply is used
Checks for existing groups before creation
Skips duplicates by default
Supports optional approval gating
Creates rollback_plan.json with delete endpoints for created groups
Writes CSV, JSON, and Markdown evidence output
Rejects -admin Okta URLs
```

## What this utility does not do

```text
Does not create users
Does not assign users to groups
Does not assign groups to apps
Does not delete or update existing groups
Does not create group rules
```

Use Utility 24 for group membership loading and Utility 26 for group rule creation.

## Setup

### Prerequisites

You need:

```text
Python 3.10+
An Okta org URL
An Okta API token with permission to read and create groups
Reviewed group input file in CSV, JSON, or YAML format
```

### Create a virtual environment

macOS / Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Windows PowerShell:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### Install the utility

```bash
python -m pip install --upgrade pip
python -m pip install -e .
```

Confirm the command works:

```bash
okta-group-create --help
```

## Environment configuration

Copy `.env.example` to `.env`.

macOS / Linux:

```bash
cp .env.example .env
```

Windows PowerShell:

```powershell
Copy-Item .env.example .env
```

Populate `.env` with your Okta values:

```env
OKTA_TARGET_ORG_URL=https://your-org.okta.com
OKTA_API_TOKEN=your-okta-api-token
```

Use the normal Okta org URL.

Correct:

```text
https://your-org.okta.com
```

Incorrect:

```text
https://your-org-admin.okta.com
https://your-org.okta.com/admin
https://your-org.okta.com/api/v1
```

Do not commit `.env`.

## Create a working config file

Copy the example config:

```bash
cp config.example.json input/group-create.config.json
```

Windows PowerShell:

```powershell
Copy-Item config.example.json input/group-create.config.json
```

Open:

```text
input/group-create.config.json
```

Example:

```json
{
  "targetOrgUrl": "https://your-org.okta.com",
  "groupsFile": "input/groups.csv",
  "settings": {
    "skipExisting": true,
    "requireApproved": false,
    "approvedValues": ["true", "yes", "y", "approved"],
    "continueOnError": false,
    "maxGroupsPerRun": 100,
    "requestTimeoutSeconds": 30,
    "maxRetries": 3,
    "retryBackoffSeconds": 2
  },
  "columns": {
    "name": "name",
    "description": "description",
    "approved": "approved"
  },
  "profileFieldMappings": {
    "name": "name",
    "description": "description"
  }
}
```

## Input formats

### CSV input

Example `input/groups.csv`:

```csv
name,description,approved
Finance App Users,Users allowed to access finance applications,true
Salesforce Users,Users allowed to access Salesforce,true
VPN Users,Users allowed to access VPN,true
```

Required field:

```text
name
```

Recommended fields:

```text
description
approved
```

### JSON input

```json
{
  "groups": [
    {
      "name": "Finance App Users",
      "description": "Users allowed to access finance applications",
      "approved": true
    },
    {
      "profile": {
        "name": "Salesforce Users",
        "description": "Users allowed to access Salesforce"
      },
      "approved": true
    }
  ]
}
```

### YAML input

```yaml
groups:
  - name: Finance App Users
    description: Users allowed to access finance applications
    approved: true
  - profile:
      name: Salesforce Users
      description: Users allowed to access Salesforce
    approved: true
```

## Config field explanations

| Field | Purpose |
|---|---|
| `targetOrgUrl` | Okta org URL. Overridden by `OKTA_TARGET_ORG_URL` when present. |
| `groupsFile` | CSV, JSON, or YAML file containing groups to create. |
| `skipExisting` | If true, existing groups are skipped instead of treated as failures. |
| `requireApproved` | If true, only rows with an approved value are eligible for creation. |
| `approvedValues` | Accepted approval values when approval gating is enabled. |
| `continueOnError` | If true, continue processing after a failed group creation. |
| `maxGroupsPerRun` | Safety limit for group creation volume. |
| `columns` | CSV column names for common values. |
| `profileFieldMappings` | Maps input fields to Okta group profile fields. |

## Run a dry run first

```bash
okta-group-create --config input/group-create.config.json --dry-run
```

Dry-run mode:

```text
Reads the input file
Validates group rows
Builds the planned Okta payloads
Writes evidence output
Does not call Okta write APIs
Does not create groups
```

Review the output folder:

```text
output/okta-group-create-<timestamp>/
```

Important dry-run files:

```text
group_create_plan.json
group_create_result.json
skipped_groups.csv
execution_report.md
```

## Apply group creation

After reviewing the dry-run output:

```bash
okta-group-create --config input/group-create.config.json --apply
```

Apply mode:

```text
Checks whether each group already exists
Creates missing groups
Skips existing groups when skipExisting is true
Writes created, existing, skipped, failed, and rollback output
```

## Output files

Each run creates a timestamped folder:

```text
output/okta-group-create-YYYYMMDDTHHMMSSZ/
```

Files:

```text
group_create_plan.json
group_create_result.json
created_groups.csv
existing_groups.csv
skipped_groups.csv
failed_groups.csv
rollback_plan.json
execution_report.md
```

## Rollback plan

When groups are created, the utility writes `rollback_plan.json` with delete endpoints for the groups created in that run.

Example:

```json
{
  "action": "delete_group",
  "groupId": "00gabc123",
  "method": "DELETE",
  "endpoint": "/api/v1/groups/00gabc123"
}
```

The utility does not automatically rollback. Review the rollback plan before using it.

## Recommended first test

Use a small CSV with one or two harmless test groups:

```csv
name,description,approved
Utility 23 Test Group 01,Test group created by Utility 23,true
Utility 23 Test Group 02,Second test group created by Utility 23,true
```

Run dry-run first, then apply only after confirming the plan.

## Troubleshooting

### `Use the normal Okta org URL, not the Admin Console URL`

Your URL likely contains `-admin` or `/admin`.

Use:

```text
https://your-org.okta.com
```

not:

```text
https://your-org-admin.okta.com
```

### `OKTA_API_TOKEN is required for apply mode`

Set `OKTA_API_TOKEN` in `.env`.

Dry-run does not require a token, but apply mode does.

### Group was skipped as existing

The group already exists in Okta and `skipExisting` is enabled.

This is expected idempotent behavior.

### Group was skipped as not approved

`requireApproved` is enabled and the row does not have an accepted approval value.

Set the row to one of:

```text
true
yes
y
approved
```

or disable `requireApproved`.

### `maxGroupsPerRun` exceeded

The input file contains more groups than the configured safety limit.

Increase `maxGroupsPerRun` only after reviewing the input file.

## Development

Install development dependencies:

```bash
python -m pip install -r requirements-dev.txt
```

Run tests:

```bash
pytest
```

Compile check:

```bash
python -m compileall src tests
```
