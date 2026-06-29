# okta-config-backup

Read-only Okta configuration backup utility for reusable IAM delivery work.

This utility exports a timestamped Okta configuration backup for common tenant-level objects including applications, groups, group rules, policies, identity providers, authorization servers, hooks, network zones, trusted origins, branding/domain metadata, authenticators, and selected org settings.

It is designed as the first safety-layer utility in an Okta delivery toolkit. It does **not** create, update, assign, deactivate, or restore anything in Okta.

## What this utility produces

Each run creates a timestamped backup folder under `output/`, for example:

```text
output/okta-config-backup-20260625T142210Z/
  applications.json
  authorization_servers.json
  authenticators.json
  brands.json
  domains.json
  event_hooks.json
  group_rules.json
  groups.json
  identity_providers.json
  inline_hooks.json
  manifest.json
  network_zones.json
  org.json
  policies.json
  trusted_origins.json
  execution_report.md
```

The `manifest.json` records:

- backup ID and timestamp
- Okta org URL
- requested resources
- exported file paths
- object counts
- warnings and API failures
- redaction status
- utility version

## Key safety behaviors

- **Read-only execution:** only uses `GET` requests.
- **Secret-safe default output:** common sensitive values are redacted before files are written.
- **Timestamped evidence:** every run generates a manifest and execution report.
- **Pagination-aware:** follows Okta `Link` headers with `rel="next"`.
- **Rate-limit aware:** retries `429` and transient `5xx` responses using retry headers where available.
- **Partial failure tolerant:** records failed resources and continues unless `failFast` is enabled.
- **Config-driven:** accepts JSON config and environment variables.
- **Dry-run support:** validates configuration and shows the export plan without calling Okta or writing backup data.

## Requirements

- Python 3.10+
- Network access to the Okta org
- Okta API token with enough read permissions for the resources being exported

Okta API tokens should be treated as secrets. Do not commit `.env` files or real tokens to Git.

## Quick start

### 1. Open the folder in VS Code

Open this folder:

```text
01-okta-config-backup
```

### 2. Create a virtual environment

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

macOS/Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
pip install -e .
```

### 3. Create your `.env` file

Copy `.env.example` to `.env`:

```bash
cp .env.example .env
```

On Windows PowerShell:

```powershell
Copy-Item .env.example .env
```

Edit `.env`:

```text
OKTA_ORG_URL=https://your-org.okta.com
OKTA_API_TOKEN=your_okta_api_token_here
```

### 4. Review the config file

Use the sample config:

```text
config.example.json
```

You can copy it to `input/config.json`:

```bash
cp config.example.json input/config.json
```

Windows PowerShell:

```powershell
Copy-Item config.example.json input/config.json
```

### 5. Run a dry run

```bash
python -m okta_config_backup --config input/config.json --dry-run
```

The dry run validates the config and shows what would be exported. It does not call Okta.

### 6. Run the backup

```bash
python -m okta_config_backup --config input/config.json
```

The tool prints the backup folder path and report path when finished.

## CLI usage

```bash
python -m okta_config_backup --config input/config.json
```

Common options:

```bash
# Validate the export plan only
python -m okta_config_backup --config input/config.json --dry-run

# Export only selected resources
python -m okta_config_backup --config input/config.json --include applications,groups,policies

# Use a different output folder
python -m okta_config_backup --config input/config.json --output-dir output/client-a

# Export selected policy types
python -m okta_config_backup --config input/config.json --policy-types OKTA_SIGN_ON,PASSWORD,MFA_ENROLL
```

## Configuration

Example:

```json
{
  "orgUrl": "https://your-org.okta.com",
  "outputDir": "output",
  "include": [
    "org",
    "applications",
    "groups",
    "group_rules",
    "policies",
    "identity_providers",
    "authorization_servers",
    "event_hooks",
    "inline_hooks",
    "network_zones",
    "trusted_origins",
    "brands",
    "domains",
    "authenticators"
  ],
  "policyTypes": [
    "OKTA_SIGN_ON",
    "PASSWORD",
    "MFA_ENROLL",
    "IDP_DISCOVERY",
    "PROFILE_ENROLLMENT"
  ],
  "pageLimit": 200,
  "timeoutSeconds": 30,
  "maxRetries": 4,
  "retryBaseSeconds": 1.0,
  "failFast": false,
  "redactionEnabled": true
}
```

`OKTA_ORG_URL` in `.env` overrides `orgUrl` from the config file. `OKTA_API_TOKEN` must be supplied through the environment or `.env` file.

## Supported resource names

| Resource | Okta API path used |
|---|---|
| `org` | `/api/v1/org` |
| `applications` | `/api/v1/apps` |
| `groups` | `/api/v1/groups` |
| `group_rules` | `/api/v1/groups/rules` |
| `policies` | `/api/v1/policies?type=<policyType>` plus policy rules |
| `identity_providers` | `/api/v1/idps` |
| `authorization_servers` | `/api/v1/authorizationServers` plus scopes, claims, access policies, and rules |
| `event_hooks` | `/api/v1/eventHooks` |
| `inline_hooks` | `/api/v1/inlineHooks` |
| `network_zones` | `/api/v1/zones` |
| `trusted_origins` | `/api/v1/trustedOrigins` |
| `brands` | `/api/v1/brands` |
| `domains` | `/api/v1/domains` |
| `authenticators` | `/api/v1/authenticators` |
| `features` | `/api/v1/features` |
| `user_schema` | `/api/v1/meta/schemas/user/default` |

Some endpoints may require specific Okta licensing, admin permissions, or Okta Identity Engine features. If an endpoint fails, the error is recorded in `manifest.json` and `execution_report.md`.

## Output redaction

Redaction is enabled by default. The utility redacts common secret-bearing fields and hook authorization header values before writing output.

Examples of redacted fields include:

- `client_secret`
- `apiToken`
- `access_token`
- `refresh_token`
- `password`
- `privateKey`
- `sharedSecret`
- hook authorization header values

The goal is to make backup output safer for review and Git-based change control, but this is still an internal backup artifact. Review backup output before sharing it outside the delivery team.

## Testing

Run unit tests:

```bash
pip install -r requirements-dev.txt
pytest
```

Run syntax validation only:

```bash
python -m compileall src tests
```

## Exit codes

| Code | Meaning |
|---|---|
| `0` | Backup completed without recorded API errors |
| `1` | Backup completed with one or more recorded API errors |
| `2` | Configuration or runtime failure before backup completion |

## Recommended Git handling

Commit the utility code, examples, tests, and README.

Do not commit:

- `.env`
- real Okta API tokens
- client backup output unless it has been reviewed and approved
- unredacted customer configuration

The included `.gitignore` excludes `.env`, virtual environments, cache folders, and generated backup output.
