# Security Notes

`okta-org-diff` reads local Okta backup files and writes comparison reports. It does not connect to Okta and does not require an API token.

## Sensitive data handling

Backup files and generated diff reports may contain sensitive configuration details. Treat the following as sensitive unless reviewed and approved:

- Raw backup files
- Diff reports
- JSON output
- CSV output
- Execution reports

## Recommended controls

- Validate backups before diffing them.
- Redact backups before sharing or committing them.
- Do not commit `.env` files, raw credentials, tokens, private keys, or unreviewed backup output.
- Review generated reports before distribution.
- Use non-production data for testing when possible.

## Disclaimer

WARNING: These utilities have limited testing and are provided as-is with no warranty. Use at your own risk.
