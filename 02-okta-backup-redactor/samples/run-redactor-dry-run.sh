#!/usr/bin/env bash
set -euo pipefail
okta-backup-redactor --source-backup-dir samples/sample-backup-sensitive --dry-run
