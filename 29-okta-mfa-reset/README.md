# WARNING

These utilities have limited testing and are provided as-is with no warranty. Use at your own risk.

# 29-okta-mfa-reset

`okta-mfa-reset` resets MFA/factor/authenticator enrollments for approved users in Okta.

This is a mutating utility. It is intended for controlled help desk, migration, and security operations where selected users need MFA reset actions after review and approval.

## What this utility does

- Resets all enrolled factors for approved users.
- Deletes a selected enrolled factor by factor ID.
- Deletes a selected enrolled factor by factor type after discovering the user's enrolled factors.
- Optionally deletes a selected Identity Engine authenticator enrollment by enrollment ID.
- Supports one-user and bulk CSV workflows.
- Runs in dry-run mode by default.
- Requires `--apply` and a confirmation phrase before making changes.
- Requires `approved` and `reason` values by default.
- Blocks admin, break-glass, service-account, and other protected-looking users by default.
- Produces execution evidence, skipped rows, failed rows, changed rows, and rollback guidance.

## What this utility does not do

- It does not create users.
- It does not enroll new MFA factors.
- It does not reset passwords.
- It does not bypass Okta policy.
- It does not automatically roll back MFA resets. Users usually need to re-enroll factors after reset.

## Okta API behavior

The main supported actions are:

| Action | Okta API behavior |
|---|---|
| `reset_all_factors` | Calls the user lifecycle factor reset endpoint for the user. |
| `delete_factor` | Lists or deletes enrolled factors through the User Factors API. |
| `delete_authenticator_enrollment` | Deletes a specific Identity Engine authenticator enrollment by enrollment ID when enabled. |

Use `reset_all_factors` for the most common help desk MFA reset workflow.

Use `delete_factor` when you want to remove only one factor, such as SMS, call, token, or push.

Use `delete_authenticator_enrollment` only when you know your org supports the User Authenticator Enrollments API and you have the specific enrollment ID.

## Setup

Create a Python virtual environment.

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

Install the utility.

```bash
python -m pip install --upgrade pip
python -m pip install -e .
```

Create a local environment file.

macOS/Linux:

```bash
cp .env.example .env
```

Windows PowerShell:

```powershell
Copy-Item .env.example .env
```

Edit `.env` and populate the values.

```env
OKTA_ORG_URL=https://your-org.okta.com
OKTA_API_TOKEN=your-okta-api-token
```

Use the normal Okta org URL. Do not use the Admin Console URL.

Correct:

```text
https://example.okta.com
```

Incorrect:

```text
https://example-admin.okta.com
https://example.okta.com/admin
https://example.okta.com/api/v1
```

Copy the sample config.

macOS/Linux:

```bash
cp samples/mfa-reset.sample.json input/mfa-reset.config.json
```

Windows PowerShell:

```powershell
Copy-Item samples/mfa-reset.sample.json input/mfa-reset.config.json
```

Copy the sample CSV.

macOS/Linux:

```bash
cp samples/mfa-reset-users.sample.csv input/mfa-reset-users.csv
```

Windows PowerShell:

```powershell
Copy-Item samples/mfa-reset-users.sample.csv input/mfa-reset-users.csv
```

## Primary commands

Dry run:

```bash
okta-mfa-reset --config input/mfa-reset.config.json --dry-run
```

Apply approved reset actions:

```bash
okta-mfa-reset \
  --config input/mfa-reset.config.json \
  --apply \
  --confirm "RESET APPROVED MFA ENROLLMENTS"
```

Show help:

```bash
okta-mfa-reset --help
```

## Input CSV

Default input file:

```text
input/mfa-reset-users.csv
```

Default columns:

```csv
userId,login,email,action,factorId,factorType,provider,authenticatorEnrollmentId,approved,reason
```

Example reset-all row:

```csv
userId,login,email,action,factorId,factorType,provider,authenticatorEnrollmentId,approved,reason
00u123abc,user1@example.com,user1@example.com,reset_all_factors,,,,,true,Approved help desk MFA reset ticket HD-12345
```

Example selected factor row by factor ID:

```csv
userId,login,email,action,factorId,factorType,provider,authenticatorEnrollmentId,approved,reason
00u123abc,user1@example.com,user1@example.com,delete_factor,ufs123factor,,,,true,Approved removal of old SMS factor
```

Example selected factor row by factor type:

```csv
userId,login,email,action,factorId,factorType,provider,authenticatorEnrollmentId,approved,reason
00u123abc,user1@example.com,user1@example.com,delete_factor,,sms,OKTA,,true,Approved removal of SMS factor
```

Example Identity Engine authenticator enrollment row:

```csv
userId,login,email,action,factorId,factorType,provider,authenticatorEnrollmentId,approved,reason
00u123abc,user1@example.com,user1@example.com,delete_authenticator_enrollment,,,,enroll123,true,Approved authenticator enrollment reset
```

## Actions

| Action | Description |
|---|---|
| `reset_all_factors` | Resets all MFA factors for the user. |
| `delete_factor` | Deletes one enrolled factor by factor ID, or by factor type if the utility can discover a single match. |
| `delete_authenticator_enrollment` | Deletes one Identity Engine authenticator enrollment by enrollment ID. Disabled by default. |

## Config fields

Important settings:

```json
{
  "settings": {
    "defaultAction": "reset_all_factors",
    "requireApproved": true,
    "requireReason": true,
    "maxUsersPerRun": 25,
    "allowResetAllFactors": true,
    "allowDeleteSelectedFactors": true,
    "allowDeleteAuthenticatorEnrollments": false,
    "verifyUsersBeforeAction": true,
    "skipProtectedLogins": true,
    "continueOnError": false
  }
}
```

Recommended first test settings:

```json
{
  "settings": {
    "defaultAction": "reset_all_factors",
    "requireApproved": true,
    "requireReason": true,
    "maxUsersPerRun": 1,
    "allowResetAllFactors": true,
    "allowDeleteSelectedFactors": false,
    "allowDeleteAuthenticatorEnrollments": false,
    "verifyUsersBeforeAction": true
  }
}
```

## Safety controls

This utility skips rows when:

- `approved` is blank or not one of the configured approved values.
- `reason` is blank and reasons are required.
- The user identifier is missing.
- The action is not allowed by config.
- The row targets a protected-looking login.
- More than `maxUsersPerRun` rows are approved for action.
- A selected factor action does not include enough factor information.
- A selected factor type matches multiple enrolled factors.

Protected-looking logins are blocked by default if they contain values like:

```text
admin
breakglass
break-glass
service
svc
root
superadmin
```

Review and adjust the config before using this in a production org.

## Output files

Each run creates a timestamped folder under `output/`.

Common files:

```text
mfa_reset_plan.json
mfa_reset_result.json
changed_mfa_resets.csv
skipped_mfa_resets.csv
failed_mfa_resets.csv
rollback_plan.json
execution_report.md
```

## Rollback guidance

MFA resets usually cannot be automatically rolled back because factor secrets, device bindings, and authenticator enrollments are intentionally removed or invalidated.

The generated `rollback_plan.json` provides operational guidance, such as:

```text
User must re-enroll MFA factors through normal Okta enrollment flow.
```

## Suggested workflow

1. Export or identify users requiring MFA reset.
2. Build `input/mfa-reset-users.csv`.
3. Set `approved=true` only for reviewed rows.
4. Add a clear `reason` for each row.
5. Run dry-run.
6. Review `mfa_reset_plan.json` and `execution_report.md`.
7. Run apply with the confirmation phrase.
8. Confirm users can re-enroll MFA as expected.

## Notes

Keep `.env` out of Git and shared ZIP files. The `.gitignore` file excludes `.env`, `.venv`, output files, caches, and local artifacts.
