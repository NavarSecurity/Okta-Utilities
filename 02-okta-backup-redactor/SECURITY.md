# Security Notes

This utility is designed to reduce the chance of sensitive values being stored or shared in Okta backup files. It is not a substitute for manual security review.

## Handling output

- Treat source backups as sensitive.
- Treat redaction reports as sensitive if findings are present because they include value previews.
- Review `redaction_report.md` before sharing or committing output.
- Do not commit `.env`, API tokens, raw backup folders, private keys, or unreviewed reports.

## Redaction approach

The redactor uses exact secret-key matching and selected value-pattern detection. It intentionally avoids broad substring matching because that creates false positives and can break useful Okta configuration structures.

## Recommended usage

Run the utility in dry-run mode first, review the report, then use `--apply` to create a separate redacted copy. The source backup folder is never modified.
