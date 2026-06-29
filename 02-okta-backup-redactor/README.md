# 02-okta-backup-redactor

`okta-backup-redactor` scans an Okta configuration backup folder for sensitive values and creates a separate redacted copy that is safer to review, share internally, or commit to Git.

This utility is designed to be used after `01-okta-config-backup` and before sharing or storing backup artifacts.

## What this utility does

The redactor reads a local backup folder and detects sensitive values such as:

- API tokens
- SSWS tokens
- Bearer tokens
- Basic authorization values
- Client secrets
- Shared secrets
- Private keys
- Authorization headers
- Password-like secret values

It then creates a redacted copy of the backup using a placeholder such as:

```text
[REDACTED]
```

## What this utility does not do

This utility does **not** connect to Okta.

It does **not** require an Okta API token.

It does **not** modify the original backup folder.

It does **not** guarantee that every possible sensitive value has been removed. Always review the redacted output before sharing or committing it.

## Recommended workflow

The normal workflow is:

```text
1. Run 01-okta-config-backup to create a raw backup.
2. Run 02-okta-backup-redactor against that backup.
3. Review the redaction report.
4. Apply redaction to create a separate redacted backup copy.
5. Run 05-okta-backup-validator against the redacted backup.
6. Only share or commit the redacted backup after review.
```

## Folder structure

Expected project structure:

```text
02-okta-backup-redactor/
  README.md
  SECURITY.md
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

The `input/source-backup/` folder is provided as a convenience location for backup files. You can either copy a backup into that folder or point the utility directly to an external backup folder using `--source-backup-dir`.

## Prerequisites

You need:

```text
Python 3.10+
A local backup folder created by 01-okta-config-backup
```

You do **not** need:

```text
Okta admin access
Okta API token
Network access to Okta
```

## Installation

From inside the `02-okta-backup-redactor` folder, create a virtual environment.

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
okta-backup-redactor --help
```

You should see options such as:

```text
--config
--source-backup-dir
--output-dir
--include-files
--exclude-files
--dry-run
--apply
--print-json
--version
```

## Prepare a backup folder

This utility expects a backup folder created by `01-okta-config-backup`.

Example backup folder:

```text
../01-okta-config-backup/output/okta-config-backup-20260626T164507Z/
```

That folder may contain files such as:

```text
manifest.json
execution_report.md
applications.json
groups.json
policies.json
domains.json
authorization_servers.json
```

You can provide this backup folder in either of two ways.

## Option A: Copy the backup into `input/source-backup/`

Copy the contents of your backup folder into:

```text
02-okta-backup-redactor/input/source-backup/
```

Expected result:

```text
input/source-backup/
  manifest.json
  applications.json
  groups.json
  policies.json
  domains.json
  authorization_servers.json
```

The default config uses this source folder:

```json
"sourceBackupDir": "input/source-backup"
```

## Option B: Point directly to an external backup folder

Instead of copying the backup, you can point directly to the folder:

```bash
okta-backup-redactor \
  --source-backup-dir ../01-okta-config-backup/output/okta-config-backup-20260626T164507Z \
  --dry-run
```

This is often cleaner because it avoids copying backup files into the redactor utility folder.

## Create a working config file

Do not edit `config.example.json` directly. Copy it first.

### macOS / Linux

```bash
cp config.example.json input/redactor.config.json
```

### Windows PowerShell

```powershell
Copy-Item config.example.json input/redactor.config.json
```

Open:

```text
input/redactor.config.json
```

Example config:

```json
{
  "sourceBackupDir": "input/source-backup",
  "outputDir": "output",
  "includeFiles": [],
  "excludeFiles": [],
  "redactionPlaceholder": "[REDACTED]",
  "maxValuePreviewChars": 120,
  "writeReports": true,
  "failOnSensitiveFindings": false
}
```

### Config field explanations

| Field | Purpose |
|---|---|
| `sourceBackupDir` | Backup folder to scan and redact. |
| `outputDir` | Folder where redaction results are written. |
| `includeFiles` | Optional list of specific JSON files to scan. Empty means include all JSON files. |
| `excludeFiles` | Optional list of files to skip. |
| `redactionPlaceholder` | Replacement value written in place of detected sensitive values. |
| `maxValuePreviewChars` | Limits value previews shown in reports. |
| `writeReports` | Writes Markdown and JSON reports. |
| `failOnSensitiveFindings` | Returns a failure exit code if sensitive values are found. Useful in CI/CD. |

## Run a dry run first

Always run dry-run before apply mode:

```bash
okta-backup-redactor --config input/redactor.config.json --dry-run
```

Dry-run mode:

```text
Scans the backup folder
Builds a redaction plan
Writes a redaction report
Does not create a redacted backup copy
Does not modify the source backup
```

Expected output folder:

```text
output/okta-backup-redaction-YYYYMMDDTHHMMSSZ/
```

Review:

```text
redaction_report.md
redaction_result.json
```

## Review the dry-run report

Open:

```text
output/okta-backup-redaction-*/redaction_report.md
```

The report shows:

```text
Files scanned
Findings detected
JSON paths where sensitive values were found
Value previews
Whether apply mode was used
```

Use this report to confirm that the utility is detecting the right values before creating a redacted copy.

## Apply redaction

After the dry-run report looks correct, run:

```bash
okta-backup-redactor --config input/redactor.config.json --apply
```

Apply mode creates a separate redacted backup copy here:

```text
output/okta-backup-redaction-YYYYMMDDTHHMMSSZ/redacted-backup/
```

The original source backup remains unchanged.

## Run directly without a config file

You can run the utility directly with a source backup folder:

```bash
okta-backup-redactor \
  --source-backup-dir ../01-okta-config-backup/output/okta-config-backup-20260626T164507Z \
  --dry-run
```

Then apply:

```bash
okta-backup-redactor \
  --source-backup-dir ../01-okta-config-backup/output/okta-config-backup-20260626T164507Z \
  --apply
```

## Redact only selected files

To scan only specific files:

```bash
okta-backup-redactor \
  --source-backup-dir ../01-okta-config-backup/output/okta-config-backup-20260626T164507Z \
  --include-files applications.json,policies.json \
  --dry-run
```

Apply:

```bash
okta-backup-redactor \
  --source-backup-dir ../01-okta-config-backup/output/okta-config-backup-20260626T164507Z \
  --include-files applications.json,policies.json \
  --apply
```

## Exclude selected files

To scan everything except certain files:

```bash
okta-backup-redactor \
  --source-backup-dir ../01-okta-config-backup/output/okta-config-backup-20260626T164507Z \
  --exclude-files execution_report.md,manifest.json \
  --dry-run
```

This is useful if you want to focus only on exported resource files and skip evidence/report files.

## Important behavior

### The source backup is never modified

If your source backup is:

```text
../01-okta-config-backup/output/okta-config-backup-20260626T164507Z/
```

that folder stays unchanged.

The redacted copy is written separately:

```text
output/okta-backup-redaction-*/redacted-backup/
```

### Normal Okta structures are preserved

The redactor should not break normal Okta configuration structures such as:

```text
policyTypes.PASSWORD
authorizationServers
detailsByAuthorizationServerId
passwordChange
selfServicePasswordReset
```

These names may look sensitive, but they are normal Okta object and policy structures.

### Actual sensitive values are redacted

Example:

```json
"client_secret": "abc123secret"
```

becomes:

```json
"client_secret": "[REDACTED]"
```

Example:

```json
"Authorization": "SSWS 00abc123"
```

becomes:

```json
"Authorization": "[REDACTED]"
```

## Validate the redacted backup

After creating the redacted copy, validate it with `05-okta-backup-validator`.

Example:

```bash
cd ../05-okta-backup-validator

okta-backup-validator \
  --backup-dir ../02-okta-backup-redactor/output/<redaction-output-folder>/redacted-backup \
  --strict
```

The validator helps confirm that:

```text
JSON files are still valid
Object counts still match
Required fields still exist
Sensitive values are not exposed
```

## Recommended end-to-end workflow

```bash
# 1. Back up the Okta org.
cd 01-okta-config-backup
okta-config-backup --config input/config.json

# 2. Redact the backup.
cd ../02-okta-backup-redactor
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .

okta-backup-redactor \
  --source-backup-dir ../01-okta-config-backup/output/<backup-folder> \
  --dry-run

# Review redaction_report.md.

okta-backup-redactor \
  --source-backup-dir ../01-okta-config-backup/output/<backup-folder> \
  --apply

# 3. Validate the redacted backup.
cd ../05-okta-backup-validator

okta-backup-validator \
  --backup-dir ../02-okta-backup-redactor/output/<redaction-output-folder>/redacted-backup \
  --strict
```

## Output files

Each run creates a timestamped output folder:

```text
output/okta-backup-redaction-YYYYMMDDTHHMMSSZ/
```

Dry-run output:

```text
redaction_report.md
redaction_result.json
```

Apply output:

```text
redacted-backup/
redaction_report.md
redaction_result.json
```

## Exit codes

| Exit code | Meaning |
|---:|---|
| `0` | Redaction completed successfully. |
| `1` | Sensitive findings were detected and `failOnSensitiveFindings` or equivalent failure behavior was enabled. |
| `2` | Runtime or configuration error. |

## What to commit or share

Do **not** commit or share:

```text
Original raw backup folder
.env files
API tokens
Unreviewed reports that include sensitive value previews
```

Safer artifacts to review after validation:

```text
redacted-backup/
redaction_report.md
redaction_result.json
validation_report.md
```

Even after redaction, treat backup files as sensitive configuration data.

## Troubleshooting

### `Source backup directory not found`

The configured `sourceBackupDir` does not exist.

Fix the path in:

```text
input/redactor.config.json
```

or pass the source folder directly:

```bash
okta-backup-redactor --source-backup-dir ../01-okta-config-backup/output/<backup-folder> --dry-run
```

### No findings were detected

This can mean either:

```text
The backup is already clean
The utility did not scan the intended folder
The sensitive value is stored under a key the utility does not currently detect
```

Confirm that the command points to the correct backup folder.

### Redacted backup was not created

Apply mode is required to create the redacted copy:

```bash
okta-backup-redactor --config input/redactor.config.json --apply
```

Dry-run only creates reports.

### A normal Okta key was redacted

If a structural key or harmless value is being redacted, update the safe-key allowlist or redaction matching logic. Normal object names like `authorizationServers`, `policyTypes.PASSWORD`, `passwordChange`, and `selfServicePasswordReset` should be preserved.

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

## Disclaimer

These utilities have limited testing and are provided as-is with no warranty. Use at your own risk, review all code and output carefully, and test in a non-production environment before using on sensitive, client-owned, or production systems.
