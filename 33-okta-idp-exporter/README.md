# WARNING

These utilities have limited testing and are provided as-is with no warranty. Use at your own risk.

# okta-idp-exporter

Python utility for exporting Okta external Identity Provider configuration with secret-safe output.

This utility is intended for Okta federation discovery, migration support, partner identity provider review, and security baseline work. It exports SAML, OIDC, social, and other configured external IdPs from an Okta org and writes reviewable JSON and CSV evidence files.

---

## What This Utility Does

The `okta-idp-exporter` utility exports configured Okta Identity Providers.

| Capability | Purpose |
|---|---|
| Export IdPs | Export external identity provider configuration from Okta. |
| Redact sensitive values | Remove or mask client secrets, tokens, private keys, and authorization headers from output. |
| Summarize IdPs | Write a CSV summary for review, migration planning, or audit evidence. |
| Split by type | Optionally group exported IdPs by type, such as `SAML2` or `OIDC`. |
| Export IdP keys | Optionally export IdP key credential metadata where available. |
| Filter output | Optionally filter by IdP type or status. |

This utility is read-only. It does not create, update, activate, deactivate, or delete IdPs.

---

## Safety Model

This utility is designed to be conservative.

The export operation is read-only:

```bash
okta-idp-exporter --config config.json
```

Dry-run mode validates configuration and writes a planned execution report without calling Okta:

```bash
okta-idp-exporter --config config.json --dry-run
```

The utility should not write API tokens, client secrets, private keys, or authorization headers to output files.

---

## Folder Structure

```text
33-okta-idp-exporter/
  README.md
  pyproject.toml
  .env.example
  .gitignore
  config.example.json
  src/
    okta_idp_exporter/
      __init__.py
      __main__.py
      cli.py
      config.py
      exporter.py
      normalize.py
      okta_client.py
      redact.py
      reports.py
  samples/
    config.export.sample.json
    config.saml-oidc-only.sample.json
    config.active-only.sample.json
    sample-idps_full.json
  tests/
    test_config.py
    test_normalize.py
    test_okta_client.py
    test_redact.py
  input/
  output/
```

---

## Requirements

- Python 3.10 or newer
- Okta admin API token
- Okta org URL
- Network access to the Okta tenant

The Okta API token should be generated from an account with permissions to read Identity Provider configuration. If key export is enabled, the token may also need permission to read IdP key credential metadata.

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
.venv/
output/
*.log
```

---

## Configuration

The utility is driven by `config.json`.

Example full export configuration:

```json
{
  "outputDir": "output",
  "includeInactive": true,
  "includeLinks": false,
  "includeKeys": true,
  "splitByType": true,
  "redactSensitiveValues": true,
  "redaction": {
    "replacement": "[REDACTED]",
    "redactKeyNamesContaining": [
      "secret",
      "token",
      "password",
      "private",
      "authorization",
      "client_secret",
      "assertion"
    ]
  },
  "filters": {
    "types": [],
    "statuses": []
  }
}
```

Example SAML and OIDC only configuration:

```json
{
  "outputDir": "output",
  "includeInactive": true,
  "includeLinks": false,
  "includeKeys": true,
  "splitByType": true,
  "redactSensitiveValues": true,
  "filters": {
    "types": ["SAML2", "OIDC"],
    "statuses": []
  }
}
```

Example active IdPs only configuration:

```json
{
  "outputDir": "output",
  "includeInactive": false,
  "includeLinks": false,
  "includeKeys": false,
  "splitByType": true,
  "redactSensitiveValues": true,
  "filters": {
    "types": [],
    "statuses": ["ACTIVE"]
  }
}
```

---

## Configuration Fields

| Field | Purpose |
|---|---|
| `outputDir` | Directory where timestamped export output is written. |
| `includeInactive` | Include inactive IdPs when true. |
| `includeLinks` | Include Okta `_links` objects when true. Usually leave false for cleaner output. |
| `includeKeys` | Also export IdP key credential metadata where available. |
| `splitByType` | Write separate JSON files by IdP type. |
| `redactSensitiveValues` | Mask sensitive fields before writing output. |
| `redaction.replacement` | Value used when masking sensitive fields. |
| `redaction.redactKeyNamesContaining` | Key-name fragments that should be redacted. |
| `filters.types` | Optional list of IdP types to include. |
| `filters.statuses` | Optional list of IdP statuses to include. |

---

## Operation: Dry Run

Use dry-run mode to validate the configuration and confirm the planned export behavior.

```bash
okta-idp-exporter --config config.json --dry-run
```

Expected output:

```text
output/idp-export-<timestamp>/
  execution_report.json
  manifest.json
```

Dry-run mode does not call Okta.

---

## Operation: Export IdPs

Use export mode to capture Okta Identity Provider configuration.

```bash
okta-idp-exporter --config config.json
```

Expected output:

```text
output/idp-export-<timestamp>/
  idps_full.json
  idps_summary.csv
  idp_keys.json
  idp_keys_summary.csv
  execution_report.json
  manifest.json
  idps_by_type/
```

If `includeKeys` is false, the IdP key files are not created.

---

## Output Reports

Each run creates timestamped output.

Common files:

| File | Purpose |
|---|---|
| `idps_full.json` | Redacted full Identity Provider export. |
| `idps_summary.csv` | Human-readable IdP summary for review. |
| `idp_keys.json` | Redacted IdP key credential metadata when enabled. |
| `idp_keys_summary.csv` | Human-readable key credential summary when enabled. |
| `idps_by_type/` | Optional grouped output by IdP type. |
| `execution_report.json` | Counts, warnings, errors, and run metadata. |
| `manifest.json` | Config path, output files, operation, and timestamp. |

Execution reports should not include API tokens or sensitive headers.

---

## Recommended Workflow

For client work, use this sequence.

Copy the sample configuration:

```bash
cp samples/config.export.sample.json config.json
```

Validate the planned run:

```bash
okta-idp-exporter --config config.json --dry-run
```

Run the export:

```bash
okta-idp-exporter --config config.json
```

Review the summary file:

```bash
cat output/idp-export-*/idps_summary.csv
```

For SAML and OIDC migration discovery, use this sample configuration:

```bash
cp samples/config.saml-oidc-only.sample.json config.json
```

Then run:

```bash
okta-idp-exporter --config config.json
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

Open `.env` and confirm the Okta org URL and API token.

The org URL should look like:

```text
https://your-org.okta.com
```

Do not include `/api/v1` in `OKTA_ORG_URL`.

---

### 403 Forbidden

The API token may not have sufficient admin permissions to read Identity Provider configuration or IdP key credential metadata.

If the IdP export succeeds but key export fails, review `execution_report.json`. The utility should write a warning for the key export failure while preserving the completed IdP export.

---

### No IdPs exported

Confirm the org has external Identity Providers configured.

Also confirm the configuration does not filter out the relevant IdP types or statuses.

Example unrestricted filters:

```json
{
  "filters": {
    "types": [],
    "statuses": []
  }
}
```

---

### Missing inactive IdPs

If inactive IdPs are missing, set `includeInactive` to true.

```json
{
  "includeInactive": true
}
```

---

### Sensitive values appear in output

Confirm redaction is enabled.

```json
{
  "redactSensitiveValues": true
}
```

Add additional key fragments if your org has custom fields that should be redacted.

```json
{
  "redaction": {
    "redactKeyNamesContaining": [
      "secret",
      "token",
      "password",
      "private",
      "authorization",
      "client_secret",
      "assertion",
      "customSensitiveField"
    ]
  }
}
```

---

## Security Notes

- Do not commit `.env`.
- Do not commit raw exports from client environments unless they have been reviewed.
- Treat IdP exports as sensitive because they may reveal federation architecture, partner domains, issuer URLs, callback behavior, account linking rules, and certificate metadata.
- Keep `redactSensitiveValues` enabled unless there is a documented reason to disable it.
- Review exported files before attaching them to tickets, documentation, or repositories.
- Rotate the Okta API token if it is accidentally shared.

---

## Practical Use Cases

Use this utility to:

- Back up external IdP configuration before migration work.
- Inventory SAML and OIDC IdPs across an Okta org.
- Prepare federation discovery evidence for a client engagement.
- Compare IdP configuration manually across dev, test, and production orgs.
- Identify inactive or stale external IdPs.
- Review account linking and provisioning behavior.
- Capture IdP key credential metadata for certificate or key rotation planning.
- Produce a clean CSV summary for architecture review or handoff.

---

## Notes

Identity Provider configuration can directly affect sign-in behavior, routing, account linking, provisioning, and federation trust. Review exported configuration carefully before using it for migration or production change planning.

For production environments, keep the redacted export with the project evidence package and store it in an approved location.
