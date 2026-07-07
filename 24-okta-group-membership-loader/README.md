# WARNING

These utilities have limited testing and are provided as-is with no warranty. Use at your own risk.

# 24-okta-group-membership-loader

`okta-group-membership-loader` bulk adds, removes, or replaces Okta group memberships from a reviewed CSV, JSON, or YAML input file.

It is intended for controlled Okta group membership loading during migrations, app access onboarding, user cleanup, access remediation, and test data setup.

## Purpose

Use this utility when you need to apply approved group membership changes in a repeatable and evidence-backed way instead of manually adding or removing each user in the Okta Admin Console.

The utility can help with:

```text
Adding users to existing Okta groups
Removing users from existing Okta groups after review
Replacing a group's membership with a reviewed desired member list
Loading group memberships after user import or migration
Producing evidence of planned, applied, skipped, and failed records
Producing rollback_plan.json for changes created by the run
```

## What this utility does

```text
Reads group membership actions from CSV, JSON, or YAML
Supports add, remove, and replace actions
Runs dry-run mode by default
Requires --apply plus an explicit confirmation phrase before changes are made
Resolves groupId directly or groupName by lookup when enabled
Resolves userId directly or login/email by lookup when enabled
Checks current group membership before adding or removing when verification is enabled
Skips existing memberships by default during add
Skips missing memberships by default during remove
Blocks remove and replace unless explicitly enabled in config
Creates rollback_plan.json
Writes CSV, JSON, and Markdown evidence output
Rejects -admin Okta URLs
```

## What this utility does not do

```text
Does not create groups
Does not create users
Does not delete groups
Does not deactivate users
Does not create group rules
Does not assign groups to apps
Does not grant admin roles
```

Use Utility 23 to create groups. Use Utility 19 to import users. Use Utility 26 for group rule creation.

## Setup

### Prerequisites

You need:

```text
Python 3.10+
An Okta org URL
An Okta API token with permission to read users, read groups, and modify group membership
Reviewed group membership input file in CSV, JSON, or YAML format
Existing Okta groups
Existing Okta users
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
okta-group-membership-loader --help
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

macOS / Linux:

```bash
cp config.example.json input/group-membership-loader.config.json
```

Windows PowerShell:

```powershell
Copy-Item config.example.json input/group-membership-loader.config.json
```

Open:

```text
input/group-membership-loader.config.json
```

Example:

```json
{
  "targetOrgUrl": "https://your-org.okta.com",
  "membershipFile": "input/group-memberships.csv",
  "inputFormat": "auto",
  "defaultAction": "add",
  "settings": {
    "continueOnError": false,
    "requestTimeoutSeconds": 30,
    "maxRetries": 3,
    "retryBackoffSeconds": 2,
    "verifyExistingStateInDryRun": true
  },
  "safety": {
    "requireApproved": true,
    "approvedValues": ["true", "yes", "y", "approved"],
    "requireReason": true,
    "maxChangesPerRun": 250,
    "allowRemove": false,
    "allowReplace": false,
    "skipExistingAdditions": true,
    "skipMissingRemovals": true,
    "allowGroupNameLookup": true,
    "allowUserLoginLookup": true,
    "blockAdminUsers": true,
    "protectedLoginPatterns": ["admin", "breakglass", "break-glass", "service", "svc-"]
  }
}
```

## Create an input file

For add-only testing, create:

```text
input/group-memberships.csv
```

Example CSV:

```csv
groupId,groupName,userId,login,email,action,approved,reason
00gExampleGroupId01,Finance App Users,00uExampleUserId01,finance.user01@example.com,finance.user01@example.com,add,true,Approved access request for Finance App Users
00gExampleGroupId01,Finance App Users,00uExampleUserId02,finance.user02@example.com,finance.user02@example.com,add,true,Approved access request for Finance App Users
```

Recommended columns:

```text
groupId
groupName
userId
login
email
action
approved
reason
```

The safest input uses real Okta IDs:

```text
groupId
userId
```

Using `groupName`, `login`, or `email` requires lookup calls to Okta.

## Actions

### Add

Adds a user to a group.

```csv
groupId,userId,action,approved,reason
00gExampleGroupId01,00uExampleUserId01,add,true,Approved access request
```

Okta endpoint used in apply mode:

```text
PUT /api/v1/groups/{groupId}/users/{userId}
```

### Remove

Removes a user from a group.

```csv
groupId,userId,action,approved,reason
00gExampleGroupId01,00uExampleUserId01,remove,true,Approved removal request
```

To allow remove actions, set:

```json
"allowRemove": true
```

Okta endpoint used in apply mode:

```text
DELETE /api/v1/groups/{groupId}/users/{userId}
```

### Replace

Treats the rows for a group as the desired final membership list. The utility adds missing desired users and removes current users who are not in the desired list.

To allow replace actions, set:

```json
"allowReplace": true
```

Use replace carefully. It can remove users from groups if they are not present in the reviewed input file.

## Run a dry run

```bash
okta-group-membership-loader --config input/group-membership-loader.config.json --dry-run
```

Dry-run writes an output folder like:

```text
output/okta-group-membership-loader-20260707T120000Z/
```

Review these files before apply:

```text
group_membership_plan.json
membership_changes.csv
skipped_memberships.csv
failed_memberships.csv
rollback_plan.json
execution_report.md
```

## Apply approved membership changes

Apply mode requires a confirmation phrase.

```bash
okta-group-membership-loader \
  --config input/group-membership-loader.config.json \
  --apply \
  --confirm "APPLY GROUP MEMBERSHIP CHANGES"
```

Apply mode modifies Okta group membership.

## Output files

```text
loader_result.json
Full JSON result for the run.

group_membership_plan.json
Planned membership changes.

membership_changes.csv
Planned membership changes in reviewable CSV format.

applied_membership_changes.csv
Changes that were actually applied in apply mode.

skipped_memberships.csv
Rows skipped because of approval, safety, duplicate, missing membership, or validation checks.

failed_memberships.csv
Rows that failed during lookup or API execution.

rollback_plan.json
Suggested rollback operations for planned or applied changes.

execution_report.md
Human-readable summary of the run.
```

## Recommended workflow

```text
1. Create or confirm target groups exist.
2. Create or confirm target users exist.
3. Build and review input/group-memberships.csv.
4. Mark only approved rows with approved=true.
5. Run dry-run.
6. Review membership_changes.csv and skipped_memberships.csv.
7. Run apply only after review.
8. Save the output folder as implementation evidence.
```

## Safety notes

```text
Start with add-only tests.
Leave allowRemove=false until you intentionally need removals.
Leave allowReplace=false until you intentionally need full group membership replacement.
Use groupId and userId when possible.
Do not use production admin accounts for testing.
Do not commit .env, output files, or real membership exports.
```

## Testing

Install development dependencies:

```bash
python -m pip install -r requirements-dev.txt
```

Run tests:

```bash
pytest
```
