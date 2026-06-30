# 10-okta-app-cloner

`okta-app-cloner` clones selected Okta application configuration from a backup export into a target Okta org with dry-run planning, duplicate checks, sanitized payloads, rollback output, and execution reporting.

This utility is intended for controlled application migration and rebuild work. It reads `applications.json` from a backup created by `01-okta-config-backup` and can create selected applications in a target Okta org.

## What this utility does

- Reads local `applications.json` backup files
- Selects apps by label, source app ID, or sign-on mode
- Sanitizes source app payloads before creation
- Removes source-org object IDs, links, timestamps, generated credentials, secrets, and redacted values
- Checks the target org for existing apps with the same label
- Supports dry-run mode before apply mode
- Requires `--apply` before creating anything
- Writes clone plans, execution results, rollback plans, app mapping CSVs, and Markdown reports

## What this utility does not do

This version does not clone app assignments, group assignments, users, app-specific secrets, provisioning credentials, IdP secrets, custom domains, or production cutover settings.

Client secrets and generated credentials from the source org are intentionally not cloned. New secrets should be generated and handled in the target org.

## Folder structure

```text
10-okta-app-cloner/
  README.md
  SECURITY.md
  .env.example
  config.example.json
  pyproject.toml
  requirements.txt
  requirements-dev.txt
  src/
  input/
    source-backup/
  output/
  samples/
  tests/
```

## Prerequisites

You need:

```text
Python 3.10+
A source backup folder from 01-okta-config-backup
A target Okta org URL
A target Okta API token with permission to read and create applications
```

## Installation

From inside the `10-okta-app-cloner` folder:

### macOS / Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .
```

### Windows PowerShell

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e .
```

Confirm the command works:

```bash
okta-app-cloner --help
```

## Configure the target org

Copy the environment example:

```bash
cp .env.example .env
```

Edit `.env`:

```text
OKTA_TARGET_ORG_URL=https://target-org.okta.com
OKTA_TARGET_API_TOKEN=your_target_org_api_token
```

Do not include `/admin`, `/api/v1`, or the `SSWS` prefix.

## Prepare the source backup

You can either copy a backup into:

```text
input/source-backup/
```

or point directly to a backup folder using `--source-backup-dir`.

The source backup must contain:

```text
applications.json
```

## Create a working config

Copy the example config:

```bash
cp config.example.json input/cloner.config.json
```

Example config:

```json
{
  "sourceBackupDir": "input/source-backup",
  "targetOrgUrl": "https://target-org.okta.com",
  "outputDir": "output",
  "selection": {
    "applications": {
      "labels": ["Customer Portal OIDC"],
      "ids": [],
      "signOnModes": []
    }
  },
  "skipExisting": true,
  "cloneInactiveApps": false,
  "activateClonedApps": false,
  "includeAssignments": false,
  "includeProvisioningSettings": false,
  "failFast": false,
  "pageLimit": 200,
  "timeoutSeconds": 30,
  "maxRetries": 4,
  "retryBaseSeconds": 1.0,
  "redactionEnabled": true
}
```

## Run a dry run

Dry run is the default and should always be run first:

```bash
okta-app-cloner --config input/cloner.config.json --dry-run
```

Or point directly to a backup folder:

```bash
okta-app-cloner \
  --source-backup-dir ../01-okta-config-backup/output/<backup-folder> \
  --labels "Customer Portal OIDC" \
  --dry-run
```

Dry-run mode:

```text
Reads the source backup
Builds a clone plan
Sanitizes app payloads
Checks for existing target apps with the same label
Writes evidence output
Does not create apps
```

## Apply the clone

Only after reviewing the dry-run output, run:

```bash
okta-app-cloner --config input/cloner.config.json --apply
```

Or:

```bash
okta-app-cloner \
  --source-backup-dir ../01-okta-config-backup/output/<backup-folder> \
  --labels "Customer Portal OIDC" \
  --apply
```

## Clone one app by label

```bash
okta-app-cloner \
  --source-backup-dir ../01-okta-config-backup/output/<backup-folder> \
  --labels "Customer Portal OIDC" \
  --dry-run
```

Then:

```bash
okta-app-cloner \
  --source-backup-dir ../01-okta-config-backup/output/<backup-folder> \
  --labels "Customer Portal OIDC" \
  --apply
```

## Clone one app by source app ID

```bash
okta-app-cloner \
  --source-backup-dir ../01-okta-config-backup/output/<backup-folder> \
  --ids "0oa123abc456" \
  --dry-run
```

## Output files

Each run creates:

```text
output/okta-app-cloner-YYYYMMDDTHHMMSSZ/
  clone_plan.json
  clone_result.json
  rollback_plan.json
  app_mapping.csv
  execution_report.md
```

Open `execution_report.md` first for a readable summary.

## Duplicate behavior

If `skipExisting` is `true`, the utility checks the target org for an app with the same label and skips creation if one already exists.

This helps prevent duplicate app creation.

## Rollback behavior

When apply mode creates an app, the utility writes a `rollback_plan.json` entry with the target app ID and the delete endpoint.

Rollback is not automatically executed. Review the rollback plan before using it.

## Recommended workflow

```text
1. Run 01-okta-config-backup against the source org.
2. Validate the backup with 05-okta-backup-validator.
3. Run okta-app-cloner in dry-run mode.
4. Review clone_plan.json and execution_report.md.
5. Run okta-app-cloner with --apply.
6. Validate the target org with a new backup, inventory, or diff.
```

## Testing

```bash
python -m pip install -r requirements-dev.txt
pytest
python -m compileall src tests
```

## Disclaimer

WARNING: These utilities have limited testing and are provided as-is with no warranty. Use at your own risk.

## Version 0.1.1 note: source-org key mapping cleanup

This version improves payload sanitization for cloned applications. Okta application backup responses may contain source-org-specific identifiers that should not be sent to a target org during app creation.

The cloner now strips fields such as:

```text
orn
kid
keyId
key_id
keyMappingId
appInstanceKeyMappingId
credentials.signing
credentials.oauthClient
```

This prevents target-org creation failures such as:

```text
404 Resource not found: <source-key-id> (AppInstanceKeyMapping)
```

That error can happen when an OIDC app backup includes a `credentials.signing.kid` value from the source org. The target org does not have that source signing key mapping, so the app create request fails. The target org should generate or assign its own credentials and signing key material.

After cloning, review the created app in the target org and manually verify credentials, signing settings, redirect URIs, grant types, assignments, and activation state before production use.
