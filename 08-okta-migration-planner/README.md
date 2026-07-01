# WARNING

These utilities have limited testing and are provided as-is with no warranty. Use at your own risk.

# 08-okta-migration-planner

Read-only utility for comparing a source Okta configuration backup against a target Okta configuration backup and generating migration planning artifacts.

This tool does **not** call Okta APIs and does **not** change either Okta org. It reads local backup folders created by `01-okta-config-backup`, maps source objects to target objects, identifies missing objects, flags conflicts, and produces cutover readiness evidence.

## Purpose

Use this utility before migration, restore, cloning, Terraform import, or cutover work to answer:

- What exists in the source org?
- What already exists in the target org?
- What source objects are missing from the target?
- Which objects match but have configuration differences?
- Which items require manual review before migration?
- Is the target environment ready for cutover work?

## Supported resource types

Initial supported resources:

- `groups`
- `applications`
- `trusted_origins`
- `network_zones`
- `authorization_servers`
- `policies`
- `identity_providers`

Higher-risk resources such as policies and identity providers are included for planning, but missing items are marked for manual review by default instead of being treated as simple create candidates.

## Install

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .
```

Windows PowerShell:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e .
```

Confirm installation:

```bash
okta-migration-planner --help
```

## Basic usage

Run against the included samples:

```bash
okta-migration-planner --config config.example.json
```

Run against real backup folders:

```bash
okta-migration-planner \
  --source-backup-dir ../01-okta-config-backup/output/source-backup-folder \
  --target-backup-dir ../01-okta-config-backup/output/target-backup-folder
```

Analyze selected resources only:

```bash
okta-migration-planner \
  --source-backup-dir ../backups/source \
  --target-backup-dir ../backups/target \
  --include groups,applications,trusted_origins
```

Strict mode:

```bash
okta-migration-planner \
  --source-backup-dir ../backups/source \
  --target-backup-dir ../backups/target \
  --strict
```

Strict mode returns a blocking readiness status when warnings exist.

## Outputs

Each run creates a timestamped output folder:

```text
output/okta-migration-plan-YYYYMMDDTHHMMSSZ/
  migration_plan.json
  object_mapping.csv
  conflicts.csv
  manual_review_items.csv
  cutover_readiness_report.md
  execution_report.md
```

### `migration_plan.json`

Full machine-readable migration plan with summary counts, resource-by-resource planning details, conflicts, manual review items, and cutover readiness status.

### `object_mapping.csv`

Source-to-target mapping table. Useful for migration workbooks, review sessions, and downstream scripts.

### `conflicts.csv`

Items that matched by natural key but have material differences, or duplicate natural keys that need review.

### `manual_review_items.csv`

Items that cannot be safely planned automatically, such as high-risk objects missing from the target or objects without a usable natural key.

### `cutover_readiness_report.md`

Human-readable summary of blockers, warnings, resource counts, and recommended next steps.

## Matching behavior

The planner matches source and target objects by natural keys:

| Resource | Natural key |
|---|---|
| `groups` | `profile.name` |
| `applications` | `label` |
| `trusted_origins` | `origin` or `name` |
| `network_zones` | `name` |
| `authorization_servers` | `name` |
| `policies` | `type::name` |
| `identity_providers` | `name` |

If a source object has no target match, the planner marks it as either:

- `missing_in_target`, for safer create/restore candidates
- `manual_review_missing_high_risk`, for higher-risk objects such as policies and IdPs

## Configuration

Example:

```json
{
  "sourceBackupDir": "samples/source-backup",
  "targetBackupDir": "samples/target-backup",
  "outputDir": "output",
  "include": [
    "groups",
    "applications",
    "trusted_origins",
    "network_zones",
    "authorization_servers",
    "policies",
    "identity_providers"
  ],
  "compareMaterialDifferences": true,
  "treatMissingHighRiskAsBlocker": true,
  "strictMode": false,
  "writeCsv": true,
  "writeMarkdown": true,
  "maxJsonPreviewChars": 300
}
```

## Recommended workflow

```text
1. Run okta-config-backup against the source org.
2. Run okta-config-backup against the target org.
3. Run okta-backup-validator against both backups.
4. Run okta-migration-planner.
5. Review migration_plan.json, object_mapping.csv, conflicts.csv, and cutover_readiness_report.md.
6. Use the plan to drive restore, cloning, Terraform import, or manual migration tasks.
7. Run another backup and diff after changes are made.
```

## Exit codes

| Exit code | Meaning |
|---:|---|
| `0` | Plan generated and readiness is not blocked. |
| `1` | Plan generated, but readiness is blocked or strict mode failed. |
| `2` | Runtime/configuration error. |

## Tests

```bash
python -m pip install -r requirements-dev.txt
pytest
python -m compileall src tests
```

## Disclaimer

These utilities have limited testing and are provided as-is with no warranty. Use at your own risk, review all code and output carefully, and test in a non-production environment before using on sensitive, client-owned, or production systems.
