# 05-okta-backup-validator

`okta-backup-validator` validates local backup folders produced by `01-okta-config-backup` before those backups are used for restore, migration, Terraform import planning, diffing, audit evidence, or client handoff.

It does **not** connect to Okta and does **not** create, update, delete, assign, deactivate, or restore anything. It only reads local JSON backup files and produces validation evidence.

## Purpose

Use this utility to answer:

> Can we trust this Okta backup before we use it for migration, restore, comparison, or audit evidence?

The validator checks:

- `manifest.json` presence and JSON validity
- Backup folder readability
- Manifest required fields
- Backup ID and timestamp format
- Org URL sanity checks, including placeholder detection
- Redaction status
- Recorded backup errors in the manifest
- Expected resource files
- Listed file existence
- JSON validity of exported files
- Manifest count consistency
- Required object fields for common Okta resources
- Potential unredacted sensitive values using exact sensitive key matching

## Supported backup files

The utility is designed for backup folders with files such as:

```text
manifest.json
org.json
applications.json
groups.json
group_rules.json
policies.json
identity_providers.json
authorization_servers.json
event_hooks.json
inline_hooks.json
network_zones.json
trusted_origins.json
brands.json
domains.json
authenticators.json
```

It also tolerates partial backups when the manifest records resource-level errors, unless strict mode is enabled.

### Domains response shape support

The validator normalizes Okta Domains API wrapper responses before count and required-field checks. It supports flat domain arrays, a top-level `{"domains": [...]}` object, and wrapped arrays such as `[{"domains": [...]}]`. This prevents false `RESOURCE_REQUIRED_FIELDS_MISSING` findings when `domains.json` contains valid domain records inside an Okta response wrapper.

### Sensitive value scan behavior

The validator uses exact/canonical key matching for likely secret fields instead of broad substring matching. This prevents false positives for normal Okta configuration keys such as `authorizationServers`, `detailsByAuthorizationServerId`, `passwordChange`, and `selfServicePasswordReset`.

When `SENSITIVE_VALUES_FOUND` is raised, the detailed JSON result and Markdown report include the exact detected value that should be redacted. Treat validation reports as sensitive when this finding appears.

## Install

From inside the `05-okta-backup-validator` folder:

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

Confirm the command is available:

```bash
okta-backup-validator --help
```

## Configuration

Copy the example config:

```bash
cp config.example.json input/validator.config.json
```

Windows PowerShell:

```powershell
Copy-Item config.example.json input/validator.config.json
```

Edit `input/validator.config.json`:

```json
{
  "backupDir": "../01-okta-config-backup/output/okta-config-backup-20260625T162843Z",
  "outputDir": "output",
  "expectedResources": [],
  "requiredResources": [
    "manifest"
  ],
  "allowMissingFilesForErroredResources": true,
  "requireNoResourceErrors": false,
  "requireRedactionEnabled": true,
  "strictMode": false,
  "failOnWarnings": false,
  "sensitiveScanEnabled": true,
  "maxSensitiveFindings": 50
}
```

### Important config fields

| Field | Meaning |
|---|---|
| `backupDir` | Local backup folder to validate. |
| `outputDir` | Where validation reports are written. |
| `expectedResources` | Optional resource list to validate. Empty means use `manifest.requestedResources`. |
| `requiredResources` | Resource files that must exist. Use `manifest` to require `manifest.json`. |
| `allowMissingFilesForErroredResources` | If true, missing files are warnings when the manifest already records an error for that resource. |
| `requireNoResourceErrors` | If true, any `manifest.errors` entry fails validation. |
| `requireRedactionEnabled` | If true, `redactionEnabled` must be true in the manifest. |
| `strictMode` | Enables stricter validation. Equivalent to failing on backup errors, missing errored files, and warnings. |
| `failOnWarnings` | Returns a failing exit code when warnings exist. |
| `sensitiveScanEnabled` | Scans exported JSON for common unredacted secret field names using exact sensitive key matching. |

## Run the validator

```bash
okta-backup-validator --config input/validator.config.json
```

Or pass the backup directory directly:

```bash
okta-backup-validator \
  --backup-dir ../01-okta-config-backup/output/okta-config-backup-20260625T162843Z
```

Run in strict mode:

```bash
okta-backup-validator \
  --backup-dir ../01-okta-config-backup/output/okta-config-backup-20260625T162843Z \
  --strict
```

Print the validation result JSON to the terminal:

```bash
okta-backup-validator --config input/validator.config.json --print-json
```

## Output files

Each run creates a timestamped folder:

```text
output/okta-backup-validation-YYYYMMDDTHHMMSSZ/
  validation_result.json
  validation_report.md
```

### `validation_result.json`

Machine-readable validation result with all checks, severity levels, summary counts, and overall status.

### `validation_report.md`

Human-readable validation report for review, delivery evidence, or project handoff.

## Overall status

| Status | Meaning |
|---|---|
| `PASS` | Backup passed required validation checks. |
| `WARN` | Backup is readable but has issues requiring review, such as partial backup errors. |
| `FAIL` | Backup should not be used for migration, restore, or evidence until failures are fixed. |

## Exit codes

| Exit code | Meaning |
|---:|---|
| `0` | Validation completed with `PASS` or `WARN`, unless `failOnWarnings` is enabled. |
| `1` | Validation completed with `FAIL`, or warnings are treated as failures. |
| `2` | Runtime/configuration failure, such as missing config or invalid config JSON. |

## Recommended workflow

```text
1. Run 01-okta-config-backup.
2. Run 05-okta-backup-validator against the backup folder.
3. Review validation_report.md.
4. Only use the backup for restore, migration, diff, Terraform import, or evidence if the result is acceptable.
```

For client work, use strict mode before restore or migration:

```bash
okta-backup-validator --backup-dir <backup-folder> --strict
```

## Examples

Validate the included good sample:

```bash
okta-backup-validator --backup-dir samples/sample-backup-good
```

Validate the included bad sample:

```bash
okta-backup-validator --backup-dir samples/sample-backup-bad
```

The bad sample intentionally includes a placeholder org URL, a manifest count mismatch, a recorded API error, and an unredacted `client_secret` value. Sensitive findings include the exact value in `validation_result.json` and `validation_report.md` so operators know exactly what to redact.

## Testing

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
