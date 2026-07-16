# WARNING

These utilities have limited testing and are provided as-is with no warranty. Use at your own risk.

# okta-scim-provisioning-tester

Python utility for testing downstream SCIM provisioning behavior.

This utility is intended for Okta SCIM integration testing, private SCIM connector validation, client onboarding support, and provisioning troubleshooting. It can test the SCIM operations commonly used during Okta provisioning flows, including user create, user update, user deactivate, group create, and group membership push.

---

## What This Utility Does

The `okta-scim-provisioning-tester` utility supports two main operations:

| Operation | Purpose |
|---|---|
| `discovery` | Test read-only SCIM discovery endpoints such as `ServiceProviderConfig`, `Schemas`, and `ResourceTypes`. |
| `test` | Test downstream SCIM provisioning behavior for users and groups. |

This utility sends requests directly to a downstream SCIM service. It does not create an Okta app integration and does not modify Okta configuration.

---

## Safety Model

This utility is designed to be conservative.

Dry-run mode writes a planned operation report and does not send SCIM requests.

```bash
okta-scim-provisioning-tester --config config.json --dry-run
```

Discovery mode is read-only, but it still sends HTTP requests when executed without `--dry-run`.

```bash
okta-scim-provisioning-tester --config config.json --operation discovery --apply
```

Provisioning test mode can create, update, deactivate, and optionally delete test users and groups in the downstream SCIM service. Use dry-run first.

```bash
okta-scim-provisioning-tester --config config.json --operation test --dry-run
okta-scim-provisioning-tester --config config.json --operation test --apply
```

The utility should not send mutating SCIM requests unless `--apply` is provided.

---

## Folder Structure

```text
40-okta-scim-provisioning-tester/
  README.md
  pyproject.toml
  .env.example
  .gitignore
  config.example.json
  src/
    okta_scim_provisioning_tester/
      __init__.py
      __main__.py
      cli.py
      config.py
      scim_client.py
      planner.py
      payloads.py
      operations.py
      redact.py
      reports.py
  samples/
    config.test.sample.json
    config.discovery.sample.json
    scim_test_plan.sample.json
  tests/
    test_config.py
    test_payloads.py
    test_planner.py
    test_redact.py
    test_scim_client.py
  input/
    .gitkeep
    scim_test_plan.json
  output/
    .gitkeep
```

---

## Requirements

- Python 3.10 or newer
- Network access to the downstream SCIM service
- SCIM base URL
- SCIM authentication credential, usually bearer token or basic authentication

This utility tests a SCIM service endpoint. The SCIM service may be a vendor app, internal application, mock SCIM server, or private SCIM connector backend.

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

Copy the test configuration:

```bash
cp samples/config.test.sample.json config.json
```

Copy the sample SCIM test plan:

```bash
cp samples/scim_test_plan.sample.json input/scim_test_plan.json
```

Open `.env` and update the SCIM values.

---

## Environment Variables

Create a `.env` file using `.env.example`.

Bearer token example:

```env
SCIM_BASE_URL=https://scim.example.com/scim/v2
SCIM_AUTH_TYPE=bearer
SCIM_BEARER_TOKEN=replace-with-scim-bearer-token
```

Basic authentication example:

```env
SCIM_BASE_URL=https://scim.example.com/scim/v2
SCIM_AUTH_TYPE=basic
SCIM_BASIC_USERNAME=replace-with-basic-username
SCIM_BASIC_PASSWORD=replace-with-basic-password
```

No authentication example for a local mock SCIM service:

```env
SCIM_BASE_URL=http://localhost:8080/scim/v2
SCIM_AUTH_TYPE=none
```

Do not commit `.env` files.

The `.gitignore` file should exclude:

```text
.env
.venv/
output/*
!output/.gitkeep
```

---

## Configuration

The utility is driven by `config.json`.

Example test configuration:

```json
{
  "operation": "test",
  "outputDirectory": "output",
  "planFile": "input/scim_test_plan.json",
  "baseUrlEnv": "SCIM_BASE_URL",
  "authTypeEnv": "SCIM_AUTH_TYPE",
  "timeoutSeconds": 30,
  "verifySsl": true,
  "continueOnError": true,
  "redactSensitiveValues": true,
  "operations": {
    "serviceProviderConfig": true,
    "schemas": true,
    "resourceTypes": true,
    "createUser": true,
    "updateUser": true,
    "deactivateUser": true,
    "createGroup": true,
    "groupPush": true,
    "cleanup": false
  },
  "cleanup": {
    "deleteUserAfterTest": false,
    "deleteGroupAfterTest": false
  }
}
```

Example discovery-only configuration:

```json
{
  "operation": "discovery",
  "outputDirectory": "output",
  "planFile": "input/scim_test_plan.json",
  "baseUrlEnv": "SCIM_BASE_URL",
  "authTypeEnv": "SCIM_AUTH_TYPE",
  "timeoutSeconds": 30,
  "verifySsl": true,
  "continueOnError": true,
  "redactSensitiveValues": true,
  "operations": {
    "serviceProviderConfig": true,
    "schemas": true,
    "resourceTypes": true,
    "createUser": false,
    "updateUser": false,
    "deactivateUser": false,
    "createGroup": false,
    "groupPush": false,
    "cleanup": false
  }
}
```

---

## SCIM Test Plan

The test plan controls the test user, update values, and group used by the provisioning test.

Example `input/scim_test_plan.json`:

```json
{
  "testUser": {
    "schemas": [
      "urn:ietf:params:scim:schemas:core:2.0:User"
    ],
    "userName": "utility40.scim.test@example.com",
    "externalId": "utility40-test-user-001",
    "name": {
      "givenName": "Utility40",
      "familyName": "SCIMTest"
    },
    "displayName": "Utility40 SCIM Test",
    "emails": [
      {
        "value": "utility40.scim.test@example.com",
        "type": "work",
        "primary": true
      }
    ],
    "active": true
  },
  "updateUser": {
    "name.givenName": "Utility40Updated",
    "title": "Updated by utility 40",
    "department": "IAM Test"
  },
  "group": {
    "schemas": [
      "urn:ietf:params:scim:schemas:core:2.0:Group"
    ],
    "displayName": "Utility40 SCIM Test Group",
    "externalId": "utility40-test-group-001"
  },
  "cleanup": {
    "deleteUserAfterTest": false,
    "deleteGroupAfterTest": false
  }
}
```

Use a clearly identifiable test user and test group. Do not use a real employee account for SCIM testing.

---

## Operation: Dry Run

Use dry run to verify the planned SCIM requests before sending anything to the downstream SCIM service.

```bash
okta-scim-provisioning-tester --config config.json --dry-run
```

Expected output:

```text
output/scim-provisioning-dry-run-<timestamp>/
  planned_operations.json
  config_summary.json
  execution_report.json
  manifest.json
```

Dry run does not send HTTP requests.

---

## Operation: Discovery

Use discovery mode to test the read-only SCIM discovery endpoints.

```bash
cp samples/config.discovery.sample.json config.json
okta-scim-provisioning-tester --config config.json --operation discovery --apply
```

Typical SCIM discovery requests:

```text
GET /ServiceProviderConfig
GET /Schemas
GET /ResourceTypes
```

Expected output:

```text
output/scim-provisioning-discovery-<timestamp>/
  operation_results.json
  operation_results.csv
  scim_responses.json
  execution_report.json
  manifest.json
```

Discovery mode is useful before testing provisioning because it verifies that the SCIM base URL, authentication, and core SCIM metadata endpoints are reachable.

---

## Operation: Provisioning Test

Use provisioning test mode to validate downstream behavior for user and group operations.

Run a dry run first:

```bash
cp samples/config.test.sample.json config.json
cp samples/scim_test_plan.sample.json input/scim_test_plan.json
okta-scim-provisioning-tester --config config.json --operation test --dry-run
```

Apply the test only after reviewing the dry-run output:

```bash
okta-scim-provisioning-tester --config config.json --operation test --apply
```

Typical provisioning test requests:

```text
POST /Users
PATCH /Users/{userId}
PATCH /Users/{userId} with active=false
POST /Groups
PATCH /Groups/{groupId} to add the test user as a member
```

Expected output:

```text
output/scim-provisioning-test-<timestamp>/
  operation_results.json
  operation_results.csv
  scim_responses.json
  execution_report.json
  manifest.json
```

---

## Cleanup Behavior

Cleanup is disabled by default.

```json
{
  "operations": {
    "cleanup": false
  },
  "cleanup": {
    "deleteUserAfterTest": false,
    "deleteGroupAfterTest": false
  }
}
```

Some SCIM services do not support hard delete. Many real provisioning flows deactivate users instead of deleting them. Review the target SCIM service behavior before enabling cleanup.

To include cleanup operations in the test plan, update the config intentionally:

```json
{
  "operations": {
    "cleanup": true
  }
}
```

---

## Output Reports

Each run creates timestamped output.

| File | Purpose |
|---|---|
| `planned_operations.json` | Dry-run preview of SCIM requests that would be sent. |
| `config_summary.json` | Dry-run summary of config and enabled operations. |
| `operation_results.json` | Structured result for each SCIM request. |
| `operation_results.csv` | Flat request result summary for review. |
| `scim_responses.json` | Raw SCIM responses, redacted where configured. |
| `execution_report.json` | Run status, counts, failures, and captured SCIM IDs. |
| `manifest.json` | Operation, config path, timestamp, and generated file list. |

Execution reports should not include bearer tokens, passwords, or authorization headers.

---

## Recommended Workflow

For client work, use this sequence:

```bash
cp samples/config.discovery.sample.json config.json
okta-scim-provisioning-tester --config config.json --operation discovery --dry-run
```

After reviewing the discovery dry run:

```bash
okta-scim-provisioning-tester --config config.json --operation discovery --apply
```

Then prepare a test plan:

```bash
cp samples/config.test.sample.json config.json
cp samples/scim_test_plan.sample.json input/scim_test_plan.json
```

Open `input/scim_test_plan.json` and update the test user and test group values.

Run a provisioning dry run:

```bash
okta-scim-provisioning-tester --config config.json --operation test --dry-run
```

Apply the provisioning test:

```bash
okta-scim-provisioning-tester --config config.json --operation test --apply
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

Confirm the SCIM authentication values in `.env`.

```bash
cat .env
```

For bearer token authentication, confirm:

```text
SCIM_AUTH_TYPE=bearer
SCIM_BEARER_TOKEN=your-token
```

For basic authentication, confirm:

```text
SCIM_AUTH_TYPE=basic
SCIM_BASIC_USERNAME=your-username
SCIM_BASIC_PASSWORD=your-password
```

---

### 404 Not Found

Confirm the SCIM base URL.

The base URL should usually end at the SCIM version root:

```text
https://scim.example.com/scim/v2
```

Do not include `/Users`, `/Groups`, or `/ServiceProviderConfig` in `SCIM_BASE_URL`.

---

### 405 Method Not Allowed

The downstream SCIM service may not support the method being tested.

Examples:

```text
PATCH may not be supported for user updates.
DELETE may not be supported for cleanup.
Group PATCH may not be supported for group push.
```

Disable unsupported operations in `config.json` and rerun.

---

### 409 Conflict

The test user or group may already exist.

Use a unique `userName`, `externalId`, and `displayName` in `input/scim_test_plan.json`, or clean up the prior test object in the downstream service.

---

### TLS or certificate errors

If using a local development SCIM service with a self-signed certificate, either fix the certificate trust chain or temporarily set:

```json
{
  "verifySsl": false
}
```

Do not disable TLS verification for production testing unless the project has an approved exception.

---

## Security Notes

- Do not commit `.env`.
- Do not use real employee accounts for create, update, deactivate, or group push testing.
- Use unique test users and groups that are clearly identifiable.
- Treat SCIM responses as sensitive because they can contain user profile data.
- Review `scim_responses.json` before sharing it outside the project team.
- Run dry-run mode before any provisioning test.
- Avoid enabling cleanup unless the downstream SCIM service behavior is understood.

---

## Practical Use Cases

Use this utility to:

- Validate a private SCIM connector before connecting it to Okta.
- Test whether a downstream app supports SCIM user create, update, and deactivate.
- Test whether group creation and group membership push work correctly.
- Capture evidence during SCIM provisioning troubleshooting.
- Verify SCIM endpoint authentication and discovery metadata.
- Confirm whether a vendor SCIM endpoint behaves consistently with Okta provisioning expectations.
- Produce reusable evidence during IAM app onboarding work.

---

## Notes

This utility tests the downstream SCIM service directly. It does not replace end-to-end testing from the Okta Admin Console.

A successful utility run means the downstream SCIM endpoint responded successfully to the tested operations. It does not prove that the Okta app integration, app assignments, profile mappings, or group push settings are fully configured in Okta.
