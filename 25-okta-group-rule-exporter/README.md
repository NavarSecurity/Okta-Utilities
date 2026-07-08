# WARNING

These utilities have limited testing and are provided as-is with no warranty. Use at your own risk.

# okta-group-rule-exporter

`okta-group-rule-exporter` is Utility 25 in the Okta utility pack. It exports Okta group rules and their conditions for backup, migration planning, cleanup analysis, and rule review.

This utility is **read-only**. It does not create, update, activate, deactivate, or delete group rules.

## What this utility exports

The utility exports:

- Group rule ID, name, status, and priority
- Rule conditions, including Okta Expression Language expressions
- Included and excluded source group conditions
- User exclusion conditions
- Target group assignments from rule actions
- Optional group ID to group name mappings from Okta `_embedded` data
- JSON and CSV evidence files for review or migration planning

## Important Okta behavior

Okta group rules are automation rules that assign users to groups based on conditions such as profile attributes or group membership. The Group Rules API supports listing group rules and can return group-name mapping data through the `expand` query parameter.

This exporter is meant to capture the current rule logic before cleanup, migration, or later recreation with another utility.

## Setup

Create a virtual environment.

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

Create your environment file.

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

Use the normal Okta org URL, not the Admin Console URL.

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

## Configure the export

Copy the sample config into the input folder.

macOS/Linux:

```bash
cp samples/group-rule-export.sample.json input/group-rule-export.config.json
```

Windows PowerShell:

```powershell
Copy-Item samples/group-rule-export.sample.json input/group-rule-export.config.json
```

Edit:

```text
input/group-rule-export.config.json
```

Example config:

```json
{
  "targetOrgUrl": "https://your-org.okta.com",
  "outputDir": "output",
  "export": {
    "ruleIds": [],
    "ruleNameContains": "",
    "statuses": ["ACTIVE", "INACTIVE"],
    "includeInactive": true,
    "expandGroupNames": true,
    "saveRawResponses": false
  },
  "settings": {
    "requestTimeoutSeconds": 30,
    "maxRetries": 3,
    "pageLimit": 200,
    "continueOnError": false
  }
}
```

## Config fields

| Field | Purpose |
|---|---|
| `targetOrgUrl` | Okta org base URL. `.env` value takes priority if set. |
| `outputDir` | Folder where timestamped run output is written. |
| `export.ruleIds` | Optional list of specific group rule IDs to keep in output. Leave empty for all rules. |
| `export.ruleNameContains` | Optional case-insensitive name filter. Leave blank for all names. |
| `export.statuses` | Statuses to include, usually `ACTIVE` and `INACTIVE`. |
| `export.includeInactive` | If false, inactive rules are removed even if listed in `statuses`. |
| `export.expandGroupNames` | Adds `expand=groupIdToGroupName` to the Okta request so output can include group names when Okta returns them. |
| `export.saveRawResponses` | Saves raw API response pages. Keep false unless troubleshooting. |
| `settings.pageLimit` | Okta page size. The API supports values up to 200. |
| `settings.maxRetries` | Retry count for temporary failures and rate limiting. |

## Dry run

Run a dry-run first:

```bash
okta-group-rule-exporter --config input/group-rule-export.config.json --dry-run
```

Dry-run validates configuration and creates a planned run folder without calling Okta.

## Export

Run the read-only export:

```bash
okta-group-rule-exporter --config input/group-rule-export.config.json --export
```

The utility will call Okta using:

```text
GET /api/v1/groups/rules
```

with pagination until all matching group rules are exported.

## Output files

Each run creates a timestamped folder under `output/`.

Typical files:

```text
group_rules.json
group_rules.csv
group_rule_conditions.csv
group_rule_group_targets.csv
group_rule_actions.csv
group_rule_summary.md
group_rule_export_result.json
execution_report.md
raw_group_rules.json    # only when saveRawResponses is true
```

## How to use the output

Use the files for:

- Group rule backup
- Migration planning
- Cleanup analysis
- Rule ownership review
- Detecting rules that target retired groups
- Preparing for Utility 26 group rule creation

Recommended workflow:

```text
1. Run Utility 25 to export group rules.
2. Review group_rules.csv and group_rule_conditions.csv.
3. Validate target groups and source conditions.
4. Use the output as planning input before recreating rules in another org.
```

## Required Okta permissions

The API token or OAuth client must have permission to read group rules. For OAuth-based access, Okta documents `okta.groups.read` as the read scope for listing group rules.

## Safety notes

- This utility is read-only.
- Do not commit `.env`.
- Do not commit API tokens.
- Review raw exports before storing them in a shared repo.
- Group rule expressions may contain internal attribute names or business logic.

## Troubleshooting

### Invalid Okta URL

Use the org URL, not the Admin Console URL.

Correct:

```text
https://your-org.okta.com
```

Incorrect:

```text
https://your-org-admin.okta.com
```

### Unauthorized

Check that:

- `.env` contains the correct Okta org URL
- `.env` contains a valid API token
- The token has permission to read group rules

### Empty export

Check whether:

- No group rules exist
- `statuses` excluded the rules
- `ruleIds` filtered out all rules
- `ruleNameContains` filtered out all rules

## Test the utility

Install dev dependencies:

```bash
python -m pip install -r requirements-dev.txt
```

Run tests:

```bash
python -m pytest
```
