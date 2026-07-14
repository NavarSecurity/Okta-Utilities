# WARNING

These utilities have limited testing and are provided as-is with no warranty. Use at your own risk.

# okta-idp-create

Python utility for creating external SAML 2.0 and OpenID Connect Identity Providers in Okta from reviewed JSON configuration files.

This utility is intended for Okta federation setup, tenant migration support, partner onboarding, and repeatable non-production testing. It is designed to preview planned Identity Provider creation actions before making changes to an Okta org.

---

## What This Utility Does

The `okta-idp-create` utility supports controlled creation of external IdP objects in Okta.

| Capability | Purpose |
|---|---|
| `dry-run` | Validate input files and generate a planned change report without creating anything. |
| `apply` | Create approved external IdPs in Okta. |
| Existing IdP detection | Check for existing IdPs by name and skip or fail based on configuration. |
| Secret redaction | Redact client secrets, private keys, tokens, and certificate-like sensitive values from output reports. |
| Rollback evidence | Write best-effort rollback actions for IdPs created during apply mode. |

The utility accepts Okta API-compatible payloads so exported or reviewed IdP configuration can be promoted into a target org with minimal transformation.

---

## Safety Model

This utility is conservative by default.

Dry run is the default behavior:

```bash
okta-idp-create --config config.json --dry-run
```

Apply mode must be explicit:

```bash
okta-idp-create --config config.json --apply
```

The utility should not create an Identity Provider unless `--apply` is provided.

By default, existing IdPs with the same name are skipped instead of duplicated.

---

## Folder Structure

```text
34-okta-idp-create/
  README.md
  pyproject.toml
  .env.example
  .gitignore
  config.example.json
  src/
    okta_idp_create/
      __init__.py
      __main__.py
      cli.py
      config.py
      okta_client.py
      planner.py
      redact.py
      reports.py
  samples/
    config.create.sample.json
    config.oidc.sample.json
    idps.create.sample.json
    idps.oidc.sample.json
  tests/
    test_config.py
    test_planner.py
    test_redact.py
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

The Okta API token should be generated from an account with permissions to manage Identity Providers.

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
cp samples/config.create.sample.json config.json
```

Copy a sample IdP input file:

```bash
cp samples/idps.create.sample.json input/idps.create.json
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

Example configuration:

```json
{
  "inputFile": "input/idps.create.json",
  "outputDirectory": "output",
  "checkExisting": true,
  "matchBy": "name",
  "onExisting": "skip",
  "activateAfterCreate": false,
  "redactSensitiveValues": true,
  "timeoutSeconds": 30
}
```

Configuration fields:

| Field | Purpose |
|---|---|
| `inputFile` | Path to the reviewed IdP creation input file. |
| `outputDirectory` | Base directory for timestamped output reports. |
| `checkExisting` | Checks the target org for existing IdPs before create. |
| `matchBy` | Matching strategy. Currently supports `name`. |
| `onExisting` | Behavior when an IdP with the same name exists. Supports `skip` or `error`. |
| `activateAfterCreate` | Activates created IdPs after creation if supported by the org and payload. |
| `redactSensitiveValues` | Redacts secrets from reports and payload evidence. |
| `timeoutSeconds` | HTTP timeout for Okta API requests. |

---

## IdP Input File Format

The input file should contain an `identityProviders` array.

Recommended input pattern:

```json
{
  "identityProviders": [
    {
      "name": "Utility34 Test SAML IdP",
      "type": "SAML2",
      "description": "Test-only external SAML IdP for utility validation.",
      "payload": {
        "type": "SAML2",
        "name": "Utility34 Test SAML IdP",
        "protocol": {},
        "policy": {}
      }
    }
  ]
}
```

Use the `payload` field for the Okta API-compatible Identity Provider creation payload.

This utility intentionally avoids inventing federation details. For SAML, obtain the issuer, SSO URL, and signing certificate or key reference from the external IdP. For OIDC, obtain the issuer, authorization endpoint, token endpoint, JWKS endpoint, client ID, and client secret from the external IdP.

---

## SAML IdP Input Example

A SAML IdP usually needs external IdP details such as issuer, SSO URL, and certificate/key information.

Example structure:

```json
{
  "identityProviders": [
    {
      "name": "Utility34 Test SAML IdP",
      "type": "SAML2",
      "payload": {
        "type": "SAML2",
        "name": "Utility34 Test SAML IdP",
        "protocol": {
          "type": "SAML2",
          "endpoints": {
            "sso": {
              "url": "https://example.com/utility34-test/saml/sso",
              "binding": "HTTP-POST",
              "destination": "https://example.com/utility34-test/saml/sso"
            }
          },
          "settings": {
            "nameFormat": "urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress"
          },
          "credentials": {
            "trust": {
              "issuer": "urn:utility34:test:saml:idp",
              "audience": "https://your-org.okta.com",
              "kid": "replace-with-uploaded-idp-key-id"
            }
          }
        },
        "policy": {
          "provisioning": {
            "action": "DISABLED",
            "profileMaster": false,
            "groups": {
              "action": "NONE"
            }
          },
          "accountLink": {
            "action": "DISABLED"
          },
          "subject": {
            "userNameTemplate": {
              "template": "idpuser.subjectNameId"
            },
            "matchType": "USERNAME"
          },
          "maxClockSkew": 120000
        }
      }
    }
  ]
}
```

Review the payload against your Okta org and Identity Engine or Classic Engine behavior before apply mode.

---

## OIDC IdP Input Example

An OIDC IdP usually needs issuer, authorization endpoint, token endpoint, JWKS endpoint, client ID, client secret, and scopes.

Example structure:

```json
{
  "identityProviders": [
    {
      "name": "Utility34 Test OIDC IdP",
      "type": "OIDC",
      "payload": {
        "type": "OIDC",
        "name": "Utility34 Test OIDC IdP",
        "protocol": {
          "type": "OIDC",
          "scopes": [
            "openid",
            "profile",
            "email"
          ],
          "endpoints": {
            "authorization": {
              "url": "https://idp.example.com/oauth2/v1/authorize",
              "binding": "HTTP-REDIRECT"
            },
            "token": {
              "url": "https://idp.example.com/oauth2/v1/token",
              "binding": "HTTP-POST"
            },
            "jwks": {
              "url": "https://idp.example.com/oauth2/v1/keys",
              "binding": "HTTP-REDIRECT"
            },
            "userInfo": {
              "url": "https://idp.example.com/oauth2/v1/userinfo",
              "binding": "HTTP-REDIRECT"
            }
          },
          "credentials": {
            "client": {
              "client_id": "replace-with-client-id",
              "client_secret": "replace-with-client-secret"
            }
          },
          "issuer": {
            "url": "https://idp.example.com"
          }
        },
        "policy": {
          "provisioning": {
            "action": "DISABLED",
            "profileMaster": false,
            "groups": {
              "action": "NONE"
            }
          },
          "accountLink": {
            "action": "DISABLED"
          },
          "subject": {
            "userNameTemplate": {
              "template": "idpuser.email"
            },
            "matchType": "USERNAME"
          },
          "maxClockSkew": 120000
        }
      }
    }
  ]
}
```

Do not commit real client secrets.

---

## Dry Run

Run dry run before applying changes:

```bash
okta-idp-create --config config.json --dry-run
```

Expected output:

```text
output/idp-create-<timestamp>/
  planned_changes.json
  idp_payloads_redacted.json
  skipped_existing.json
  failed_idps.json
  execution_report.json
  manifest.json
```

Dry run validates the input structure and writes planned actions. If `checkExisting` is enabled and Okta credentials are present, it also checks whether an IdP with the same name already exists.

---

## Apply

Apply only after reviewing the dry-run output.

```bash
okta-idp-create --config config.json --apply
```

Expected output:

```text
output/idp-create-<timestamp>/
  planned_changes.json
  created_idps.json
  idp_payloads_redacted.json
  skipped_existing.json
  failed_idps.json
  rollback_actions.json
  execution_report.json
  manifest.json
```

The utility writes rollback actions such as:

```json
{
  "action": "delete",
  "idpId": "0oaexample123",
  "name": "Utility34 Test SAML IdP",
  "reason": "Rollback created IdP from utility 34 apply run"
}
```

Rollback actions are evidence files. Review them before using them manually or in another tool.

---

## Recommended Workflow

For client work, use this sequence.

Copy sample files:

```bash
cp samples/config.create.sample.json config.json
cp samples/idps.create.sample.json input/idps.create.json
```

Update `.env` with the target Okta org URL and API token.

Update `input/idps.create.json` with reviewed IdP payloads.

Run dry run:

```bash
okta-idp-create --config config.json --dry-run
```

Review:

```text
planned_changes.json
idp_payloads_redacted.json
execution_report.json
```

Apply only after review:

```bash
okta-idp-create --config config.json --apply
```

Archive the output folder with project evidence.

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

The API token may not have sufficient admin permissions to manage Identity Providers.

Confirm the token was generated by an Okta admin account with the required permissions.

---

### Existing IdP skipped

If an IdP with the same name already exists, the utility skips it by default.

To fail instead of skip, update config:

```json
{
  "onExisting": "error"
}
```

---

### SAML IdP creation fails because of a key or certificate issue

Confirm the IdP signing certificate or key reference was uploaded or represented in the way your Okta org expects.

For many production SAML IdPs, you need to establish trust using the IdP signing certificate before the configuration is complete.

---

### OIDC IdP creation fails because of client credentials

Confirm the client ID and client secret are correct and that the redirect URI configured at the external OIDC provider matches the Okta callback URL.

The callback URL is usually based on the Okta org domain, for example:

```text
https://your-org.okta.com/oauth2/v1/authorize/callback
```

---

## Security Notes

- Do not commit `.env`.
- Do not commit real OIDC client secrets.
- Do not commit private keys.
- Treat IdP payloads as sensitive because they may expose issuer URLs, domains, partner federation details, client IDs, and trust settings.
- Use dry-run mode before apply mode.
- Keep execution reports and rollback files with project evidence.
- Do not create routing rules for a test IdP unless the sign-in impact is understood.

---

## Practical Use Cases

Use this utility to:

- Recreate external IdPs in a target Okta org during migration.
- Create test SAML or OIDC IdPs for exporter validation.
- Standardize partner federation setup from reviewed payloads.
- Support repeatable lower-environment IdP creation.
- Produce evidence showing which IdPs were planned, created, skipped, or failed.
- Avoid manual copy/paste mistakes in Admin Console IdP setup.

---

## Notes

This utility creates the IdP object. It does not automatically configure IdP routing rules, app sign-in behavior, profile mappings, or downstream authorization behavior.

For production environments, create or export a backup before applying IdP changes.
