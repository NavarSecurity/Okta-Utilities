# 07-okta-hcl-generator

`okta-hcl-generator` creates starter Terraform HCL files from an Okta configuration backup created by `01-okta-config-backup`.

It is intended to help engineers begin converting existing Okta configuration into Terraform-managed code. It does **not** call Okta, does **not** change any Okta org, and does **not** guarantee production-ready Terraform. It generates starter HCL that must be reviewed before use.

## Purpose

Use this utility when you need to:

- Generate starter Terraform files from an Okta backup
- Create Terraform resource stubs for groups, apps, trusted origins, network zones, and authorization servers
- Generate import suggestions alongside starter HCL
- Create object-to-Terraform resource mapping evidence
- Identify objects that need manual Terraform review
- Prepare for a future Terraform migration or infrastructure-as-code effort

## Supported resources

This first version supports starter HCL for:

- `groups`
- `applications` for OIDC and SAML starter resources
- `trusted_origins`
- `network_zones`
- `authorization_servers`
- `authorization_server_scopes`
- `authorization_server_claims`

It flags these for manual review instead of fully generating HCL:

- `policies`
- `identity_providers`
- authorization server policies and rules
- unsupported application types

Those objects can affect authentication behavior, federation trust, policy priority, secrets, certificates, or access decisions, so they should not be blindly converted into Terraform without review.

## What this utility does not do

This utility does **not**:

- Connect to Okta
- Create, update, delete, or import anything
- Run `terraform import`
- Run `terraform plan` or `terraform apply`
- Generate final production-ready Terraform for every object type
- Recreate secrets, certificates, app assignments, provisioning settings, or policy behavior automatically

## Folder structure

```text
07-okta-hcl-generator/
  README.md
  SECURITY.md
  config.example.json
  pyproject.toml
  requirements.txt
  requirements-dev.txt
  src/
  input/
    source-backup/
  output/
  samples/
    source-backup/
  tests/
```

## Prerequisites

You need:

```text
Python 3.10+
A local backup folder created by 01-okta-config-backup
```

You do not need:

```text
Okta API token
Okta admin access
Network access to Okta
Terraform installed just to generate files
```

Terraform is only needed later if you plan to validate or apply the generated HCL.

## Installation

From inside the `07-okta-hcl-generator` folder:

### macOS / Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .
```

### Windows PowerShell

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e .
```

Confirm the command works:

```bash
okta-hcl-generator --help
```

## Prepare a backup folder

This utility expects a backup folder from `01-okta-config-backup`.

Example:

```text
../01-okta-config-backup/output/okta-config-backup-20260626T164507Z/
```

That folder may contain:

```text
manifest.json
applications.json
groups.json
trusted_origins.json
network_zones.json
authorization_servers.json
policies.json
identity_providers.json
```

You can either copy backup files into:

```text
input/source-backup/
```

or pass the backup path directly with `--backup-dir`.

## Basic usage

Run against the default `input/source-backup` folder:

```bash
okta-hcl-generator --config config.example.json
```

Or point directly to a backup folder:

```bash
okta-hcl-generator \
  --backup-dir ../01-okta-config-backup/output/<backup-folder>
```

If your path has spaces, wrap it in quotes:

```bash
okta-hcl-generator \
  --backup-dir "/Users/name/Projects/Okta Projects/01-okta-config-backup/output/<backup-folder>"
```

## Generate only selected resources

Applications and groups only:

```bash
okta-hcl-generator \
  --backup-dir ../01-okta-config-backup/output/<backup-folder> \
  --include applications,groups
```

Groups only:

```bash
okta-hcl-generator \
  --backup-dir ../01-okta-config-backup/output/<backup-folder> \
  --include groups
```

Authorization servers, scopes, and claims:

```bash
okta-hcl-generator \
  --backup-dir ../01-okta-config-backup/output/<backup-folder> \
  --include authorization_servers,authorization_server_scopes,authorization_server_claims
```

## Use a working config file

Copy the example config:

```bash
cp config.example.json input/hcl.config.json
```

Windows PowerShell:

```powershell
Copy-Item config.example.json input/hcl.config.json
```

Edit:

```text
input/hcl.config.json
```

Example:

```json
{
  "backupDir": "../01-okta-config-backup/output/<backup-folder>",
  "outputDir": "output",
  "include": [
    "groups",
    "applications",
    "trusted_origins",
    "network_zones",
    "authorization_servers",
    "authorization_server_scopes",
    "authorization_server_claims",
    "policies",
    "identity_providers"
  ],
  "resourceNamePrefix": "okta",
  "providerVersionConstraint": "~> 4.0",
  "generateImportSuggestions": true,
  "writeMarkdown": true,
  "strictMode": false
}
```

Then run:

```bash
okta-hcl-generator --config input/hcl.config.json
```

## Config fields

| Field | Purpose |
|---|---|
| `backupDir` | Backup folder to read. |
| `outputDir` | Folder where generated HCL output is written. |
| `include` | Resource types to generate. |
| `resourceNamePrefix` | Prefix for Terraform resource names. |
| `providerVersionConstraint` | Okta Terraform provider version constraint. |
| `generateImportSuggestions` | Writes `terraform_imports.sh` and `imports.tf`. |
| `writeMarkdown` | Writes Markdown reports. |
| `strictMode` | Returns failure if missing files or unsupported resources are found. |

## Output files

Each run creates a timestamped output folder:

```text
output/okta-hcl-YYYYMMDDTHHMMSSZ/
```

Generated files may include:

```text
providers.tf
variables.tf
outputs.tf
groups.tf
applications.tf
trusted_origins.tf
network_zones.tf
authorization_servers.tf
authorization_server_scopes.tf
authorization_server_claims.tf
terraform_imports.sh
imports.tf
resource_mapping.csv
unsupported_resources.csv
manual_review_items.csv
hcl_generation_plan.json
hcl_generation_report.md
execution_report.md
```

## How to use the generated Terraform files

The generated `.tf` files are starter files. Review and edit them before using them in a real Terraform workspace.

Recommended flow:

```text
1. Generate HCL from a known-good backup.
2. Review hcl_generation_report.md.
3. Review manual_review_items.csv.
4. Review every generated .tf file.
5. Copy the generated .tf files into a Terraform workspace.
6. Run terraform fmt.
7. Run terraform validate.
8. Import existing resources if appropriate.
9. Run terraform plan.
10. Resolve drift before any apply.
```

## Import suggestions

The utility writes two import helper files when enabled:

```text
terraform_imports.sh
imports.tf
```

These are suggestions only. Review them before running.

Example import command:

```bash
terraform import okta_group.okta_group_sales_users 00gabc123
```

Example import block:

```hcl
import {
  to = okta_group.okta_group_sales_users
  id = "00gabc123"
}
```

## Important limitations

Generated HCL may need manual correction. Okta backup JSON and Terraform provider schema do not always map one-to-one.

Pay special attention to:

- App credentials and generated secrets
- OIDC grant types and redirect URIs
- SAML signing and certificate behavior
- App assignments
- Provisioning settings
- Policy rules and priorities
- Identity provider secrets and certificates
- Authorization server policy rules
- Group references
- Network zone behavior

## Recommended workflow with other utilities

```text
1. Run 01-okta-config-backup.
2. Run 05-okta-backup-validator.
3. Optionally run 03-okta-org-inventory-exporter.
4. Run 06-okta-terraform-import-generator if you only need import commands.
5. Run 07-okta-hcl-generator to create starter HCL.
6. Review generated HCL manually.
7. Use Terraform tooling to validate, import, and plan.
```

## Troubleshooting

### `Backup directory not found`

The backup path is wrong. Use quotes if the path contains spaces.

```bash
okta-hcl-generator --backup-dir "/full/path/to/backup-folder"
```

### `Backup file not found`

You included a resource type but the related JSON file is missing from the backup.

Example:

```text
authorization_servers.json missing
```

Rerun `01-okta-config-backup` with that resource included, or remove that resource from `include`.

### Unsupported application type

The utility only generates starter HCL for common OIDC and SAML app shapes in this version. Unsupported apps are written to:

```text
unsupported_resources.csv
```

### Policies appear in manual review

This is expected. Policies can affect authentication and access behavior, so this version does not blindly generate policy HCL.

## Development

Install dev dependencies:

```bash
python -m pip install -r requirements-dev.txt
```

Run tests:

```bash
pytest
```

Run syntax validation:

```bash
python -m compileall src tests
```

## Disclaimer

WARNING: These utilities have limited testing and are provided as-is with no warranty. Use at your own risk.
