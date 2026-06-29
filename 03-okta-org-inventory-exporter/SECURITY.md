# Security Notes

`okta-org-inventory-exporter` is a read-only local reporting utility. It reads backup files from disk and writes inventory reports. It does not call Okta APIs and does not require API tokens.

Backup files can still contain sensitive configuration details. Treat both source backups and generated inventory reports as internal engineering artifacts. Review generated CSV, JSON, and Markdown files before sharing or committing them.

Do not place `.env` files, API tokens, client secrets, private keys, raw customer exports, or unreviewed backup files in Git.
