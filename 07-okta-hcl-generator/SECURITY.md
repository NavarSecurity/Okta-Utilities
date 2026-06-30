# Security Notes

`okta-hcl-generator` does not call Okta and does not require an Okta API token. It reads local backup files and writes starter Terraform HCL.

Treat all backup files and generated Terraform output as sensitive because they can expose application labels, redirect URIs, issuer URLs, authorization server configuration, group names, policy names, network ranges, and other internal configuration details.

Do not commit raw backups, `.env` files, API tokens, client secrets, private keys, or unreviewed generated HCL.

Generated files are starter artifacts only. Review all generated Terraform before using it with `terraform import`, `terraform plan`, or `terraform apply`.

WARNING: These utilities have limited testing and are provided as-is with no warranty. Use at your own risk.
