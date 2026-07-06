# Security Notes

This utility is designed for read-only OAuth/OIDC testing. It can request tokens and introspect tokens, but it does not modify Okta configuration.

## Sensitive inputs

Do not commit or share:

- `.env`
- Client secrets
- Access tokens
- ID tokens
- Refresh tokens
- Authorization codes
- PKCE code verifiers
- Output reports from real environments unless reviewed

## Token handling

The utility redacts token values in reports and records token fingerprints for correlation. Decoded token claims may still contain sensitive identity or authorization information.

## Recommended usage

- Use a sandbox Okta org first
- Use test clients and test authorization servers
- Rotate secrets that were pasted into shared files
- Keep `.env` and generated output out of Git
