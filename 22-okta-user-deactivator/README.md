# WARNING

These utilities have limited testing and are provided as-is with no warranty. Use at your own risk.

# 22-okta-user-deactivator

`okta-user-deactivator` bulk suspends, deprovisions, or deletes approved Okta users from a CSV file with dry-run, confirmation controls, rollback planning, and evidence reporting.

The utility name is preserved for compatibility with the original Utility 22 command, but the utility now handles broader user lifecycle actions.

## What this utility does

The utility reads a CSV file of approved users and prepares a lifecycle action plan.

Supported actions:

```text
suspend
deprovision
deactivate    # legacy alias; normalized to deprovision
delete        # optional; only allowed for deprovisioned users by default
```

The CSV can identify users by:

```text
Okta user ID
login
email
```

Apply mode can call Okta lifecycle/API endpoints to suspend, deprovision, or delete approved users.

## What this utility does not do

This utility does **not** create users or groups.

It does **not** remove app assignments directly.

It does **not** automatically execute rollback actions.

It does **not** delete active users by default. Delete is blocked unless `allowDeleteDeprovisionedUsers` is enabled, and deletion requires the user to already be `DEPROVISIONED` by default.

It does **not** bypass Okta lifecycle behavior. Deprovisioning users may trigger downstream app deprovisioning depending on the org and app configuration.

## When to use it

Use this utility when you have an approved list of users that should be suspended, deprovisioned, or deleted after deprovisioning.

Common use cases:

```text
Dormant account cleanup
Migration cutover cleanup
Post-reconciliation cleanup
Terminated user batch processing
Sandbox test-user cleanup
Access governance remediation
Cleanup of deprovisioned test accounts
```

## Required safety model

The utility is built around five safety controls:

```text
Dry-run by default
Approval column required by default
Reason column required by default
Confirmation phrase required for apply mode
Delete disabled by default unless explicitly enabled
```

The default apply confirmation phrase is:

```text
APPLY APPROVED USER LIFECYCLE ACTIONS
```

## Folder structure

```text
22-okta-user-deactivator/
  README.md
  SECURITY.md
  .gitignore
  .env.example
  config.example.json
  pyproject.toml
  requirements.txt
  requirements-dev.txt
  src/
  input/
  output/
  samples/
  tests/
```

## Prerequisites

You need:

```text
Python 3.10+
Okta org URL
Okta API token with user lifecycle permissions
A reviewed CSV file of users to suspend, deprovision, or delete
```

Use a non-production Okta org first.

## Setup

Create a virtual environment from inside the utility folder.

### macOS / Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### Windows PowerShell

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Install the utility:

```bash
python -m pip install --upgrade pip
python -m pip install -e .
```

Confirm the command is available:

```bash
okta-user-deactivator --help
```

## Configure environment variables

Copy the example environment file:

```bash
cp .env.example .env
```

Edit `.env`:

```env
OKTA_TARGET_ORG_URL=https://your-org.okta.com
OKTA_API_TOKEN=replace-with-token
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
```

The `.env` value takes priority over the JSON config value.

## Create a working config

Copy the example config:

```bash
cp config.example.json input/user-lifecycle.config.json
```

Open:

```text
input/user-lifecycle.config.json
```

Default config:

```json
{
  "targetOrgUrl": "https://your-org.okta.com",
  "inputFile": "input/users-to-deprovision.csv",
  "outputDir": "output",
  "settings": {
    "defaultAction": "suspend",
    "requireApproved": true,
    "requireReason": true,
    "continueOnError": false,
    "maxUsersPerRun": 100,
    "verifyUsersOnDryRun": false,
    "sendDeprovisionEmail": false,
    "sendDeleteEmail": false,
    "skipAlreadyInTargetState": true,
    "allowDeleteDeprovisionedUsers": false,
    "requireDeprovisionedBeforeDelete": true
  }
}
```

## Prepare the input CSV

Copy the sample CSV:

```bash
cp samples/users-to-deprovision.sample.csv input/users-to-deprovision.csv
```

Minimum useful columns:

```csv
id,login,email,action,approved,reason
,utility22.test.user01@example.com,utility22.test.user01@example.com,suspend,true,Dormant test account
,utility22.test.user02@example.com,utility22.test.user02@example.com,deprovision,true,Approved deprovisioning
,utility22.test.user03@example.com,utility22.test.user03@example.com,delete,true,Approved deletion after deprovisioning
```

You can use only `id`, only `login`, or only `email`, but `id` is preferred when available.

## CSV columns

| Column | Purpose |
|---|---|
| `id` | Okta user ID. Preferred identifier. |
| `login` | Okta login. Used when `id` is blank. |
| `email` | Email address. Used when `id` and `login` are blank. |
| `action` | `suspend`, `deprovision`, `deactivate`, or `delete`. |
| `approved` | Must be an approved value such as `true`, `yes`, `y`, or `approved`. |
| `reason` | Required by default. Provides audit context. |

## Action difference

### Suspend

Suspending a user blocks access but keeps the user record and app assignments in place.

Rollback suggestion:

```text
POST /api/v1/users/{userId}/lifecycle/unsuspend
```

### Deprovision

Deprovisioning a user uses Okta's deactivate lifecycle action. In Okta user status terms, the result is normally `DEPROVISIONED`.

Rollback suggestion:

```text
POST /api/v1/users/{userId}/lifecycle/activate?sendEmail=false
```

Deprovisioning can have broader impact than suspension because downstream apps may also be deprovisioned depending on app provisioning settings.

### Delete

Deleting removes an already deprovisioned user from Okta.

Delete is intentionally blocked by default. To allow delete rows, set:

```json
"allowDeleteDeprovisionedUsers": true
```

By default, the utility will only delete a user if the resolved Okta user status is:

```text
DEPROVISIONED
```

That behavior is controlled by:

```json
"requireDeprovisionedBeforeDelete": true
```

Deleted users do not receive rollback entries because this utility cannot restore a deleted user.

## Run a dry run

```bash
okta-user-deactivator --config input/user-lifecycle.config.json --dry-run
```

Dry-run mode:

```text
Reads the CSV
Checks approval and reason fields
Builds the action plan
Writes evidence output
Does not call lifecycle mutation endpoints
Does not suspend, deprovision, or delete users
```

If `verifyUsersOnDryRun` is set to `true`, dry-run also resolves users through the Okta API, but it still does not change users.

## Review the dry-run output

Each run creates a timestamped folder:

```text
output/okta-user-lifecycle-YYYYMMDDTHHMMSSZ/
```

Review these files before apply mode:

```text
user_lifecycle_plan.csv
user_lifecycle_plan.json
user_lifecycle_result.json
skipped_users.csv
execution_report.md
```

Confirm:

```text
Only intended users are planned
No admin or break-glass accounts are included
Each planned user has approved=true
Each planned user has a reason
The action is suspend, deprovision, or delete as intended
Delete rows are only for already deprovisioned users
```

## Apply the approved actions

Apply mode requires the confirmation phrase.

```bash
okta-user-deactivator \
  --config input/user-lifecycle.config.json \
  --apply \
  --confirm "APPLY APPROVED USER LIFECYCLE ACTIONS"
```

Apply mode:

```text
Resolves each user in Okta
Checks safety rules again
Suspends, deprovisions, or deletes approved users
Skips users already in the target state
Skips delete actions when the user is not DEPROVISIONED by default
Writes rollback and evidence files
```

## Apply output files

Apply mode writes:

```text
changed_users.csv
skipped_users.csv
failed_users.csv
rollback_plan.json
user_lifecycle_result.json
execution_report.md
```

Use these files for audit evidence and change records.

Backward-compatible aliases are also written for earlier Utility 22 naming:

```text
user_deactivation_plan.csv
user_deactivation_plan.json
user_deactivation_result.json
```

## Rollback plan

The utility writes `rollback_plan.json` for successful suspend and deprovision actions.

Example rollback entry:

```json
{
  "userId": "00uabc123",
  "login": "user@example.com",
  "originalAction": "deprovision",
  "rollbackAction": "activate",
  "rollbackEndpoint": "POST /api/v1/users/00uabc123/lifecycle/activate?sendEmail=false"
}
```

The utility does not automatically rollback because lifecycle restoration should be reviewed first.

Delete actions do not create rollback entries.

## Important safety notes

Avoid using this utility against your own admin account.

Avoid using broad CSV exports without review.

Start with one test user in a sandbox org.

Use `suspend` before `deprovision` while learning.

Only use `delete` for already deprovisioned test users or approved cleanup records.

Do not put real client, customer, admin, break-glass, or service-account users in a test CSV.

Do not share `.env`, local config files with tokens, output folders, or real user exports.

## Recommended first test

Use one staged or test user:

```csv
id,login,email,action,approved,reason
,utility22.test.user01@example.com,utility22.test.user01@example.com,suspend,true,Utility 22 sandbox test
```

Run dry-run first:

```bash
okta-user-deactivator --config input/user-lifecycle.config.json --dry-run
```

Only run apply after reviewing the plan.

## Troubleshooting

### `Apply mode requires the configured confirmation phrase`

Apply mode requires:

```bash
--confirm "APPLY APPROVED USER LIFECYCLE ACTIONS"
```

unless you change the phrase in config.

### `User was not approved for action`

The row is missing an approved value.

Set:

```csv
approved
true
```

### `Reason is required`

The row is missing a reason.

Add a review reason to the CSV.

### `Delete action is disabled`

Delete rows are blocked unless you set:

```json
"allowDeleteDeprovisionedUsers": true
```

### `Delete skipped because the user is not DEPROVISIONED`

The resolved Okta user was not already deprovisioned. Deprovision the user first, then run a separate delete batch after review.

### `Login matched blocked login pattern`

The login matched a configured safety pattern such as `admin`, `breakglass`, or `svc-`.

Review before changing safety settings.

### `Use the normal Okta org URL`

You used the Admin Console URL.

Use:

```text
https://your-org.okta.com
```

not:

```text
https://your-org-admin.okta.com
```

## Development

Install test dependencies:

```bash
python -m pip install -r requirements-dev.txt
```

Run tests:

```bash
pytest
```

Run syntax validation:

```bash
python -m compileall src tests
```
