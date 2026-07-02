# WARNING

These utilities have limited testing and are provided as-is with no warranty. Use at your own risk.

# 16-okta-scope-claim-exporter

`okta-scope-claim-exporter` is a read-only utility that exports OAuth scopes and token claims from Okta custom authorization servers.

It is designed for API onboarding, migration planning, audit review, and post-build verification after using `15-okta-api-auth-server-builder`.

## What this utility does

The exporter connects to an Okta org and exports:

- Custom authorization servers
- OAuth scopes for each authorization server
- Token claims for each authorization server
- Scope and claim counts by authorization server
- Optional raw Okta API responses for evidence and troubleshooting

The utility writes JSON, CSV, Markdown, and execution report outputs.

## What this utility does not do

This utility does **not** create authorization servers.

It does **not** create, update, or delete scopes.

It does **not** create, update, or delete claims.

It does **not** export application assignments, app configuration, users, or groups.

It does **not** modify Okta in any way.

## Common use cases

Use this utility when you need to answer questions like:

```text
Which custom authorization servers exist?
Which OAuth scopes are configured on each authorization server?
Which token claims are configured on each authorization server?
Which scopes and claims need to be recreated in another Okta org?
Did Utility 15 create the expected scopes and claims?
Can we provide API security evidence for audit or architecture review?
```

## Folder structure

```text
16-okta-scope-claim-exporter/
  README.md
  SECURITY.md
  .gitignore
  .env.example
  config.example.json
  pyproject.toml
  requirements.txt
  requirements-dev.txt
  src/
    okta_scope_claim_exporter/
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
Okta API token with permission to read API authorization server configuration
```

The utility uses read-only Okta API calls.

## Install

From inside the `16-okta-scope-claim-exporter` folder:

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
okta-scope-claim-exporter --help
```

## Configure Okta access

Copy the environment example:

```bash
cp .env.example .env
```

Edit `.env`:

```text
OKTA_SOURCE_ORG_URL=https://your-org.okta.com
OKTA_API_TOKEN=your-okta-api-token
```

Use the normal Okta org URL.

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

Environment variables override the org URL in the JSON config.

## Create a working config

Copy the sample config:

```bash
cp samples/scope-claim-export.sample.json input/scope-claim-export.config.json
```

Open:

```text
input/scope-claim-export.config.json
```

Example:

```json
{
  "sourceOrgUrl": "https://your-org.okta.com",
  "outputDir": "output",
  "settings": {
    "includeInactiveAuthorizationServers": true,
    "includeScopes": true,
    "includeClaims": true,
    "includeRawResponses": false,
    "continueOnError": true,
    "requestTimeoutSeconds": 30,
    "maxRetries": 3
  },
  "filters": {
    "authorizationServerIds": [],
    "authorizationServerNames": [],
    "excludeAuthorizationServerIds": [],
    "excludeAuthorizationServerNames": []
  }
}
```

## Config field explanations

### `sourceOrgUrl`

The Okta org to read from.

If `.env` contains `OKTA_SOURCE_ORG_URL` or `OKTA_ORG_URL`, the environment value takes priority.

### `outputDir`

Parent folder where timestamped export output is written.

Default:

```json
"outputDir": "output"
```

### `includeInactiveAuthorizationServers`

Controls whether inactive authorization servers are exported.

```json
"includeInactiveAuthorizationServers": true
```

For audit and migration work, keep this as `true` so inactive but important configuration is not missed.

### `includeScopes`

Controls whether scopes are exported.

```json
"includeScopes": true
```

### `includeClaims`

Controls whether claims are exported.

```json
"includeClaims": true
```

### `includeRawResponses`

Controls whether raw Okta API response files are written.

```json
"includeRawResponses": false
```

Set this to `true` when you need deeper troubleshooting evidence. Raw responses may include sensitive configuration context, so review before sharing.

### `continueOnError`

If `true`, the utility continues exporting other authorization servers even if one server, scope list, or claim list fails.

```json
"continueOnError": true
```

### `authorizationServerIds`

Use this when you only want to export specific authorization servers by ID.

```json
"authorizationServerIds": ["ausabc123example"]
```

### `authorizationServerNames`

Use this when you only want to export specific authorization servers by name.

```json
"authorizationServerNames": ["Example API Authorization Server"]
```

### `excludeAuthorizationServerIds`

Use this to skip selected authorization servers by ID.

```json
"excludeAuthorizationServerIds": ["ausabc123example"]
```

### `excludeAuthorizationServerNames`

Use this to skip selected authorization servers by name.

```json
"excludeAuthorizationServerNames": ["Old Test Server"]
```

## Run dry-run first

Dry-run validates the config and writes a plan, but does not call Okta.

```bash
okta-scope-claim-exporter --config input/scope-claim-export.config.json --dry-run
```

Review the output folder:

```text
output/okta-scope-claim-exporter-YYYYMMDDTHHMMSSZ/
```

Dry-run output:

```text
scope_claim_export_plan.json
execution_report.md
```

## Export from Okta

After reviewing dry-run output, run export mode:

```bash
okta-scope-claim-exporter --config input/scope-claim-export.config.json --export
```

`--export` performs read-only Okta API calls and writes the export files.

## Output files

Each export creates a timestamped output folder:

```text
output/okta-scope-claim-exporter-YYYYMMDDTHHMMSSZ/
```

Expected output files:

```text
scope_claim_export.json
authorization_servers.csv
scopes.csv
claims.csv
scope_claim_summary.csv
scope_claim_report.md
execution_report.md
```

If `includeRawResponses` is true, the utility also writes:

```text
raw/authorization_servers.json
raw/<auth-server-id>_scopes.json
raw/<auth-server-id>_claims.json
```

## Output file purposes

### `scope_claim_export.json`

Complete structured export of authorization servers, scopes, and claims.

Use this file for migration planning or as input to a future loader/builder.

### `authorization_servers.csv`

Flattened list of authorization servers.

Useful for review and inventory.

### `scopes.csv`

Flattened list of scopes by authorization server.

Useful for API owner review and migration mapping.

### `claims.csv`

Flattened list of claims by authorization server.

Useful for token design review and security review.

### `scope_claim_summary.csv`

One row per authorization server with scope and claim counts.

### `scope_claim_report.md`

Human-readable report summarizing exported servers, scopes, claims, skipped objects, warnings, and errors.

### `execution_report.md`

Run evidence showing mode, target org, counts, errors, and output path.

## Recommended workflow with Utility 15

```text
1. Run 15-okta-api-auth-server-builder to create or update authorization server objects.
2. Run 16-okta-scope-claim-exporter in dry-run mode.
3. Run 16-okta-scope-claim-exporter in export mode.
4. Review scopes.csv and claims.csv.
5. Confirm scopes and claims match the intended API security design.
6. Store the export evidence with the delivery artifacts.
```

## Example: export one authorization server by name

Edit the config:

```json
"filters": {
  "authorizationServerIds": [],
  "authorizationServerNames": ["Example API Authorization Server"],
  "excludeAuthorizationServerIds": [],
  "excludeAuthorizationServerNames": []
}
```

Then run:

```bash
okta-scope-claim-exporter --config input/scope-claim-export.config.json --export
```

## Example: export all active and inactive authorization servers

```json
"settings": {
  "includeInactiveAuthorizationServers": true,
  "includeScopes": true,
  "includeClaims": true
}
```

Then run:

```bash
okta-scope-claim-exporter --config input/scope-claim-export.config.json --export
```

## Troubleshooting

### `Invalid Okta org URL`

The utility rejected the URL because it looks like an Admin Console URL or API endpoint.

Use:

```text
https://your-org.okta.com
```

Do not use:

```text
https://your-org-admin.okta.com
https://your-org.okta.com/admin
https://your-org.okta.com/api/v1
```

### `Missing Okta API token`

Set this in `.env`:

```text
OKTA_API_TOKEN=your-okta-api-token
```

### `403 Forbidden`

The API token does not have permission to read authorization server configuration.

Use a token created by an admin account with the appropriate Okta permissions.

### `No authorization servers matched the filters`

Check the server names and IDs in your config.

Try clearing the filters:

```json
"authorizationServerIds": [],
"authorizationServerNames": [],
"excludeAuthorizationServerIds": [],
"excludeAuthorizationServerNames": []
```

### Raw output contains sensitive configuration context

Raw responses can include configuration details that should be treated carefully.

Set this to false for normal use:

```json
"includeRawResponses": false
```

## Development

Install dev requirements:

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
