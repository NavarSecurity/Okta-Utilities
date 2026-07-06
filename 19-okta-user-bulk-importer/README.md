# WARNING

These utilities have limited testing and are provided as-is with no warranty. Use at your own risk.

# 19-okta-user-bulk-importer

`okta-user-bulk-importer` imports users into Okta from a CSV file with dry-run planning, duplicate detection, failure reporting, and evidence output.

This utility is intended for controlled user migration, test tenant seeding, reconciliation-driven imports, and staged onboarding. It does not create applications, groups, policies, authorization servers, or assignments beyond optional user-to-group membership loading.

## What This Utility Does

- Reads users from a CSV file
- Builds Okta user creation payloads
- Validates required profile fields before calling Okta
- Detects duplicate users by login or email
- Creates users through the Okta Users API when `--apply` is used
- Optionally updates existing users when explicitly enabled
- Optionally assigns imported users to existing Okta groups
- Produces a dry-run import plan before changes are made
- Produces created, updated, skipped, failed, group assignment, rollback, and execution evidence outputs
- Redacts password-like values from generated reports

## What This Utility Does Not Do

- It does not create groups
- It does not create apps
- It does not assign users to apps
- It does not remove users
- It does not deactivate users automatically
- It does not import passwords by default
- It does not bypass Okta schema requirements

## Setup

Create and activate a virtual environment.

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

Confirm the CLI works:

```bash
okta-user-bulk-importer --help
```

## Configure Okta Access

Copy the environment example:

```bash
cp .env.example .env
```

Edit `.env`:

```env
OKTA_TARGET_ORG_URL=https://your-org.okta.com
OKTA_API_TOKEN=your-okta-api-token
```

Use the normal Okta org URL. Do not use the Admin Console URL.

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

The API token must have enough permission to read users and create users. If group assignment is enabled, it also needs permission to manage group memberships.

## Prepare the Input Files

Copy the example config:

```bash
cp config.example.json input/user-import.config.json
```

Create a CSV file at:

```text
input/users.csv
```

Minimum CSV example:

```csv
login,email,firstName,lastName
alex.test@example.com,alex.test@example.com,Alex,Test
jordan.test@example.com,jordan.test@example.com,Jordan,Test
```

Extended CSV example:

```csv
login,email,firstName,lastName,displayName,department,title,employeeNumber,groupIds
alex.test@example.com,alex.test@example.com,Alex,Test,Alex Test,IT,Analyst,E1001,00gabc123;00gdef456
```

## Config Fields

The main config file is:

```text
input/user-import.config.json
```

Important fields:

```json
{
  "inputUserCsv": "input/users.csv",
  "profileFieldMap": {
    "login": "login",
    "email": "email",
    "firstName": "firstName",
    "lastName": "lastName",
    "department": "department",
    "title": "title"
  },
  "requiredProfileFields": ["login", "email", "firstName", "lastName"],
  "duplicateLookupField": "login",
  "defaultGroupIds": [],
  "perRowGroupIdsColumn": "groupIds",
  "settings": {
    "skipExisting": true,
    "updateExisting": false,
    "activateUsers": false,
    "continueOnError": true,
    "performDuplicateCheckInDryRun": true,
    "allowPasswordImport": false,
    "assignGroups": false
  }
}
```

### `profileFieldMap`

Maps Okta profile fields to CSV column names.

Example:

```json
"profileFieldMap": {
  "login": "login",
  "email": "email",
  "firstName": "firstName",
  "lastName": "lastName",
  "department": "department"
}
```

This means the value from the CSV column `department` becomes the Okta profile field `department`.

### `requiredProfileFields`

Fields that must be present before the row is eligible for import.

Recommended default:

```json
["login", "email", "firstName", "lastName"]
```

### `duplicateLookupField`

Controls how duplicate users are checked.

Recommended default:

```json
"login"
```

### `activateUsers`

Controls whether Okta activates users immediately after creation.

Recommended first-run value:

```json
false
```

This creates staged users and is safer for testing.

### `assignGroups`

Controls whether the utility adds created or updated users to existing groups.

Recommended first-run value:

```json
false
```

Set this to `true` only after validating the import file and group IDs.

## Run a Dry Run

```bash
okta-user-bulk-importer --config input/user-import.config.json --dry-run
```

Dry-run does not create or update users.

If `performDuplicateCheckInDryRun` is enabled, dry-run performs read-only user lookup calls to detect existing users.

Review the output folder:

```text
output/okta-user-bulk-importer-<timestamp>/
```

Important files:

```text
user_import_plan.json
user_import_result.json
skipped_users.csv
failed_users.csv
execution_report.md
```

## Apply the Import

Only run apply after reviewing the dry-run plan.

```bash
okta-user-bulk-importer --config input/user-import.config.json --apply
```

Apply mode can create users, update users if enabled, and assign users to groups if enabled.

## Output Files

Each run creates a timestamped output folder with:

```text
user_import_plan.json
user_import_result.json
created_users.csv
updated_users.csv
skipped_users.csv
failed_users.csv
group_assignments.csv
rollback_plan.json
execution_report.md
```

### `user_import_plan.json`

Shows each row and the planned action:

```text
create
update
skip_existing
duplicate_blocked
```

### `created_users.csv`

Lists users created by the run.

### `updated_users.csv`

Lists users updated by the run, if `updateExisting` is enabled.

### `skipped_users.csv`

Lists rows skipped because the user already existed or no action was needed.

### `failed_users.csv`

Lists failed rows and Okta API errors.

### `rollback_plan.json`

Contains suggested cleanup actions for users and group memberships created by the run. The utility does not automatically execute rollback actions.

## Recommended First Test

Use this safe starting configuration:

```json
"settings": {
  "skipExisting": true,
  "updateExisting": false,
  "activateUsers": false,
  "continueOnError": true,
  "performDuplicateCheckInDryRun": true,
  "allowPasswordImport": false,
  "assignGroups": false
}
```

This gives you staged user creation without group assignment or password import.

## Safety Notes

- Always run `--dry-run` first
- Start with 1-2 test users before importing a large CSV
- Use staged user creation first by keeping `activateUsers` set to `false`
- Keep `.env` out of Git
- Do not store real passwords in CSV files
- Avoid enabling `updateExisting` until you understand exactly what profile fields will be overwritten
- Avoid enabling `assignGroups` until group IDs are confirmed

## Testing

Install development dependencies:

```bash
python -m pip install -r requirements-dev.txt
```

Run tests:

```bash
pytest
```
