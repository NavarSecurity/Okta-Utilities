# WARNING

These utilities have limited testing and are provided as-is with no warranty. Use at your own risk.

# 12-okta-saml-app-create

`okta-saml-app-create` creates Okta SAML 2.0 application integrations from a JSON configuration file. It is intended for repeatable application onboarding work where SAML settings such as ACS URL, audience, recipient, destination, NameID, signing options, and attribute statements need to be captured and applied consistently.

The utility is designed with a safety-first workflow:

```text
1. Write or copy a SAML app config.
2. Run dry-run mode to review the generated payload.
3. Review the generated plan and execution report.
4. Run apply mode only after the payload is approved.
5. Review rollback and evidence output.
```


## Payload compatibility note

This utility intentionally does not emit a SAML catalog/template `name` such as `template_saml_2_0` in the create-app payload. Some Okta orgs reject that value with `Resource not found: template_saml_2_0 (App)`. The generated payload relies on `signOnMode: SAML_2_0`, `profile.label`, and `settings.signOn` instead.

The generated payload also includes Okta app object sections that custom SAML app creation commonly requires: `visibility`, `accessibility`, and `credentials.userNameTemplate`. These defaults prevent validation errors such as `Missing visibility` while keeping the app visible in the web and iOS dashboards unless you explicitly hide it.

## What this utility does

This utility can:

- Build a SAML 2.0 app payload from JSON config
- Validate required SAML fields before calling Okta
- Check the target Okta org for an existing app with the same label
- Create the app only when `--apply` is explicitly used
- Optionally assign the new app to existing groups or users by ID
- Generate execution evidence and rollback planning output
- Keep source credentials and runtime output out of Git through `.gitignore`

## What this utility does not do

This utility does **not**:

- Create users or groups
- Create certificates
- Upload metadata XML
- Automatically validate the service provider endpoint
- Automatically test SAML login
- Automatically restore or delete apps
- Clone an existing app from another org
- Manage provisioning or SCIM settings

Use `10-okta-app-cloner` if your goal is to clone an app from a backup. Use this utility when you want to create a new SAML app from a clean config file.

## Folder structure

```text
12-okta-saml-app-create/
  README.md
  SECURITY.md
  .gitignore
  .env.example
  config.example.json
  pyproject.toml
  requirements.txt
  requirements-dev.txt
  src/okta_saml_app_create/
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
An Okta API token with permission to create apps and optional assignments
```

For testing, use a non-production Okta org.

## Install

From inside the `12-okta-saml-app-create` folder:

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

Confirm the command works:

```bash
okta-saml-app-create --help
```

## Configure target Okta access

Copy the environment example:

```bash
cp .env.example .env
```

Windows PowerShell:

```powershell
Copy-Item .env.example .env
```

Edit `.env`:

```text
OKTA_TARGET_ORG_URL=https://your-okta-org.okta.com
OKTA_TARGET_API_TOKEN=your_okta_api_token
```

Do not include `/admin`, `/api/v1`, or `/oauth2` in the org URL.

Do not include `SSWS` before the token. The utility adds that header automatically.

Correct:

```text
OKTA_TARGET_API_TOKEN=00abc123actualtoken
```

Incorrect:

```text
OKTA_TARGET_API_TOKEN=SSWS 00abc123actualtoken
```

## Create a SAML app config

Copy the example config:

```bash
cp config.example.json input/saml-app.config.json
```

Windows PowerShell:

```powershell
Copy-Item config.example.json input/saml-app.config.json
```

Edit:

```text
input/saml-app.config.json
```

Example config:

```json
{
  "targetOrgUrl": "https://your-okta-org.okta.com",
  "outputDir": "output",
  "skipExisting": true,
  "failFast": false,
  "pageLimit": 200,
  "timeoutSeconds": 30,
  "maxRetries": 4,
  "retryBaseSeconds": 1.0,
  "app": {
    "label": "Example SAML App",
    "defaultRelayState": "",
    "ssoAcsUrl": "https://app.example.com/saml/acs",
    "recipient": "https://app.example.com/saml/acs",
    "destination": "https://app.example.com/saml/acs",
    "audience": "https://app.example.com/saml/metadata",
    "subjectNameIdTemplate": "${user.email}",
    "subjectNameIdFormat": "urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress",
    "responseSigned": true,
    "assertionSigned": true,
    "signatureAlgorithm": "RSA_SHA256",
    "digestAlgorithm": "SHA256",
    "honorForceAuthn": false,
    "authnContextClassRef": "urn:oasis:names:tc:SAML:2.0:ac:classes:PasswordProtectedTransport",
    "visibility": {
      "autoSubmitToolbar": false,
      "hide": {
        "iOS": false,
        "web": false
      }
    },
    "accessibility": {
      "selfService": false,
      "errorRedirectUrl": null,
      "loginRedirectUrl": null
    },
    "userNameTemplate": {
      "template": "${source.login}",
      "type": "BUILT_IN"
    },
    "attributeStatements": [
      {
        "type": "EXPRESSION",
        "name": "email",
        "namespace": "urn:oasis:names:tc:SAML:2.0:attrname-format:unspecified",
        "values": [
          "user.email"
        ]
      }
    ],
    "assignments": {
      "groupIds": [],
      "userIds": []
    }
  }
}
```

## Config field explanations

| Field | Meaning |
|---|---|
| `targetOrgUrl` | Target Okta org where the app will be created. `.env` can override this. |
| `outputDir` | Folder where execution reports are written. |
| `skipExisting` | If true, skip app creation when an app with the same label already exists. |
| `label` | Display name of the SAML app in Okta. |
| `ssoAcsUrl` | Assertion Consumer Service URL from the service provider. |
| `recipient` | SAML recipient value. Often the ACS URL. |
| `destination` | SAML destination value. Often the ACS URL. |
| `audience` | SAML audience / entity ID expected by the service provider. |
| `defaultRelayState` | Optional relay state sent to the service provider. |
| `subjectNameIdTemplate` | Okta expression for the SAML NameID value. |
| `subjectNameIdFormat` | NameID format URI. |
| `responseSigned` | Whether the SAML response should be signed. |
| `assertionSigned` | Whether the SAML assertion should be signed. |
| `signatureAlgorithm` | Signing algorithm, such as `RSA_SHA256`. |
| `digestAlgorithm` | Digest algorithm, such as `SHA256`. |
| `honorForceAuthn` | Whether Okta should honor ForceAuthn requests. |
| `authnContextClassRef` | SAML authentication context class reference. |
| `visibility` | Dashboard visibility settings. Defaults keep the app visible on web and iOS. |
| `accessibility` | Self-service and optional redirect URL settings. Defaults match a controlled admin-created app. |
| `userNameTemplate` | Okta application username template. Defaults to `${source.login}` with `BUILT_IN` type. |
| `attributeStatements` | SAML attributes to include in assertions. |
| `assignments.groupIds` | Optional existing Okta group IDs to assign to the app. |
| `assignments.userIds` | Optional existing Okta user IDs to assign to the app. |

## Run dry-run first

Dry-run is the default mode, but it is best to be explicit:

```bash
okta-saml-app-create --config input/saml-app.config.json --dry-run
```

Dry-run mode:

```text
Validates config
Builds the Okta app payload
Checks for duplicate app labels in the target org
Writes plan and report files
Does not create the app
Does not assign groups or users
```

Generated output:

```text
output/okta-saml-app-create-YYYYMMDDTHHMMSSZ/
  saml_app_create_plan.json
  saml_app_create_result.json
  rollback_plan.json
  app_mapping.csv
  execution_report.md
```

Review `saml_app_create_plan.json` before applying.

## Apply app creation

Only run apply mode after reviewing dry-run output:

```bash
okta-saml-app-create --config input/saml-app.config.json --apply
```

Apply mode:

```text
Creates the SAML app in the target org
Optionally assigns groups or users if configured
Writes the created app ID to app_mapping.csv
Writes rollback planning output
Writes execution evidence
```

## Create an app without assignments

Set assignments to empty lists:

```json
"assignments": {
  "groupIds": [],
  "userIds": []
}
```

Then run:

```bash
okta-saml-app-create --config input/saml-app.config.json --dry-run
okta-saml-app-create --config input/saml-app.config.json --apply
```

## Create an app with group assignments

Use existing Okta group IDs:

```json
"assignments": {
  "groupIds": [
    "00gabc123example"
  ],
  "userIds": []
}
```

The utility does not create the group. The group must already exist in the target org.

## Create an app with user assignments

Use existing Okta user IDs:

```json
"assignments": {
  "groupIds": [],
  "userIds": [
    "00uabc123example"
  ]
}
```

The utility does not create the user. The user must already exist in the target org.

## Duplicate behavior

If `skipExisting` is true, the utility checks the target org for an existing app with the same label before creating anything.

If a match is found, the app is skipped and no new app is created.

```json
"skipExisting": true
```

If `skipExisting` is false and a duplicate label exists, the utility records an error instead of creating another app with the same label.

## Output files

Each run writes a timestamped folder under `output/`.

| File | Purpose |
|---|---|
| `saml_app_create_plan.json` | Planned app payload, duplicate check result, and assignment plan. |
| `saml_app_create_result.json` | Final execution result. |
| `rollback_plan.json` | Review artifact showing created app IDs and suggested delete action if rollback is approved. |
| `app_mapping.csv` | Maps requested app label to created or existing target app ID. |
| `execution_report.md` | Human-readable execution summary. |

## Rollback note

The utility does not automatically roll back changes.

If apply mode creates an app, the rollback plan records the created app ID and a suggested deletion action. Review and execute rollback manually through an approved process.

## Security notes

- Do not commit `.env` files.
- Do not commit API tokens.
- Treat output reports as internal delivery evidence.
- Test in a non-production Okta org before using in production.
- Review generated payloads before using `--apply`.

## Troubleshooting

### `Invalid token provided`

Common causes:

```text
Wrong token
Token belongs to a different Okta org
Token copied incorrectly
Token was revoked
Token includes the literal SSWS prefix in .env
Wrong target org URL
```

### `403 Forbidden`

The token works, but the admin account does not have permission to create apps or assign users/groups.

### `400 The request body was not well-formed`

The generated SAML payload is invalid for Okta. Check:

```text
ssoAcsUrl
recipient
destination
audience
subjectNameIdFormat
signatureAlgorithm
digestAlgorithm
attributeStatements
```

Review `saml_app_create_plan.json` to see the exact payload sent.

### App was skipped

If the app was skipped, check whether an app with the same label already exists in the target org and `skipExisting` is true.

### Assignment failed but app was created

The app creation and assignment steps are separate. If assignment fails, review `saml_app_create_result.json` and `execution_report.md`. The rollback plan should still identify the created app.

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
