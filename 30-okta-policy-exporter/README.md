# okta-policy-exporter

# WARNING

These utilities have limited testing and are provided as-is with no warranty. Use at your own risk.

## Purpose

`okta-policy-exporter` is utility 30 in the Okta Utility Pack. It is a read-only command-line utility that exports Okta policies and policy rules for backup, migration planning, audit review, troubleshooting, and drift-detection inputs.

It exports:

- Global session / Okta sign-on policies
- App sign-in / authentication policies
- Password policies
- Authenticator / MFA enrollment policies
- Identity provider discovery policies, when enabled
- Profile enrollment policies, when enabled
- Okta account management policies, when visible to the API
- Custom authorization server access policies, when enabled and visible to the API token

## What this utility does not do

This utility does not create, update, delete, activate, deactivate, or reorder Okta policies or rules. It only reads from Okta and writes local export files.

It also does not print or write your Okta API token. Output is additionally passed through a conservative redaction function for secret-like fields.

## Setup

Install dependencies:

```bash
npm install
```

Create your local environment file:

```bash
cp .env.example .env
```

Create your working config file:

```bash
cp config.example.json config.json
```

Edit `.env` and set:

```bash
OKTA_ORG_URL=https://your-org.okta.com
OKTA_API_TOKEN=replace-with-okta-api-token
```

Edit `config.json` as needed for the policy types and export behavior.

## Required Okta access

Use an Okta API token from an admin account that is allowed to read policies and policy rules in the target org.

If `includeAuthorizationServerPolicies` is enabled, the token must also be able to read custom authorization servers and their access policies. Some orgs may not have API Access Management enabled, and some tokens may not have enough permission to read those objects. In that case, the utility records a warning and continues with the other exports.

## Run a dry run

Dry run validates config and shows the planned export. It does not call Okta.

```bash
node src/index.js --config config.json --dry-run
```

## Run the exporter

```bash
node src/index.js --config config.json
```

Run with additional progress output:

```bash
node src/index.js --config config.json --verbose
```

## Output files

Each run creates a timestamped folder under `output/`:

```text
output/policy-export-<timestamp>/
  policies_full.json
  policies_summary.csv
  policy_rules.csv
  execution_report.json
  manifest.json
  policies_by_type/
    OKTA_SIGN_ON.json
    ACCESS_POLICY.json
    PASSWORD.json
    MFA_ENROLL.json
    AUTHORIZATION_SERVER_ACCESS_POLICY.json
```

### `policies_full.json`

Full JSON export containing policy objects, rule objects, metadata, warnings, and errors.

### `policies_summary.csv`

Human-readable policy inventory with policy type, name, status, priority, system flag, timestamps, and rule count.

### `policy_rules.csv`

Flattened rule evidence with rule name, status, priority, condition summary, and action summary.

### `execution_report.json`

Run evidence file with counts, warnings, errors, output path, and generated files.

### `policies_by_type/`

One JSON file per exported policy type. These files are useful for review, migration planning, and utility 31 policy drift detection.

## Configuration reference

Example:

```json
{
  "outputDir": "./output",
  "includeOrgPolicies": true,
  "includeAuthorizationServerPolicies": true,
  "includeRules": true,
  "includeRawObjects": true,
  "policyTypes": [
    "OKTA_SIGN_ON",
    "ACCESS_POLICY",
    "PASSWORD",
    "MFA_ENROLL",
    "IDP_DISCOVERY",
    "PROFILE_ENROLLMENT",
    "ACCOUNT_MANAGEMENT"
  ],
  "authorizationServerIds": [],
  "pageLimit": 200,
  "failOnPolicyTypeError": false,
  "request": {
    "maxRetries": 5,
    "baseDelayMs": 750,
    "timeoutMs": 30000
  }
}
```

### `outputDir`

Directory where timestamped export folders are written.

### `includeOrgPolicies`

When `true`, exports policy types listed in `policyTypes` through the Okta Policy API.

### `includeAuthorizationServerPolicies`

When `true`, exports access policies attached to custom authorization servers.

### `includeRules`

When `true`, exports rules for each discovered policy.

### `includeRawObjects`

When `true`, writes full policy and rule JSON objects to `policies_full.json` and `policies_by_type/` files.

Set to `false` when you only want CSV evidence and run reports.

### `policyTypes`

Policy types to request from the Okta Policy API.

Common values:

```text
OKTA_SIGN_ON
ACCESS_POLICY
PASSWORD
MFA_ENROLL
IDP_DISCOVERY
PROFILE_ENROLLMENT
ACCOUNT_MANAGEMENT
```

Not every Okta org supports every type. Unsupported or unavailable types are recorded as warnings unless `failOnPolicyTypeError` is set to `true`.

### `authorizationServerIds`

Controls which authorization servers are exported.

Use an empty array to export all visible authorization servers:

```json
"authorizationServerIds": []
```

Use specific IDs or names to limit scope:

```json
"authorizationServerIds": ["default"]
```

### `pageLimit`

Page size for Okta list calls. `200` is a practical default.

### `failOnPolicyTypeError`

When `false`, the utility records unsupported or inaccessible policy types as warnings and continues.

When `true`, policy type export failures are treated as run errors.

### `request.maxRetries`

Maximum retry attempts for rate limits and transient server errors.

### `request.baseDelayMs`

Base retry delay used for exponential backoff when Okta does not provide a `Retry-After` value.

### `request.timeoutMs`

Request timeout in milliseconds.

## Identity Engine and Classic Engine note

For authenticator/MFA enrollment policies, Okta Identity Engine and Classic Engine can return different settings shapes. Identity Engine may return `settings.authenticators`; Classic Engine or migrated policies may return `settings.factors`. This utility intentionally preserves the raw policy settings so reviewers can see the actual schema returned by the org.

## Troubleshooting

### `Config file not found`

Create a working config file:

```bash
cp config.example.json config.json
```

### `OKTA_ORG_URL is required`

Create `.env` and set the org URL:

```bash
cp .env.example .env
```

Then edit `.env`:

```bash
OKTA_ORG_URL=https://your-org.okta.com
```

### `OKTA_API_TOKEN is required`

Set the API token in `.env`:

```bash
OKTA_API_TOKEN=replace-with-okta-api-token
```

### Authorization server warning

If the run reports that authorization servers could not be listed, either API Access Management is not available in the org, the token does not have enough permission, or authorization server export is not needed.

To skip authorization server policy export, set this in `config.json`:

```json
"includeAuthorizationServerPolicies": false
```

### Unsupported policy type warning

If one policy type fails but the rest of the export works, remove that policy type from `policyTypes` or leave `failOnPolicyTypeError` as `false`.

## Test

Run local unit tests:

```bash
npm test
```
