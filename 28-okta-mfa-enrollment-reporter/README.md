# WARNING

These utilities have limited testing and are provided as-is with no warranty. Use at your own risk.

# 28-okta-mfa-enrollment-reporter

`okta-mfa-enrollment-reporter` is a read-only Okta reporting utility that identifies which users are enrolled in MFA/authenticator factors. It can report enrollment status by user, group, and factor type.

This utility does not create, update, reset, enroll, or remove MFA factors. It only reads Okta data and writes reports.

## What this utility does

- Reads users from Okta by user, group, or full-org user listing.
- Reads each user's enrolled factors from Okta.
- Reports whether each user has any enrolled factor.
- Reports factor type, provider, status, and enrollment metadata.
- Reports users missing required factor types.
- Produces user-level, factor-level, group-level, and summary outputs.
- Supports dry-run mode before API reporting.
- Redacts phone numbers and other sensitive-looking factor profile values by default.

## Typical use cases

- MFA readiness review.
- Pre-migration MFA enrollment baseline.
- Group-by-group authenticator coverage analysis.
- Identifying users with no enrolled MFA factor.
- Identifying users missing a required authenticator type.
- Producing evidence for IAM assessment or audit work.

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

Create your `.env` file from the example file.

macOS/Linux:

```bash
cp .env.example .env
```

Windows PowerShell:

```powershell
Copy-Item .env.example .env
```

Edit `.env` and populate the values:

```env
OKTA_ORG_URL=https://your-org.okta.com
OKTA_API_TOKEN=your-okta-api-token
```

Use the normal Okta org URL. Do not use the Admin Console URL.

Correct:

```text
https://example.okta.com
https://dev-123456.okta.com
```

Incorrect:

```text
https://example-admin.okta.com
https://example.okta.com/admin
https://example.okta.com/api/v1
```

## Configuration

Copy the sample config into the input folder.

macOS/Linux:

```bash
cp samples/mfa-enrollment-report.sample.json input/mfa-enrollment-report.config.json
```

Windows PowerShell:

```powershell
Copy-Item samples/mfa-enrollment-report.sample.json input/mfa-enrollment-report.config.json
```

Edit:

```text
input/mfa-enrollment-report.config.json
```

Example config:

```json
{
  "orgUrl": "https://your-org.okta.com",
  "input": {
    "userIds": [],
    "userLogins": [],
    "groupIds": [],
    "groupNames": [],
    "statuses": ["ACTIVE"],
    "includeUsersWithoutFactors": true
  },
  "reporting": {
    "requiredFactorTypes": ["push", "token:software:totp", "sms", "webauthn"],
    "factorTypes": [],
    "includeFactorProfile": false,
    "includeRawFactors": false
  },
  "settings": {
    "pageLimit": 200,
    "requestTimeoutSeconds": 30,
    "maxRetries": 3,
    "redactSensitiveProfileValues": true
  }
}
```

## Config field explanations

### `orgUrl`

The base URL of the Okta org. If `OKTA_ORG_URL` exists in `.env`, the `.env` value takes priority.

### `input.userIds`

Optional list of exact Okta user IDs to report on.

```json
"userIds": ["00uabc123example"]
```

### `input.userLogins`

Optional list of exact Okta user logins or emails to report on.

```json
"userLogins": ["jane.doe@example.com"]
```

### `input.groupIds`

Optional list of Okta group IDs. The utility will report MFA enrollment for users in these groups.

```json
"groupIds": ["00gabc123example"]
```

### `input.groupNames`

Optional list of exact Okta group names. The utility resolves these names to group IDs before collecting group users.

```json
"groupNames": ["Example App Users"]
```

Using `groupIds` is safer than `groupNames` because group IDs are unique.

### `input.statuses`

Optional list of Okta user statuses to include.

```json
"statuses": ["ACTIVE", "STAGED"]
```

Common statuses include:

```text
STAGED
PROVISIONED
ACTIVE
RECOVERY
PASSWORD_EXPIRED
LOCKED_OUT
SUSPENDED
DEPROVISIONED
```

### `reporting.requiredFactorTypes`

A list of factor types the report should check for. Missing values appear in `missing_required_factor_types`.

Examples:

```json
"requiredFactorTypes": ["push", "webauthn"]
```

### `reporting.factorTypes`

Optional filter. If populated, only matching factor types are included in the detailed factor report.

Leave it blank to include all returned factor types.

```json
"factorTypes": []
```

### `reporting.includeFactorProfile`

If true, the factor detail CSV includes a JSON summary of the factor profile. Sensitive-looking values are redacted when redaction is enabled.

### `reporting.includeRawFactors`

If true, the utility writes a `raw_factors_redacted.json` output file. Raw output is redacted when redaction is enabled.

### `settings.redactSensitiveProfileValues`

If true, the utility redacts phone numbers, passcodes, secrets, tokens, and other sensitive-looking values from reports.

Keep this enabled unless you have a controlled reason not to.

## Dry run

Run dry-run first:

```bash
okta-mfa-enrollment-reporter --config input/mfa-enrollment-report.config.json --dry-run
```

Dry-run validates configuration and writes a plan. It does not call Okta.

Review the output folder:

```text
output/okta-mfa-enrollment-reporter-<timestamp>/
```

Important dry-run output:

```text
mfa_enrollment_plan.json
execution_report.md
```

## Report mode

Run the report:

```bash
okta-mfa-enrollment-reporter --config input/mfa-enrollment-report.config.json --report
```

`--export` is also supported as a read-only alias:

```bash
okta-mfa-enrollment-reporter --config input/mfa-enrollment-report.config.json --export
```

## Output files

The utility writes a timestamped output folder under `output/`.

Typical outputs:

```text
mfa_enrollment_plan.json
mfa_enrollment_result.json
user_mfa_summary.csv
factor_enrollments.csv
users_without_mfa.csv
missing_required_factors.csv
group_mfa_summary.csv
factor_type_summary.csv
execution_report.md
```

Optional output:

```text
raw_factors_redacted.json
```

## Important outputs explained

### `user_mfa_summary.csv`

One row per user.

Includes:

```text
user_id
login
email
status
group_names
factor_count
active_factor_count
factor_types
active_factor_types
has_any_factor
has_active_factor
missing_required_factor_types
factor_fetch_status
```

### `factor_enrollments.csv`

One row per factor enrollment.

Includes:

```text
user_id
login
email
factor_id
factor_type
provider
status
created
last_updated
```

### `users_without_mfa.csv`

Users with no enrolled factors, or no active enrolled factors depending on the returned Okta factor status.

### `missing_required_factors.csv`

Users who are missing one or more factor types listed under `reporting.requiredFactorTypes`.

### `group_mfa_summary.csv`

One row per group included in the report.

Includes counts such as:

```text
total_users
users_with_any_factor
users_with_active_factor
users_without_factor
coverage_percent
```

## How to report on one group

Use either `groupIds`:

```json
"input": {
  "groupIds": ["00gabc123example"],
  "groupNames": [],
  "userIds": [],
  "userLogins": [],
  "statuses": ["ACTIVE"]
}
```

or `groupNames`:

```json
"input": {
  "groupIds": [],
  "groupNames": ["Example App Users"],
  "userIds": [],
  "userLogins": [],
  "statuses": ["ACTIVE"]
}
```

Then run:

```bash
okta-mfa-enrollment-reporter --config input/mfa-enrollment-report.config.json --report
```

## How to report on specific users

Use `userLogins`:

```json
"input": {
  "userLogins": [
    "user1@example.com",
    "user2@example.com"
  ],
  "userIds": [],
  "groupIds": [],
  "groupNames": [],
  "statuses": ["ACTIVE"]
}
```

Then run:

```bash
okta-mfa-enrollment-reporter --config input/mfa-enrollment-report.config.json --report
```

## How to report on all active users

Leave user and group filters blank, and set statuses to `ACTIVE`:

```json
"input": {
  "userIds": [],
  "userLogins": [],
  "groupIds": [],
  "groupNames": [],
  "statuses": ["ACTIVE"]
}
```

Then run:

```bash
okta-mfa-enrollment-reporter --config input/mfa-enrollment-report.config.json --report
```

## Notes and limitations

- This utility is read-only.
- It does not reset MFA.
- It does not enroll users in MFA.
- It does not change authenticator policies.
- It reports factor enrollment data returned by the Okta Users Factors API.
- Okta Identity Engine authenticator naming may differ from classic factor naming in some orgs.
- Some factor details may require additional Okta permissions.
- Use a least-privilege read/reporting API token where possible.

## Troubleshooting

### `Invalid Okta org URL`

Use the normal Okta org URL, not the admin URL.

Correct:

```text
https://your-org.okta.com
```

Incorrect:

```text
https://your-org-admin.okta.com
```

### `401 Unauthorized`

Check:

```text
OKTA_API_TOKEN is correct
The token belongs to the same org as OKTA_ORG_URL
The token was not revoked
The token has enough permissions to read users and factors
```

### Group name not found

Use `groupIds` instead of `groupNames`, or confirm the group name exactly matches the Okta group profile name.

### No users found

Check the configured filters:

```text
userIds
userLogins
groupIds
groupNames
statuses
```

A status filter of `ACTIVE` excludes `STAGED`, `SUSPENDED`, and `DEPROVISIONED` users.
