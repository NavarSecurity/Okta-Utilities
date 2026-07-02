# WARNING

These utilities have limited testing and are provided as-is with no warranty. Use at your own risk.

# 15-okta-api-auth-server-builder

`okta-api-auth-server-builder` is a config-driven CLI utility for creating Okta custom API authorization servers and related OAuth/OIDC configuration objects.

It is designed for controlled Okta implementation work where API authorization servers, scopes, claims, access policies, and policy rules need to be created consistently across sandbox, staging, and production tenants.

## What this utility creates

The utility can create:

- Custom API authorization servers
- OAuth scopes
- Token claims
- Access policies
- Access policy rules

It does **not** create Okta applications, users, groups, app assignments, identity providers, domains, brands, or authenticators.

## Safety model

The utility is safe by default:

- `--dry-run` is the default behavior
- `--apply` is required before anything is created in Okta
- No delete operations are performed
- Existing objects are skipped by default
- Target org URLs using `-admin.okta.com` or `-admin.oktapreview.com` are rejected
- Output includes a rollback plan for created objects
- API tokens are read from `.env` or environment variables, not stored in config files

## Typical use cases

Use this utility when you need to:

- Build a custom authorization server for an API
- Standardize API scopes across Okta orgs
- Create token claims for API authorization decisions
- Create baseline OAuth access policies and rules
- Prepare an Okta tenant for API security testing
- Rebuild authorization server configuration during migration

## Folder structure

```text
15-okta-api-auth-server-builder/
  README.md
  SECURITY.md
  .gitignore
  .env.example
  config.example.json
  pyproject.toml
  requirements.txt
  requirements-dev.txt
  src/okta_api_auth_server_builder/
  input/
  output/
  samples/
  tests/
```

## Install

From inside the utility folder:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .
```

On Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e .
```

## Configure `.env`

Copy the example file:

```bash
cp .env.example .env
```

Update `.env`:

```bash
OKTA_TARGET_ORG_URL=https://your-org.okta.com
OKTA_API_TOKEN=your-okta-api-token
```

Use the normal Okta org URL. Do **not** use the Admin Console URL.

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

## Configure authorization server build file

Copy the sample config:

```bash
cp samples/api-auth-server.sample.json input/api-auth-server.config.json
```

Edit:

```text
input/api-auth-server.config.json
```

Minimal example:

```json
{
  "targetOrgUrl": "https://your-org.okta.com",
  "settings": {
    "skipExisting": true,
    "continueOnError": false
  },
  "authorizationServers": [
    {
      "name": "Example API Authorization Server",
      "description": "Authorization server for Example API.",
      "audiences": ["api://example"],
      "issuerMode": "ORG_URL",
      "status": "ACTIVE",
      "scopes": [
        {
          "name": "read:example",
          "description": "Read Example API data",
          "consent": "IMPLICIT",
          "metadataPublish": "ALL_CLIENTS",
          "default": false
        }
      ],
      "claims": [
        {
          "name": "email",
          "status": "ACTIVE",
          "claimType": "IDENTITY",
          "valueType": "EXPRESSION",
          "value": "user.email",
          "alwaysIncludeInToken": true,
          "conditions": {
            "scopes": ["openid"]
          }
        }
      ],
      "policies": [
        {
          "name": "Default API Access Policy",
          "description": "Default policy for API clients.",
          "priority": 1,
          "status": "ACTIVE",
          "clientWhitelist": ["ALL_CLIENTS"],
          "rules": [
            {
              "name": "Authorization Code Access",
              "priority": 1,
              "status": "ACTIVE",
              "grantTypeWhitelist": ["authorization_code"],
              "scopeWhitelist": ["read:example"],
              "accessTokenLifetimeMinutes": 60,
              "refreshTokenLifetimeMinutes": 10080,
              "refreshTokenWindowMinutes": 10080
            }
          ]
        }
      ]
    }
  ]
}
```

## Dry run

Run this first:

```bash
okta-api-auth-server-builder --config input/api-auth-server.config.json --dry-run
```

The dry run produces a plan and does not call any write endpoints.

## Apply

After reviewing the plan:

```bash
okta-api-auth-server-builder --config input/api-auth-server.config.json --apply
```

## Output files

Each run creates a timestamped folder under `output/`.

Typical outputs:

```text
authorization_server_plan.json
builder_result.json
created_authorization_servers.csv
created_scopes.csv
created_claims.csv
created_policies.csv
created_policy_rules.csv
skipped_items.csv
rollback_plan.json
execution_report.md
```

## Rollback plan

The utility creates `rollback_plan.json` with the delete endpoints for objects created during the run.

The utility does not automatically execute rollback because deleting authorization server objects can break API authentication and authorization flows. Review rollback steps manually before using them.

## Expected Okta permissions

The API token must be able to manage authorization servers and authorization server policies. In a sandbox, a Super Admin token is easiest for testing. In production, use a tightly controlled admin/service account with only the permissions needed for this operation.

## Important notes

- Custom authorization servers may require the appropriate Okta licensing in the target org.
- The built-in `default` authorization server may exist in some orgs, but this utility is for creating custom API authorization servers.
- OAuth policy rules can change token issuance behavior. Always test in a non-production org first.
- Use group/client-specific policies for production when possible instead of broad `ALL_CLIENTS` rules.

### Important grant type note

For authorization server access policy rules, do **not** put `refresh_token` in `grantTypeWhitelist`. Okta rejects `refresh_token` in `conditions.grantTypes.include`. Use `authorization_code` in `grantTypeWhitelist` and keep `refreshTokenLifetimeMinutes` / `refreshTokenWindowMinutes` when refresh token lifetime behavior is needed.

### Important people condition note

For authorization server access policy rules, `EVERYONE` must be used as a group condition value, not a user condition value.

Correct generated shape:

```json
"people": {
  "groups": {
    "include": ["EVERYONE"]
  },
  "users": {
    "include": []
  }
}
```

Incorrect shape:

```json
"people": {
  "users": {
    "include": ["EVERYONE"]
  }
}
```

Putting `EVERYONE` under `users.include` causes Okta to look for a user named `EVERYONE` and return `Resource(s) not found: EVERYONE (User)`.
