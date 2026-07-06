# WARNING

These utilities have limited testing and are provided as-is with no warranty. Use at your own risk.

# 17-okta-token-tester

`okta-token-tester` is a read-only Okta OIDC/OAuth testing utility. It tests token flows and validates the tokens issued by Okta authorization servers.

It is intended for API onboarding, troubleshooting, migration validation, and post-change smoke testing.

## What this utility does

- Fetches OIDC discovery metadata from an Okta issuer
- Fetches JWKS signing keys
- Tests client credentials token issuance
- Optionally exchanges an authorization code for tokens
- Decodes and validates JWT access tokens or ID tokens
- Checks issuer, audience, scopes, required claims, expiration, and signature
- Runs token introspection tests
- Redacts tokens and secrets in output files
- Writes CSV, JSON, Markdown, and execution evidence output

## What this utility does not do

- It does not create authorization servers
- It does not create apps
- It does not create scopes, claims, policies, or rules
- It does not assign users or groups
- It does not modify Okta configuration

## Normal workflow

Use this utility after you create an OIDC app or API authorization server.

```text
Utility 11 or 15 creates the OIDC/API configuration
Utility 16 exports scopes and claims for review
Utility 17 tests token issuance and token contents
```

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .
```

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e .
```

## Configure environment values

Copy the example environment file:

```bash
cp .env.example .env
```

Edit `.env`:

```text
OKTA_ORG_URL=https://your-org.okta.com
OKTA_CLIENT_ID=your-client-id
OKTA_CLIENT_SECRET=your-client-secret
OKTA_ACCESS_TOKEN=
OKTA_ID_TOKEN=
```

Use the normal Okta org URL. Do not use the `-admin` Admin Console URL.

Correct:

```text
https://your-org.okta.com
```

Incorrect:

```text
https://your-org-admin.okta.com
https://your-org.okta.com/admin
https://your-org.okta.com/oauth2/default
```

## Configure the test file

Copy the sample config:

```bash
cp samples/token-test.sample.json input/token-test.config.json
```

Edit:

```text
input/token-test.config.json
```

Important fields:

```json
{
  "orgUrl": "https://your-org.okta.com",
  "authorizationServerId": "default",
  "client": {
    "clientId": "",
    "clientSecret": "",
    "tokenEndpointAuthMethod": "client_secret_basic"
  }
}
```

`authorizationServerId` controls the issuer tested by the utility.

Examples:

```text
default        -> https://your-org.okta.com/oauth2/default
aus123abc456  -> https://your-org.okta.com/oauth2/aus123abc456
org           -> https://your-org.okta.com
```

For custom API authorization servers, use `default` or the custom authorization server ID.

## Dry run

```bash
okta-token-tester --config input/token-test.config.json --dry-run
```

Dry run creates a plan and makes no Okta calls.

Review:

```text
output/okta-token-tester-<timestamp>/token_test_plan.json
output/okta-token-tester-<timestamp>/execution_report.md
```

## Run token tests

```bash
okta-token-tester --config input/token-test.config.json --test
```

The utility writes output to:

```text
output/okta-token-tester-<timestamp>/
```

Primary output files:

```text
token_test_result.json
token_test_report.md
discovery_metadata.json
jwks_summary.csv
token_claims_summary.csv
validation_findings.csv
execution_report.md
```

## Client credentials test

Use this when testing a machine-to-machine API client.

Example config:

```json
"clientCredentialsTests": [
  {
    "name": "Client Credentials Test",
    "scopes": ["read:example"],
    "expectedAudience": "api://example",
    "expectedScopes": ["read:example"]
  }
]
```

The utility calls:

```text
POST /oauth2/{authorizationServerId}/v1/token
```

with:

```text
grant_type=client_credentials
scope=read:example
```

Then it can validate the returned access token.

## JWT validation test

Use this to validate an access token or ID token.

Example:

```json
"jwtValidationTests": [
  {
    "name": "Validate Access Token",
    "tokenSource": "accessToken",
    "tokenType": "access",
    "expectedAudience": "api://example",
    "expectedScopes": ["read:example"],
    "requiredClaims": ["iss", "sub", "aud", "exp", "iat"],
    "verifySignature": true
  }
]
```

Token sources:

```text
accessToken
idToken
clientCredentialsAccessToken
authorizationCodeAccessToken
authorizationCodeIdToken
```

If `tokenSource` is `accessToken` and no token is pasted in `.env` or the config file, the utility now automatically uses the access token issued by a successful configured token flow, such as `clientCredentialsTests`. This lets the default workflow run token issuance, JWT validation, and introspection in one pass.

For pasted tokens, put them in `.env` using `OKTA_ACCESS_TOKEN` or `OKTA_ID_TOKEN`, or use token files referenced by config. Explicit pasted tokens take precedence over runtime-issued tokens.

## Introspection test

Use introspection to check whether a token is active according to Okta.

```json
"introspectionTests": [
  {
    "name": "Introspect Access Token",
    "tokenSource": "accessToken",
    "tokenTypeHint": "access_token",
    "expectedActive": true
  }
]
```

This requires a client ID and client secret that can authenticate to the introspection endpoint.

## Authorization code exchange

This utility can exchange an authorization code, but it does not drive a browser login. You must obtain the authorization code first from an Okta authorization redirect.

Example:

```json
"authorizationCodeTests": [
  {
    "name": "Authorization Code Exchange",
    "redirectUri": "https://app.example.com/callback",
    "authorizationCode": "",
    "codeVerifier": ""
  }
]
```

You can provide values through `.env`:

```text
OKTA_AUTHORIZATION_CODE=code-from-redirect
OKTA_CODE_VERIFIER=pkce-code-verifier
```

## Notes on secrets

The utility redacts tokens and client secrets from output. It writes token fingerprints instead of raw token values. Still, treat output files as sensitive because decoded token claims can contain user or environment information.

Do not commit `.env`, input files containing tokens, or output reports with sensitive claims.
