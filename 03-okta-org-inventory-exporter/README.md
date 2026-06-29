# 03-okta-org-inventory-exporter

`okta-org-inventory-exporter` builds readable inventory reports from an Okta configuration backup folder.

This utility is intended for discovery, baseline review, migration planning, audit support, and handoff documentation. It is read-only and local-only: it does **not** call Okta APIs and does **not** change an Okta org.

## What this utility does

The exporter reads backup files created by `01-okta-config-backup` and generates inventory artifacts such as:

- High-level inventory summary
- Markdown inventory report
- CSV files by resource type
- Machine-readable inventory JSON
- Warnings for missing, malformed, or unsupported backup sections

Supported resource types include:

- `org`
- `applications`
- `groups`
- `group_rules`
- `policies`
- `identity_providers`
- `authorization_servers`
- `trusted_origins`
- `network_zones`
- `domains`
- `brands`
- `authenticators`
- `event_hooks`
- `inline_hooks`

## What this utility does not do

This utility does **not**:

- Connect to Okta
- Require an API token
- Modify backup files
- Create, update, delete, restore, or assign Okta objects
- Replace manual security or migration review

## Folder structure

```text
03-okta-org-inventory-exporter/
  README.md
  SECURITY.md
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
A local backup folder from 01-okta-config-backup
```

You do not need:

```text
Okta admin access
Okta API token
Network access to Okta
```

## Installation

From inside `03-okta-org-inventory-exporter`, create and activate a virtual environment.

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
okta-org-inventory-exporter --help
```

## Test with included sample data

Run:

```bash
okta-org-inventory-exporter --config config.example.json
```

This reads:

```text
samples/sample-backup/
```

and writes output under:

```text
output/okta-org-inventory-YYYYMMDDTHHMMSSZ/
```

## Run against a real backup folder

Use a backup folder created by `01-okta-config-backup`.

```bash
okta-org-inventory-exporter \
  --backup-dir ../01-okta-config-backup/output/okta-config-backup-20260626T164507Z
```

## Analyze selected resources only

```bash
okta-org-inventory-exporter \
  --backup-dir ../01-okta-config-backup/output/okta-config-backup-20260626T164507Z \
  --include applications,groups,policies
```

## Use a config file

Copy the example config:

```bash
cp config.example.json input/inventory.config.json
```

Windows PowerShell:

```powershell
Copy-Item config.example.json input/inventory.config.json
```

Edit `input/inventory.config.json`:

```json
{
  "backupDir": "../01-okta-config-backup/output/okta-config-backup-20260626T164507Z",
  "outputDir": "output",
  "include": ["applications", "groups", "policies"],
  "writeCsv": true,
  "writeJson": true,
  "writeMarkdown": true,
  "strictMode": false,
  "failOnManifestErrors": false,
  "maxPreviewChars": 250
}
```

Run:

```bash
okta-org-inventory-exporter --config input/inventory.config.json
```

## Config field explanations

| Field | Purpose |
|---|---|
| `backupDir` | Backup folder to inventory. |
| `outputDir` | Where inventory output is written. |
| `include` | Resource types to include. |
| `writeCsv` | Writes per-resource CSV files. |
| `writeJson` | Writes `inventory.json`. |
| `writeMarkdown` | Writes `inventory_report.md`. |
| `strictMode` | Treats warnings as blocking and returns exit code `1`. |
| `failOnManifestErrors` | Returns exit code `1` if the source backup manifest contains API errors. |
| `maxPreviewChars` | Limits long preview values in generated reports. |

## Outputs

Each run creates a timestamped folder:

```text
output/okta-org-inventory-YYYYMMDDTHHMMSSZ/
```

Typical output:

```text
inventory.json
inventory_report.md
execution_report.md
csv/
  applications.csv
  groups.csv
  policies.csv
  authorization_servers.csv
  identity_providers.csv
  trusted_origins.csv
  network_zones.csv
  domains.csv
```

### `inventory_report.md`

Human-readable summary for discovery, baseline review, or audit handoff.

### `inventory.json`

Machine-readable normalized inventory with resource counts, warnings, source backup metadata, and records.

### `csv/`

Per-resource CSV files that can be opened in Excel, imported into a worksheet, or used by downstream planning utilities.

## Recommended workflow

```bash
# 1. Create a backup.
cd 01-okta-config-backup
okta-config-backup --config input/config.json

# 2. Validate the backup.
cd ../05-okta-backup-validator
okta-backup-validator --backup-dir ../01-okta-config-backup/output/<backup-folder> --strict

# 3. Export inventory.
cd ../03-okta-org-inventory-exporter
okta-org-inventory-exporter --backup-dir ../01-okta-config-backup/output/<backup-folder>
```

## Exit codes

| Exit code | Meaning |
|---:|---|
| `0` | Inventory completed successfully. |
| `1` | Inventory completed with blocking warnings or strict-mode failure. |
| `2` | Runtime or configuration failure. |

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

WARNING: These utilities have limited testing and are provided as-is with no warranty. Use at your own risk.
