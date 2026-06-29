#!/usr/bin/env bash
set -euo pipefail

okta-selective-restore \
  --config input/restore.config.json \
  --dry-run
