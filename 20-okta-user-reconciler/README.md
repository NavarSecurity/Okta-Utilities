# WARNING

These utilities have limited testing and are provided as-is with no warranty. Use at your own risk.

# 20-okta-user-reconciler

`okta-user-reconciler` compares source and target Okta user exports and produces reconciliation evidence showing which users match, which users are missing, and which matched users have material profile differences.

This utility is intended for Okta tenant migration validation, post-import verification, cleanup planning, and audit evidence. It is local-only by default and does not call the Okta API.

## What This Utility Does

- Reads source and target user export files from CSV or JSON
- Matches users by login, email, or configured fallback fields
- Detects users present only in the source export
- Detects users present only in the target export
- Detects matched users with material profile differences
- Detects duplicate source or target user records by match key
- Produces CSV, JSON, Markdown, and execution evidence outputs
- Supports Utility 18-style user export files
- Supports simple manually created CSV user files

## What This Utility Does Not Do

- It does not create users
- It does not update users
- It does not deactivate users
- It does not assign users to groups or apps
- It does not call Okta by default
- It does not decide whether a difference is acceptable for production

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
okta-user-reconciler --help
```

## Prepare Input Files

Copy the example config:

```bash
cp config.example.json input/user-reconcile.config.json
```

Copy or create the source and target user files:

```text
input/source/users.csv
input/target/users.csv
```

Utility 18 produces a file named `users.csv`. Because you need two exports for reconciliation, keep the same Utility 18 filename and separate them by folder:

```text
Utility 18 source export users.csv  ->  input/source/users.csv
Utility 18 target export users.csv  ->  input/target/users.csv
```

A simple CSV can look like this. Sample files are included under `samples/source/users.csv` and `samples/target/users.csv`:

```csv
login,email,firstName,lastName,status,profile.department,profile.title
alex.test@example.com,alex.test@example.com,Alex,Test,ACTIVE,IT,Analyst
jordan.test@example.com,jordan.test@example.com,Jordan,Test,ACTIVE,Security,Engineer
```

For a migration validation workflow, the source file normally comes from the old Okta org and the target file comes from the new Okta org.

## Config Fields

The main config file is:

```text
input/user-reconcile.config.json
```

The file paths are user-controlled. If your Utility 18 output folders are still available, you can also point directly to those `users.csv` files instead of copying them into Utility 20.

Important fields:

```json
{
  "sourceUsersFile": "input/source/users.csv",
  "targetUsersFile": "input/target/users.csv",
  "matchRules": {
    "primaryMatchField": "login",
    "fallbackMatchFields": ["email", "profile.login", "profile.email"],
    "caseInsensitive": true,
    "trimWhitespace": true
  },
  "profileFieldsToCompare": [
    "login",
    "email",
    "firstName",
    "lastName",
    "status",
    "profile.department",
    "profile.title"
  ],
  "settings": {
    "ignoreBlankSourceValues": true,
    "ignoreBlankTargetValues": false,
    "detectDuplicates": true,
    "strictMode": false
  }
}
```

### `sourceUsersFile`

The user export from the source Okta org.

### `targetUsersFile`

The user export from the target Okta org.

### `primaryMatchField`

The main field used to decide whether a source user and target user are the same person.

Recommended default:

```json
"login"
```

### `fallbackMatchFields`

Additional fields used when the primary field is blank.

Recommended defaults:

```json
["email", "profile.login", "profile.email"]
```

### `profileFieldsToCompare`

The fields that count as material for reconciliation.

Good first-run fields:

```json
["login", "email", "firstName", "lastName", "status"]
```

Add more fields when validating profile migration quality:

```json
["profile.department", "profile.title", "profile.employeeNumber", "profile.costCenter"]
```

### `ignoreBlankSourceValues`

If true, a blank value in the source export does not create a material difference.

Recommended first-run value:

```json
true
```

### `strictMode`

If true, the utility returns a non-zero exit code when source-only users, target-only users, duplicates, or material differences are found.

Recommended first-run value:

```json
false
```

## Run a Dry Run

```bash
okta-user-reconciler --config input/user-reconcile.config.json --dry-run
```

Dry-run validates the config, reads the input files, builds the reconciliation plan, and writes output files. It does not call Okta or make changes.

## Run Reconciliation

```bash
okta-user-reconciler --config input/user-reconcile.config.json --reconcile
```

Because this utility is local-only, reconcile mode also does not modify Okta. It produces the full reconciliation result and evidence files.

## Output Files

Each run creates a timestamped folder under `output/`.

Common outputs:

```text
user_reconciliation_plan.json
user_reconciliation_result.json
matched_users.csv
source_only_users.csv
target_only_users.csv
material_differences.csv
duplicate_users.csv
reconciliation_summary.md
execution_report.md
```

### `matched_users.csv`

Users found in both source and target.

### `source_only_users.csv`

Users present in the source export but missing from the target export.

These may need to be imported, intentionally excluded, or reviewed.

### `target_only_users.csv`

Users present in the target export but missing from the source export.

These may be pre-existing test users, local admins, service accounts, or unexpected users.

### `material_differences.csv`

Matched users with meaningful differences in fields listed in `profileFieldsToCompare`.

Example:

```text
source profile.title = Engineer
target profile.title = Senior Engineer
```

This means the user exists in both places, but the profile did not reconcile exactly.

### `duplicate_users.csv`

Duplicate records found in either input file by the configured match key.

Duplicates should be reviewed before trusting migration results.

## Recommended Workflow

1. Export users from the source org with Utility 18.
2. Export users from the target org with Utility 18.
3. Copy the source export `users.csv` into `input/source/users.csv`.
4. Copy the target export `users.csv` into `input/target/users.csv`.
5. Confirm `sourceUsersFile` and `targetUsersFile` point to those paths.
6. Run dry-run.
7. Review source-only, target-only, duplicates, and material differences.
8. Adjust import, migration, or profile mapping as needed.
9. Rerun reconciliation after fixes.

## Exit Codes

```text
0 = completed successfully
1 = completed with errors or strict mode failed
2 = invalid config or missing input file
```

## Safety Notes

- This utility is local-only by default.
- It does not write to Okta.
- Review differences before treating them as migration defects.
- Do not store real user exports in Git.
- User exports may contain personal information and should be handled as sensitive data.
