# WARNING

These utilities have limited testing and are provided as-is with no warranty. Use at your own risk.

# 27-okta-group-cleanup-analyzer

`okta-group-cleanup-analyzer` is a read-only Okta utility that analyzes the current state of groups in an Okta org and identifies groups that may need cleanup review.

## What this utility does

The utility connects to Okta and reads current group evidence from the live org.

It can identify groups that are:

```text
Empty based on current group membership count
Unused based on current membership, app-assignment, and group-rule evidence
Duplicate by normalized group name
Stale by age or last update timestamp
Ownerless based on configured owner fields
Protected by name pattern, such as admin, break-glass, service account, or Everyone-style groups
```

## What this utility does not do

This utility does not:

```text
Delete Okta groups
Deactivate Okta groups
Remove users from groups
Change group rules
Change application assignments
Create cleanup tickets
Approve group deletion
```

Cleanup candidates must still be reviewed by an administrator, group owner, or application owner before action is taken.

## Folder structure

```text
27-okta-group-cleanup-analyzer/
  README.md
  SECURITY.md
  .env.example
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
Okta org URL
Okta API token with read access to groups, apps, and group rules
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

## Setup

Create and activate a Python virtual environment.

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
okta-group-cleanup-analyzer --help
```

Create your local environment file.

### macOS / Linux

```bash
cp .env.example .env
```

### Windows PowerShell

```powershell
Copy-Item .env.example .env
```

Edit `.env`:

```env
OKTA_ORG_URL=https://your-org.okta.com
OKTA_API_TOKEN=your-okta-api-token
```

Create a working config file.

### macOS / Linux

```bash
cp config.example.json input/group-cleanup-analyzer.config.json
```

### Windows PowerShell

```powershell
Copy-Item config.example.json input/group-cleanup-analyzer.config.json
```

Open and edit:

```text
input/group-cleanup-analyzer.config.json
```

## Configuration

The config should use API mode:

```json
{
  "mode": "api",
  "orgUrl": "https://your-org.okta.com",
  "analysis": {
    "findEmptyGroups": true,
    "findUnusedGroups": true,
    "findDuplicateNames": true,
    "findStaleGroups": true,
    "findOwnerlessGroups": true,
    "staleDays": 180,
    "ownerFields": [
      "owner",
      "groupOwner",
      "profile.owner",
      "profile.groupOwner"
    ],
    "protectedGroupNamePatterns": [
      "admin",
      "administrator",
      "super admin",
      "break glass",
      "service account",
      "everyone"
    ]
  },
  "settings": {
    "includeOktaBuiltInGroups": false,
    "fetchMemberCountsInApiMode": true,
    "fetchAppAssignmentCountsInApiMode": true,
    "fetchRuleTargetCountsInApiMode": true,
    "continueOnEvidenceFetchError": true,
    "requestTimeoutSeconds": 30,
    "maxRetries": 3,
    "strictMode": false
  },
  "outputDir": "output"
}
```

## Evidence settings

These settings control how complete the analysis is:

```text
fetchMemberCountsInApiMode
fetchAppAssignmentCountsInApiMode
fetchRuleTargetCountsInApiMode
```

For the most accurate cleanup picture, keep all three set to `true`.

`EMPTY_GROUP` is only reported when current member counts are fetched.

`UNUSED_GROUP` is only reported when all three evidence types are fetched:

```text
member count
app assignment count
group rule target count
```

If any required evidence cannot be fetched, the utility records an evidence warning and skips the affected empty or unused classification instead of guessing.

## Dry run

Run a dry run first:

```bash
okta-group-cleanup-analyzer --config input/group-cleanup-analyzer.config.json --dry-run
```

Dry run does not read group data from Okta. It confirms what the utility plans to check.

## Run analysis

Run the analyzer:

```bash
okta-group-cleanup-analyzer --config input/group-cleanup-analyzer.config.json --analyze
```

This creates a timestamped output folder under:

```text
output/
```

## Output files

The utility writes files such as:

```text
group_cleanup_result.json
group_cleanup_candidates.csv
empty_groups.csv
unused_groups.csv
duplicate_groups.csv
stale_groups.csv
ownerless_groups.csv
protected_groups.csv
group_cleanup_summary.md
execution_report.md
```

## How to interpret the results

`group_cleanup_candidates.csv` is the main review file.

Common reason codes:

```text
EMPTY_GROUP
UNUSED_GROUP
DUPLICATE_NAME
STALE_GROUP
OWNERLESS_GROUP
PROTECTED_NAME_PATTERN
```

Important interpretation notes:

```text
EMPTY_GROUP means the group currently has zero members according to the Okta API.
UNUSED_GROUP means the group currently has zero members, zero app assignments, and zero group-rule targets according to fetched evidence.
PROTECTED_NAME_PATTERN means the group name or description matched a protected keyword and should be review-only.
OWNERLESS_GROUP means no configured owner field was populated.
```

Do not delete groups based only on this report. Use it as an evidence-based review list.

## Recommended first test

Use the included sample config:

### macOS / Linux

```bash
cp samples/group-cleanup-analyzer.sample.json input/group-cleanup-analyzer.config.json
```

### Windows PowerShell

```powershell
Copy-Item samples/group-cleanup-analyzer.sample.json input/group-cleanup-analyzer.config.json
```

Edit `.env` with your Okta org URL and API token, then run:

```bash
okta-group-cleanup-analyzer --config input/group-cleanup-analyzer.config.json --dry-run
```

Then run:

```bash
okta-group-cleanup-analyzer --config input/group-cleanup-analyzer.config.json --analyze
```

## Safety notes

Before cleanup, verify:

```text
The group has no required members
The group is not assigned to an application
The group is not targeted by a group rule
The group is not used by an access policy
The group is not an admin, break-glass, service, or system group
The group owner or app owner has approved cleanup
```

## Development checks

Run tests:

```bash
python -m pytest
```

Run compile check:

```bash
python -m compileall src
```
