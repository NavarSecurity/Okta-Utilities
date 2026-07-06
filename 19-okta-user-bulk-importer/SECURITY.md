# Security Notes

This utility can create and update Okta users. Treat it as a privileged administrative tool.

## Secrets

Use `.env` for local secrets and never commit it to source control.

Do not put Okta API tokens, passwords, or client secrets in Git.

## Import Files

CSV import files may contain personal data. Store them in approved locations only.

Avoid password import. The utility disables password import by default and redacts password-like values from output.

## Safer Execution Pattern

1. Run against a sandbox tenant first.
2. Run `--dry-run` before `--apply`.
3. Start with a small CSV.
4. Review `failed_users.csv`, `skipped_users.csv`, and `user_import_plan.json`.
5. Use staged user creation before activating users.
6. Review `rollback_plan.json` before performing any cleanup.
