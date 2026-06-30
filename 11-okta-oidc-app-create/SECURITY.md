# Security Notes

This utility can create applications and optional assignments in a target Okta org.

## Secret handling

- Do not commit `.env` files.
- Do not commit API tokens.
- Do not paste real client secrets into tickets, chat, or Git history.
- Treat execution output as sensitive because it may contain app names, URIs, group names, and target org metadata.

## Operational safety

- Run dry-run mode before apply mode.
- Test in a non-production Okta org first.
- Review generated payloads before applying.
- Use a dedicated service/admin account for API tokens when possible.
- Use the least privilege required for app creation and assignment work.

## Git safety

The included `.gitignore` excludes `.env`, `.venv`, runtime output, and local input files.
