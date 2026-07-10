# WARNING

These utilities have limited testing and are provided as-is with no warranty. Use at your own risk.

# okta-network-zone-manager

Python utility for exporting, comparing, importing, and managing Okta Network Zones.

This utility is intended for Okta administration, migration support, security baseline reviews, and policy dependency analysis. It can be used to safely review network zone configuration before making changes to an Okta org.

---

## What This Utility Does

The `okta-network-zone-manager` utility supports four main operations:

| Operation | Purpose |
|---|---|
| `export` | Export Okta Network Zones from an org. |
| `compare` | Compare two exported network zone files offline. |
| `import` | Create or replace network zones from an approved input file. |
| `manage` | Activate, deactivate, delete, create, or replace selected zones. |

Network zones are often used in Okta sign-on policies, app sign-on policies, threat rules, and access control decisions. This utility helps capture and compare those settings before or after changes.

---

## Safety Model

This utility is designed to be conservative.

Mutation operations require explicit apply mode.

Read-only operations:

```bash
okta-network-zone-manager --config config.json --operation export
okta-network-zone-manager --config config.json --operation compare
```

Mutation preview:

```bash
okta-network-zone-manager --config config.json --operation import --dry-run
okta-network-zone-manager --config config.json --operation manage --dry-run
```

Mutation apply:

```bash
okta-network-zone-manager --config config.json --operation import --apply
okta-network-zone-manager --config config.json --operation manage --apply
```

The utility should not create, replace, activate, deactivate, or delete zones unless `--apply` is provided.

---

## Folder Structure

```text
32-okta-network-zone-manager/
  README.md
  pyproject.toml
  .env.example
  .gitignore
  config.example.json
  src/
    okta_network_zone_manager/
      __init__.py
      __main__.py
      cli.py
      config.py
      okta_client.py
      normalize.py
      diff.py
      operations.py
      reports.py
  samples/
    config.export.sample.json
    config.compare.sample.json
    config.import.sample.json
    config.manage.sample.json
    zones.import.sample.json
    actions.sample.json
    source-network_zones_full.json
    target-network_zones_full.json
  tests/
    test_normalize.py
    test_diff.py
    test_okta_client.py
  input/
  output/
```

---

## Requirements

- Python 3.10 or newer
- Okta admin API token
- Okta org URL
- Network access to the Okta tenant

The Okta API token should be generated from an account with permissions to read or manage network zones, depending on the operation being performed.

---

## Setup

Run these commands from the utility folder.

Create a virtual environment:

```bash
python3 -m venv .venv
```

Activate the virtual environment on macOS or Linux:

```bash
source .venv/bin/activate
```

Activate the virtual environment on Windows PowerShell:

```powershell
.venv\Scripts\Activate.ps1
```

Install the utility:

```bash
python -m pip install -e .
```

Copy the environment example:

```bash
cp .env.example .env
```

Copy a sample configuration file:

```bash
cp samples/config.export.sample.json config.json
```

Open `.env` and update the Okta values.

---

## Environment Variables

Create a `.env` file using `.env.example`.

Example:

```env
OKTA_ORG_URL=https://your-org.okta.com
OKTA_API_TOKEN=replace-with-okta-api-token
```

Do not commit `.env` files.

The `.gitignore` file should exclude:

```text
.env
output/
*.log
```

---

## Configuration

The utility is driven by `config.json`.

Example export configuration:

```json
{
  "outputDir": "output",
  "operation": "export",
  "okta": {
    "orgUrlEnv": "OKTA_ORG_URL",
    "apiTokenEnv": "OKTA_API_TOKEN"
  },
  "export": {
    "includeSystemZones": true,
    "limit": 200
  }
}
```

Example compare configuration:

```json
{
  "outputDir": "output",
  "operation": "compare",
  "compare": {
    "sourceFile": "samples/source-network_zones_full.json",
    "targetFile": "samples/target-network_zones_full.json",
    "matchBy": "name"
  }
}
```

Example import configuration:

```json
{
  "outputDir": "output",
  "operation": "import",
  "okta": {
    "orgUrlEnv": "OKTA_ORG_URL",
    "apiTokenEnv": "OKTA_API_TOKEN"
  },
  "import": {
    "inputFile": "samples/zones.import.sample.json",
    "matchBy": "name",
    "replaceExisting": false,
    "activateCreatedZones": false,
    "protectSystemZones": true,
    "protectedNames": [
      "LegacyIpZone",
      "BlockedIpZone",
      "DefaultEnhancedDynamicZone",
      "DefaultExemptIpZone"
    ]
  }
}
```

Example manage configuration:

```json
{
  "outputDir": "output",
  "operation": "manage",
  "okta": {
    "orgUrlEnv": "OKTA_ORG_URL",
    "apiTokenEnv": "OKTA_API_TOKEN"
  },
  "manage": {
    "actionsFile": "samples/actions.sample.json",
    "allowDelete": false,
    "allowDeleteActiveZones": false,
    "protectSystemZones": true,
    "protectedNames": [
      "LegacyIpZone",
      "BlockedIpZone",
      "DefaultEnhancedDynamicZone",
      "DefaultExemptIpZone"
    ]
  }
}
```

---

## Operation: Export Network Zones

Use export mode to capture the current Okta Network Zone configuration.

```bash
okta-network-zone-manager --config config.json --operation export
```

Expected output:

```text
output/network-zone-export-<timestamp>/
  network_zones_full.json
  network_zones_summary.csv
  execution_report.json
  manifest.json
```

Use this before policy changes, migration work, or security reviews.

---

## Operation: Compare Network Zones

Use compare mode to compare two exported zone files.

```bash
okta-network-zone-manager --config config.json --operation compare
```

Sample compare run:

```bash
cp samples/config.compare.sample.json config.json
okta-network-zone-manager --config config.json --operation compare
```

Expected output:

```text
output/network-zone-compare-<timestamp>/
  zone_drift.json
  zone_drift.csv
  zone_drift_report.md
  execution_report.json
  manifest.json
```

Compare mode is offline and does not require an Okta API token.

---

## Operation: Import Network Zones

Use import mode to create or replace zones from a reviewed input file.

Run a dry run first:

```bash
cp samples/config.import.sample.json config.json
okta-network-zone-manager --config config.json --operation import --dry-run
```

Apply the import only after reviewing the dry-run output:

```bash
okta-network-zone-manager --config config.json --operation import --apply
```

Expected output:

```text
output/network-zone-import-<timestamp>/
  change_plan.json
  rollback_actions.json
  execution_report.json
  manifest.json
```

Import mode should be reviewed carefully before apply mode is used.

---

## Operation: Manage Network Zones

Use manage mode for specific zone actions.

Supported action types:

```text
create
replace
activate
deactivate
delete
```

Example actions file:

```json
{
  "actions": [
    {
      "action": "deactivate",
      "match": {
        "name": "Temporary Vendor Zone"
      },
      "reason": "Vendor access window has ended"
    },
    {
      "action": "activate",
      "match": {
        "name": "Corporate VPN Zone"
      },
      "reason": "Re-enable trusted VPN access"
    }
  ]
}
```

Run a dry run first:

```bash
cp samples/config.manage.sample.json config.json
okta-network-zone-manager --config config.json --operation manage --dry-run
```

Apply only after review:

```bash
okta-network-zone-manager --config config.json --operation manage --apply
```

---

## Input File Format for Zone Import

Example import file:

```json
{
  "zones": [
    {
      "name": "Corporate VPN Zone",
      "type": "IP",
      "status": "ACTIVE",
      "usage": "POLICY",
      "gateways": [
        {
          "type": "CIDR",
          "value": "203.0.113.0/24"
        }
      ],
      "proxies": []
    }
  ]
}
```

The utility should preserve supported Okta zone fields where practical. Review all generated payloads before using apply mode.

---

## Output Reports

Each run creates timestamped output.

Common files:

| File | Purpose |
|---|---|
| `execution_report.json` | Counts, warnings, errors, and run metadata. |
| `manifest.json` | Input files, output files, operation, and timestamp. |
| `network_zones_full.json` | Full exported network zone data. |
| `network_zones_summary.csv` | Human-readable summary of exported zones. |
| `zone_drift.json` | Detailed comparison results. |
| `zone_drift.csv` | Summary of detected drift. |
| `zone_drift_report.md` | Markdown summary of detected drift. |
| `change_plan.json` | Preview or record of intended mutation actions. |
| `rollback_actions.json` | Best-effort rollback data for applied changes. |

Execution reports should not include API tokens or sensitive headers.

---

## Recommended Workflow

For client work, use this sequence:

```bash
cp samples/config.export.sample.json config.json
okta-network-zone-manager --config config.json --operation export
```

Review the exported zones.

For migration or drift review:

```bash
cp samples/config.compare.sample.json config.json
okta-network-zone-manager --config config.json --operation compare
```

For imports or changes:

```bash
cp samples/config.import.sample.json config.json
okta-network-zone-manager --config config.json --operation import --dry-run
```

After reviewing the dry-run report:

```bash
okta-network-zone-manager --config config.json --operation import --apply
```

---

## Testing

Install test dependencies:

```bash
python -m pip install -e ".[dev]"
```

Run tests:

```bash
pytest
```

Run tests with verbose output:

```bash
pytest -v
```

---

## Troubleshooting

### 401 Unauthorized

Confirm the Okta org URL and API token in `.env`.

```bash
cat .env
```

The org URL should look like:

```text
https://your-org.okta.com
```

Do not include `/api/v1` in `OKTA_ORG_URL`.

---

### 403 Forbidden

The API token may not have sufficient admin permissions to read or manage network zones.

Confirm the token was generated by an Okta admin account with the required permissions.

---

### No zones exported

Confirm the org actually has custom network zones configured.

Also confirm the configuration does not filter out system zones unintentionally.

---

### Delete action blocked

Delete actions are blocked by default.

To allow delete operations, update the config intentionally:

```json
{
  "allowDelete": true
}
```

Active zone deletion should remain disabled unless there is a documented reason to allow it.

```json
{
  "allowDeleteActiveZones": false
}
```

---

## Security Notes

- Do not commit `.env`.
- Do not commit raw exports from client environments unless they have been reviewed.
- Treat network zone data as sensitive because it may reveal trusted IP ranges, vendor access paths, VPN ranges, or security architecture details.
- Use dry-run mode before all mutation operations.
- Keep rollback output with the project evidence package.
- Review protected zone names before deleting or replacing anything.

---

## Practical Use Cases

Use this utility to:

- Back up Okta network zones before policy changes.
- Compare network zones between dev, test, and production Okta orgs.
- Detect missing or changed trusted IP zones after migration.
- Prepare evidence for IAM or security reviews.
- Safely import reviewed network zone definitions into a target org.
- Deactivate temporary vendor zones after a project ends.
- Validate that network zone changes were applied as expected.

---

## Notes

Network zones can directly affect authentication behavior when used in Okta policies. Review all planned changes before apply mode.

For production environments, export the current network zones before running import or manage operations.
