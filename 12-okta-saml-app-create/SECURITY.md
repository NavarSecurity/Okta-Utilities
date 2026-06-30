# Security Notes

This utility can create SAML applications in a target Okta org when `--apply` is used. Treat it as a mutation utility.

## Secret handling

Do not commit:

```text
.env
Okta API tokens
raw execution output from sensitive environments
client-owned configuration data without review
```

## Recommended practices

- Use a non-production Okta org for testing.
- Run dry-run before apply.
- Review generated payloads before apply.
- Use the least-privileged admin/service account that can create app integrations.
- Rotate exposed tokens immediately.
- Treat output reports as internal evidence.

## Mutation behavior

The utility can create:

```text
SAML applications
optional app-to-group assignments
optional app-to-user assignments
```

It does not automatically roll back created objects. Review `rollback_plan.json` before taking any rollback action.
