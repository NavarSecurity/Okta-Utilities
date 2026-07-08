# WARNING

These utilities have limited testing and are provided as-is with no warranty. Use at your own risk.

# 26-okta-group-rule-create

`okta-group-rule-create` creates Okta group rules from a JSON or YAML configuration file.

Use this utility when you need repeatable Okta group rules that automatically assign users to target groups based on profile conditions.

## Purpose

This utility creates group rules such as:

```text
If user department equals Engineering, assign the user to Engineering Users.
If user email contains @contractor.example.com, assign the user to Contractors.
If user department equals Engineering and title contains Manager, assign the user to Engineering Managers.
```

The utility now supports **basic conditions**, so you do not need to know Okta Expression Language for common group-rule use cases. It still supports raw Okta Expression Language through the `expression` field for advanced rules.

## What this utility does

```text
Creates Okta group rules from config
Supports basic condition input similar to Okta's basic condition rule builder
Converts basic conditions into the expression payload Okta expects
Still supports advanced Okta Expression Language through expression
Supports target groups by group ID or exact group name
Supports excluded users and excluded groups
Supports approved-row gating
Checks for existing rules by name
Skips existing rules by default
Creates rules inactive first by default
Optionally activates rules after creation
Writes rollback_plan.json
Writes created, skipped, failed, plan, result, and execution report files
Rejects -admin Okta URLs
```

## What this utility does not do

```text
It does not create Okta groups
It does not create Okta users
It does not update existing group rules
It does not delete existing group rules
It does not automatically approve rule creation
It does not bypass Okta group rule evaluation behavior
```

Create target groups first with `23-okta-group-create` or manually in Okta before using this utility.

## Setup

Create a Python virtual environment.

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

Install the utility.

```bash
python -m pip install --upgrade pip
python -m pip install -e .
```

Confirm the command is available.

```bash
okta-group-rule-create --help
```

Create your environment file.

### macOS / Linux

```bash
cp .env.example .env
```

### Windows PowerShell

```powershell
Copy-Item .env.example .env
```

Edit `.env` and populate these values:

```env
OKTA_TARGET_ORG_URL=https://your-org.okta.com
OKTA_API_TOKEN=your-okta-api-token
```

Use the normal Okta org URL, not the Admin Console URL.

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

## Prepare the config

Create a working config file.

### macOS / Linux

```bash
cp config.example.json input/group-rule-create.config.json
```

### Windows PowerShell

```powershell
Copy-Item config.example.json input/group-rule-create.config.json
```

Open and edit:

```text
input/group-rule-create.config.json
```

## Basic condition examples

For common rules, use `basicCondition` instead of `expression`.

### Department equals Engineering

```json
{
  "name": "Rule - Engineering Users",
  "approved": true,
  "basicCondition": {
    "attribute": "department",
    "operator": "equals",
    "value": "Engineering"
  },
  "targetGroupNames": ["Engineering Users"],
  "activate": false
}
```

The utility converts that to the expression Okta expects:

```text
user.department == "Engineering"
```

### Email contains a domain

```json
{
  "name": "Rule - Contractor Users",
  "approved": true,
  "basicCondition": {
    "attribute": "email",
    "operator": "contains",
    "value": "@contractor.example.com"
  },
  "targetGroupNames": ["Contractors"],
  "activate": false
}
```

The utility converts that to:

```text
String.stringContains(user.email, "@contractor.example.com")
```

### Multiple basic conditions

Use `basicConditions` when a rule needs more than one condition.

```json
{
  "name": "Rule - Engineering Managers",
  "approved": true,
  "basicConditions": {
    "match": "all",
    "conditions": [
      {
        "attribute": "department",
        "operator": "equals",
        "value": "Engineering"
      },
      {
        "attribute": "title",
        "operator": "contains",
        "value": "Manager"
      }
    ]
  },
  "targetGroupNames": ["Engineering Managers"],
  "activate": false
}
```

Use:

```json
"match": "all"
```

when every condition must be true.

Use:

```json
"match": "any"
```

when at least one condition can be true.

## Supported basic condition operators

| Operator | Meaning | Example |
|---|---|---|
| `equals` | Attribute equals value | department equals Engineering |
| `notEquals` | Attribute does not equal value | department notEquals Finance |
| `contains` | Attribute contains text | email contains @example.com |
| `notContains` | Attribute does not contain text | email notContains @vendor.com |
| `startsWith` | Attribute starts with text | login startsWith svc- |
| `endsWith` | Attribute ends with text | email endsWith @example.com |
| `isPresent` | Attribute is not blank | employeeNumber isPresent |
| `isBlank` | Attribute is blank | costCenter isBlank |
| `greaterThan` | Numeric comparison | employeeLevel greaterThan 5 |
| `greaterThanOrEquals` | Numeric comparison | employeeLevel greaterThanOrEquals 5 |
| `lessThan` | Numeric comparison | employeeLevel lessThan 5 |
| `lessThanOrEquals` | Numeric comparison | employeeLevel lessThanOrEquals 5 |

For numeric comparisons, add:

```json
"valueType": "number"
```

Example:

```json
{
  "attribute": "employeeLevel",
  "operator": "greaterThanOrEquals",
  "value": 5,
  "valueType": "number"
}
```

## Advanced expression option

For advanced rules, use `expression` directly.

```json
{
  "name": "Rule - Advanced Contractor Users",
  "approved": true,
  "expression": "String.stringContains(user.email, \"@contractor.example.com\")",
  "targetGroupNames": ["Contractors"],
  "activate": false
}
```

Do not use `expression` and `basicCondition` / `basicConditions` in the same rule.

## Full example config

```json
{
  "targetOrgUrl": "https://your-org.okta.com",
  "settings": {
    "skipExisting": true,
    "requireApproved": true,
    "activateAfterCreate": false,
    "continueOnError": false,
    "maxRulesPerRun": 25,
    "requestTimeoutSeconds": 30,
    "maxRetries": 3
  },
  "rules": [
    {
      "name": "Rule - Engineering Users",
      "description": "Assign Engineering users to the Engineering Users group.",
      "approved": true,
      "basicCondition": {
        "attribute": "department",
        "operator": "equals",
        "value": "Engineering"
      },
      "targetGroupIds": ["00gexampleengineering"],
      "targetGroupNames": [],
      "excludeUserIds": [],
      "excludeGroupIds": [],
      "activate": false
    }
  ]
}
```

## Config field explanations

| Field | Purpose |
|---|---|
| `targetOrgUrl` | Okta org URL. `.env` value takes priority if populated. |
| `settings.skipExisting` | Skips rules that already exist by name. |
| `settings.requireApproved` | Requires `approved: true` before a rule is created. |
| `settings.activateAfterCreate` | Default activation behavior when a rule does not set `activate`. |
| `settings.continueOnError` | Continues creating later rules after a failure. |
| `settings.maxRulesPerRun` | Safety limit for how many rules can be processed in one run. |
| `rules[].name` | Group rule name. Must be unique enough for existing-rule detection. |
| `rules[].description` | Optional description recorded in the rule profile. |
| `rules[].approved` | Must be `true` when approval gating is enabled. |
| `rules[].basicCondition` | One simple condition with attribute, operator, and value. |
| `rules[].basicConditions` | Multiple simple conditions joined by `match: all` or `match: any`. |
| `rules[].expression` | Advanced Okta Expression Language condition. Do not use with basic conditions. |
| `rules[].targetGroupIds` | Target Okta group IDs to assign users into. |
| `rules[].targetGroupNames` | Target group names to resolve during apply mode. |
| `rules[].excludeUserIds` | User IDs excluded from rule evaluation. |
| `rules[].excludeGroupIds` | Group IDs excluded from rule evaluation. |
| `rules[].activate` | Optional per-rule activation setting. |

## Target group IDs versus group names

Using group IDs is safer because Okta group IDs are unique.

```json
"targetGroupIds": ["00gabc123xyz456"]
```

Using group names is more convenient, but the utility must look up the group during apply mode.

```json
"targetGroupNames": ["Engineering Users"]
```

When group names are used, the utility requires an exact group-name match. If no group or multiple groups are found, the rule is skipped or failed instead of guessing.

## Run a dry run

Always run dry-run first.

```bash
okta-group-rule-create --config input/group-rule-create.config.json --dry-run
```

Dry-run mode:

```text
Reads the config
Validates rules
Converts basic conditions to expressions
Builds a creation plan
Does not call Okta to create rules
Does not change Okta
Writes output files for review
```

Expected output folder:

```text
output/okta-group-rule-create-YYYYMMDDTHHMMSSZ/
```

Review:

```text
group_rule_plan.json
group_rule_create_result.json
execution_report.md
```

## Apply the rules

After reviewing the dry-run plan, run apply mode.

```bash
okta-group-rule-create --config input/group-rule-create.config.json --apply
```

Apply mode:

```text
Checks existing group rules by name
Resolves target groups by name when needed
Creates approved rules
Optionally activates created rules
Writes rollback output and execution evidence
```
