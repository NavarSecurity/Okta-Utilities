> WARNING: These utilities have limited testing and are provided as-is with no warranty. Use at your own risk.

# 11-okta-oidc-app-create

`okta-oidc-app-create` creates Okta OIDC applications from a JSON configuration file with dry-run planning, duplicate checks, optional group/user assignments, rollback output, and execution evidence.

This utility is intended for repeatable application onboarding work where OIDC app configuration needs to be created consistently across Okta orgs.

## What this utility does

The utility can create one or more OIDC applications in a target Okta org using config-driven input.

Supported capabilities include:

- Dry-run planning before apply
- Explicit `--apply` required before creating anything
- OIDC app payload generation
- Redirect URI and post-logout URI configuration
- Grant type and response type configuration
- PKCE setting support
- Token endpoint authentication method support
- Duplicate detection by app label
- Optional group assignments
- Optional user assignments
- Rollback plan generation for created apps and assignments
- Timestamped execution reports
- JSON and CSV evidence output

## What this utility does not do

This utility does **not** clone an existing app from another org. Use `10-okta-app-cloner` for that.

This utility does **not** migrate all applications automatically.

This utility does **not** configure every possible Okta OIDC option.

This utility does **not** manage app sign-on policies, app provisioning, IdP routing rules, profile mappings, or branding.

## Folder structure

```text
11-okta-oidc-app-create/
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
Network access to the target Okta org
An Okta API token with permission to create applications
```

For optional assignments, the token also needs permission to read groups/users and assign them to applications.

## Installation

From inside the `11-okta-oidc-app-create` folder, create a virtual environment.

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
okta-oidc-app-create --help
```

## Configure target Okta access

Copy the example environment file:

```bash
cp .env.example .env
```

Windows PowerShell:

```powershell
Copy-Item .env.example .env
```

Edit `.env`:

```text
OKTA_TARGET_ORG_URL=https://your-org.okta.com
OKTA_TARGET_API_TOKEN=your_api_token_here
```

Do not include `SSWS` before the token. The utility adds the authorization header.

Correct:

```text
OKTA_TARGET_API_TOKEN=00abc123tokenvalue
```

Incorrect:

```text
OKTA_TARGET_API_TOKEN=SSWS 00abc123tokenvalue
```

## Create a working config file

Copy the example config:

```bash
cp config.example.json input/oidc-app.config.json
```

Windows PowerShell:

```powershell
Copy-Item config.example.json input/oidc-app.config.json
```

Edit:

```text
input/oidc-app.config.json
```

Example:

```json
{
  "targetOrgUrl": "https://your-org.okta.com",
  "outputDir": "output",
  "createAssignments": false,
  "skipExisting": true,
  "failFast": false,
  "pageLimit": 200,
  "timeoutSeconds": 30,
  "maxRetries": 4,
  "retryBaseSeconds": 1.0,
  "applications": [
    {
      "label": "Customer Portal OIDC",
      "applicationType": "web",
      "grantTypes": ["authorization_code", "refresh_token"],
      "responseTypes": ["code"],
      "redirectUris": ["https://app.example.com/callback"],
      "postLogoutRedirectUris": ["https://app.example.com/logout"],
      "initiateLoginUri": "https://app.example.com/login",
      "pkceRequired": false,
      "tokenEndpointAuthMethod": "client_secret_basic",
      "consentMethod": "REQUIRED",
      "assignments": {
        "groups": [],
        "users": []
      }
    }
  ]
}
```

## Config field explanations

| Field | Purpose |
|---|---|
| `targetOrgUrl` | Target Okta org where apps will be created. Can also come from `.env`. |
| `outputDir` | Folder where execution output is written. |
| `createAssignments` | If true, applies configured group/user assignments after app creation. |
| `skipExisting` | If true, skips apps with matching labels in the target org. |
| `failFast` | If true, stops on first failed app. |
| `applications` | List of OIDC apps to create. |
| `label` | App display name in Okta. |
| `applicationType` | OIDC app type, such as `web`, `browser`, `native`, or `service`. |
| `grantTypes` | OAuth grant types. |
| `responseTypes` | OIDC response types. |
| `redirectUris` | Allowed sign-in redirect URIs. |
| `postLogoutRedirectUris` | Allowed sign-out redirect URIs. |
| `loginUri` | Deprecated/ignored. The utility does not emit `settings.oauthClient.login_uri`; use `initiateLoginUri` instead. |
| `initiateLoginUri` | URI used for app-initiated login. |
| `pkceRequired` | Whether PKCE is required. |
| `tokenEndpointAuthMethod` | Client authentication method, such as `client_secret_basic`, `client_secret_post`, or `none`. |
| `pkceRequired` placement | The utility writes `pkce_required` under `credentials.oauthClient` only when it is `true`. It omits false PKCE values to avoid unnecessary create-payload fields for confidential web apps. |
| `loginUri` handling | The utility does not emit `settings.oauthClient.login_uri`. Use `initiateLoginUri` instead. |
| `profile` handling | The utility includes a minimal `profile.label` object because Okta Apps API OIDC create examples include app profile metadata. |
| `consentMethod` | Consent behavior where supported. |
| `assignments.groups` | Group names to assign to the app. |
| `assignments.users` | User logins to assign to the app. |

## Run a dry run first

Dry-run mode builds the plan and performs read-only checks against the target org when credentials are available.

```bash
okta-oidc-app-create --config input/oidc-app.config.json --dry-run
```

Dry-run mode:

```text
Reads the config file
Builds app creation payloads
Checks whether an app label already exists
Checks assignment targets when createAssignments is true
Writes plan and report files
Does not create apps
Does not create assignments
```

## Review dry-run output

Each run creates a timestamped folder:

```text
output/okta-oidc-app-create-YYYYMMDDTHHMMSSZ/
```

Review:

```text
oidc_app_create_plan.json
oidc_app_create_result.json
execution_report.md
```

Confirm that the plan only includes the applications you intend to create.

## Apply the creation

After reviewing dry-run output, run:

```bash
okta-oidc-app-create --config input/oidc-app.config.json --apply
```

Apply mode can create applications in the target Okta org.

## Create only selected app labels

If the config contains multiple apps, you can target one or more labels:

```bash
okta-oidc-app-create   --config input/oidc-app.config.json   --labels "Customer Portal OIDC"   --dry-run
```

Apply:

```bash
okta-oidc-app-create   --config input/oidc-app.config.json   --labels "Customer Portal OIDC"   --apply
```

For multiple labels:

```bash
okta-oidc-app-create   --config input/oidc-app.config.json   --labels "Customer Portal OIDC,Admin Portal OIDC"   --dry-run
```

## Optional assignments

Assignments are disabled by default:

```json
"createAssignments": false
```

To enable assignments:

```json
"createAssignments": true
```

Then configure the app:

```json
"assignments": {
  "groups": ["Customer Portal Users"],
  "users": ["test.user@example.com"]
}
```

The utility resolves group names and user logins in the target org before assigning them.

## Rollback output

Apply mode creates a rollback plan:

```text
rollback_plan.json
```

The rollback plan records created app IDs and assignment actions. It is an evidence artifact for review. The utility does not automatically execute rollback.

## Generated outputs

Each run creates:

```text
output/okta-oidc-app-create-YYYYMMDDTHHMMSSZ/
  oidc_app_create_plan.json
  oidc_app_create_result.json
  rollback_plan.json
  app_mapping.csv
  execution_report.md
```

## Recommended workflow

```bash
cd 11-okta-oidc-app-create

python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .

cp .env.example .env
cp config.example.json input/oidc-app.config.json

# Edit .env and input/oidc-app.config.json.

okta-oidc-app-create --config input/oidc-app.config.json --dry-run

# Review output/.../execution_report.md and oidc_app_create_plan.json.

okta-oidc-app-create --config input/oidc-app.config.json --apply
```

## Troubleshooting

### `Invalid token provided`

Usually means the API token is wrong, revoked, copied incorrectly, or belongs to a different Okta org.

### `403 Forbidden`

The token works, but the admin account does not have enough permission to create apps or assignments.

### `App already exists`

The target org already has an app with the same label. If `skipExisting` is true, the utility skips it.

### `Group not found`

A configured assignment group does not exist in the target org.

### `User not found`

A configured assignment user login does not exist in the target org.

## Development

Install test dependencies:

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

