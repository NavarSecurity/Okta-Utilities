# Security Notes

`okta-terraform-import-generator` is a local, read-only utility. It reads backup files from disk and generates Terraform import artifacts. It does not connect to Okta and does not require an Okta API token.

## Important handling guidance

- Treat raw Okta backup folders as sensitive configuration data.
- Do not commit `.env` files, API tokens, client secrets, private keys, or unreviewed backup output.
- Review generated `terraform_imports.sh`, `imports.tf`, and CSV mapping files before using them.
- Generated import artifacts can reveal internal object names, IDs, app labels, policy names, and environment structure.
- Test imports in a non-production Terraform workspace before using against production state.

## Recommended practice

Run `02-okta-backup-redactor` and `05-okta-backup-validator` before using backup files as input for this utility.

WARNING: These utilities have limited testing and are provided as-is with no warranty. Use at your own risk.
