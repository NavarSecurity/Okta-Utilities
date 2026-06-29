# Okta Org Diff Report

**Status:** `DIFFERENCES_FOUND`

**Generated:** `2026-06-29T19:32:31.590703+00:00`

**Baseline backup:** `samples/baseline-backup`

**Comparison backup:** `samples/comparison-backup`

## Summary

| Added | Removed | Changed | Unchanged | Duplicate Keys | Warnings | Errors |
| --- | --- | --- | --- | --- | --- | --- |
| 2 | 2 | 5 | 2 | 0 | 0 | 0 |

## Resource Summary

| Resource | Baseline | Comparison | Added | Removed | Changed | Dupes | Warnings | Errors |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| org | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 0 |
| applications | 2 | 2 | 1 | 1 | 1 | 0 | 0 | 0 |
| groups | 2 | 2 | 1 | 1 | 1 | 0 | 0 | 0 |
| group_rules | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| policies | 2 | 2 | 0 | 0 | 1 | 0 | 0 | 0 |
| identity_providers | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| authorization_servers | 1 | 1 | 0 | 0 | 1 | 0 | 0 | 0 |
| trusted_origins | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| network_zones | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| domains | 1 | 1 | 0 | 0 | 1 | 0 | 0 | 0 |
| brands | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| authenticators | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| event_hooks | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| inline_hooks | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |

## Changes

| Resource | Type | Key | Baseline ID | Comparison ID | Changed Paths | Message |
| --- | --- | --- | --- | --- | --- | --- |
| applications | added | New Admin App |  | 0oa3 |  |  |
| applications | removed | Legacy SAML App | 0oa2 |  |  |  |
| applications | changed | Customer Portal | 0oa1 | 0oa9 | $.settings.oauthClient.redirect_uris[length] |  |
| groups | added | Engineering Users |  | 00g3 |  |  |
| groups | removed | HR Users | 00g2 |  |  |  |
| groups | changed | Finance Users | 00g1 | 00g9 | $.profile.description |  |
| policies | changed | PASSWORD::Default Policy | 00p2 | 00p8 | $.settings.password.complexity.minLength |  |
| authorization_servers | changed | Default | aus1 | aus9 | $._details.detailsByAuthorizationServerId.scopes[length]; $.issuer |  |
| domains | changed | baseline.okta.com | default | default | $.brandId |  |

## Notes

This utility compares local backup files only. It does not connect to Okta and does not change either environment. Review generated differences before using the result for migration, restore, or cutover decisions.
