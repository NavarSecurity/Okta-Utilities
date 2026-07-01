# WARNING

These utilities have limited testing and are provided as-is with no warranty. Use at your own risk.

# 06-okta-terraform-import-generator

`okta-terraform-import-generator` generates Terraform import commands and Terraform `import` blocks from an Okta configuration backup folder.

The utility is intended to help bring existing Okta resources under Terraform management by producing repeatable import artifacts from backup data created by `01-okta-config-backup`.

## What this utility does

This utility reads local Okta backup JSON files and generates:

- `terraform_imports.sh` with `terraform import` commands
- `imports.tf` with Terraform import blocks
- `terraform_import_plan.json` with machine-readable import records
- `resource_mapping.csv` with source object to Terraform address mappings
- `unsupported_resources.csv` for objects that could not be mapped automatically
- `import_summary.md` and `execution_report.md` for review evidence

It does **not** connect to Okta.

It does **not** call Terraform.

It does **not** create, update, or delete Okta objects.

It only reads backup files and writes local planning artifacts.

## Why this utility exists

Terraform can only manage existing resources after they are imported into Terraform state. In an existing Okta org, object IDs must be mapped to Terraform resource addresses before `terraform import` can be run.

This utility automates the repetitive work of turning exported Okta backup objects into import commands and import blocks.

Example output:

```bash
terraform import okta_group.source_admins 00gsourceadmins
terraform import okta_app_oauth.customer_portal_oidc 0oasourceapp1
```

Example import block:

```hcl
import {
  to = okta_group.source_admins
  id = "00gsourceadmins"
}
```

## Supported resource categories

The first version supports import generation for:

- `groups`
- `applications`
- `trusted_origins`
- `network_zones`
- `authorization_servers`
- `authorization_server_scopes`
- `authorization_server_claims`
- `authorization_server_policies`
- `authorization_server_policy_rules`
- `policies`
- `identity_providers`

Some app types, IdP types, policy types, or provider resources may require manual review or custom mappings.

## Folder structure

Expected structure:

```text
06-okta-terraform-import-generator/
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
  tests/
```

The `input/source-backup/` folder is provided as a convenience location. You can either copy a backup into that folder or point directly to an external backup folder with `--backup-dir`.

## Prerequisites

You need:

```text
Python 3.10+
A backup folder created by 01-okta-config-backup
```

You do **not** need:

```text
Okta API token
Okta admin access
Network access to Okta
Terraform credentials just to generate the files
```

You only need Terraform later if you decide to run the generated imports.

## Installation

From inside the `06-okta-terraform-import-generator` folder, create a virtual environment.

### macOS / Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### Windows PowerShell

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Install the utility:

```bash
python -m pip install --upgrade pip
python -m pip install -e .
```

Confirm the command works:

```bash
okta-terraform-import-generator --help
```

## Prepare a backup folder

Use a backup folder from `01-okta-config-backup`.

Example:

```text
../01-okta-config-backup/output/okta-config-backup-20260626T164507Z/
```

That folder may contain files such as:

```text
manifest.json
applications.json
groups.json
policies.json
identity_providers.json
authorization_servers.json
trusted_origins.json
network_zones.json
```

Recommended: run `05-okta-backup-validator` against the backup before generating Terraform import artifacts.

## Run with the included sample backup

To test the utility with sample data:

```bash
okta-terraform-import-generator --backup-dir samples/source-backup
```

Expected output:

```text
Terraform import generation complete: output/okta-terraform-imports-YYYYMMDDTHHMMSSZ
Imports generated: <count>
Unsupported objects: <count>
Status: WARN or PASS
```

`WARN` is normal if the sample includes unsupported or manually reviewed object types.

## Run against a real backup folder

```bash
okta-terraform-import-generator \
  --backup-dir ../01-okta-config-backup/output/<backup-folder>
```

Example with a path containing spaces:

```bash
okta-terraform-import-generator \
  --backup-dir "/Users/ravikumar/Cayden's Projects/Okta Projects/01-okta-config-backup/output/okta-config-backup-20260626T164507Z"
```

## Use a config file

Copy the example config:

### macOS / Linux

```bash
cp config.example.json input/import-generator.config.json
```

### Windows PowerShell

```powershell
Copy-Item config.example.json input/import-generator.config.json
```

Edit:

```text
input/import-generator.config.json
```

Example:

```json
{
  "backupDir": "../01-okta-config-backup/output/okta-config-backup-20260626T164507Z",
  "outputDir": "output",
  "include": [
    "groups",
    "applications",
    "trusted_origins",
    "network_zones",
    "authorization_servers",
    "policies",
    "identity_providers"
  ],
  "mode": "both",
  "modulePrefix": "",
  "resourceNamePrefix": "",
  "skipSystemObjects": false,
  "strictMode": false
}
```

Run:

```bash
okta-terraform-import-generator --config input/import-generator.config.json
```

## Output modes

The utility supports three output modes.

### Commands only

```bash
okta-terraform-import-generator --backup-dir ../backups/source --mode commands
```

Creates:

```text
terraform_imports.sh
```

### Import blocks only

```bash
okta-terraform-import-generator --backup-dir ../backups/source --mode blocks
```

Creates:

```text
imports.tf
```

### Both

```bash
okta-terraform-import-generator --backup-dir ../backups/source --mode both
```

Creates both:

```text
terraform_imports.sh
imports.tf
```

## Include only selected resources

To generate imports only for groups and applications:

```bash
okta-terraform-import-generator \
  --backup-dir ../backups/source \
  --include groups,applications
```

To generate only group imports:

```bash
okta-terraform-import-generator \
  --backup-dir ../backups/source \
  --include groups
```

## Module prefix support

If your Okta Terraform resources live inside a module, use `--module-prefix`.

Example:

```bash
okta-terraform-import-generator \
  --backup-dir ../backups/source \
  --module-prefix module.okta
```

Generated command example:

```bash
terraform import module.okta.okta_group.source_admins 00gsourceadmins
```

## Resource name prefix support

To add a prefix to generated Terraform resource names:

```bash
okta-terraform-import-generator \
  --backup-dir ../backups/source \
  --resource-name-prefix imported_
```

Example resource address:

```text
okta_group.imported_source_admins
```

## Generated files

Each run creates a timestamped folder:

```text
output/okta-terraform-imports-YYYYMMDDTHHMMSSZ/
```

Common output files:

```text
terraform_import_plan.json
terraform_imports.sh
imports.tf
resource_mapping.csv
unsupported_resources.csv
import_summary.md
execution_report.md
```

### `terraform_imports.sh`

Shell script containing generated `terraform import` commands.

Review this file before running it.

### `imports.tf`

Terraform import blocks that can be copied into a Terraform project using supported Terraform versions.

Review this file before using it.

### `resource_mapping.csv`

Maps Okta backup objects to generated Terraform addresses.

Useful for review and handoff.

### `unsupported_resources.csv`

Lists objects that could not be mapped automatically.

Common reasons include:

- Unsupported Okta app type
- Unsupported IdP type
- Unsupported policy type
- Missing object ID
- Provider resource mapping not configured

### `terraform_import_plan.json`

Full machine-readable output containing all generated imports, unsupported objects, warnings, and metadata.

## Resource mapping behavior

The utility uses default mappings for common Okta resource types.

Examples:

| Okta object | Terraform type |
|---|---|
| Group | `okta_group` |
| OIDC app | `okta_app_oauth` |
| SAML app | `okta_app_saml` |
| Bookmark app | `okta_app_bookmark` |
| Trusted origin | `okta_trusted_origin` |
| Network zone | `okta_network_zone` |
| Authorization server | `okta_auth_server` |
| Authorization server scope | `okta_auth_server_scope` |
| Authorization server claim | `okta_auth_server_claim` |
| SAML IdP | `okta_idp_saml` |
| OIDC IdP | `okta_idp_oidc` |

Review and adjust these mappings for your Terraform provider version and internal standards.

## Custom mappings

You can add or override mappings in the config file.

Example:

```json
{
  "appResourceMappings": {
    "oidc_client": "okta_app_oauth",
    "saml2": "okta_app_saml",
    "bookmark": "okta_app_bookmark"
  },
  "idpResourceMappings": {
    "SAML2": "okta_idp_saml",
    "OIDC": "okta_idp_oidc"
  },
  "policyResourceMappings": {
    "OKTA_SIGN_ON": "okta_policy_signon",
    "PASSWORD": "okta_policy_password"
  }
}
```

## Important limitations

This utility generates import artifacts only. It does not generate full `.tf` configuration for each resource.

A typical Terraform adoption workflow is:

```text
1. Generate import commands or import blocks.
2. Create matching Terraform HCL resource definitions.
3. Run Terraform import.
4. Run terraform plan.
5. Reconcile HCL until the plan is clean.
```

Utility `07-okta-hcl-generator` is intended to help with starter HCL generation later.

## Recommended workflow

```bash
# 1. Create a backup.
cd 01-okta-config-backup
okta-config-backup --config input/config.json

# 2. Validate the backup.
cd ../05-okta-backup-validator
okta-backup-validator --backup-dir ../01-okta-config-backup/output/<backup-folder> --strict

# 3. Generate Terraform import artifacts.
cd ../06-okta-terraform-import-generator
okta-terraform-import-generator \
  --backup-dir ../01-okta-config-backup/output/<backup-folder> \
  --mode both

# 4. Review generated files.
open output/okta-terraform-imports-*/import_summary.md
```

## Running generated imports

Before running `terraform_imports.sh`:

- Confirm your Terraform provider configuration points to the correct Okta org.
- Confirm matching `.tf` resource blocks exist or will be created.
- Review the generated Terraform addresses.
- Review unsupported resources.
- Test in a non-production Terraform workspace first.

If approved:

```bash
cd /path/to/terraform/project
bash /path/to/06-okta-terraform-import-generator/output/<run-folder>/terraform_imports.sh
```

## Exit codes

| Exit code | Meaning |
|---:|---|
| `0` | Import artifacts generated successfully. |
| `1` | Generation completed but strict mode failed or blocking issues were found. |
| `2` | Runtime or configuration error. |

## Development

Install test dependencies:

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
