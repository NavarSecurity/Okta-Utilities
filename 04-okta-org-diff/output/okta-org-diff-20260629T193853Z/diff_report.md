# Okta Org Diff Report

**Status:** `DIFFERENCES_FOUND`

**Generated:** `2026-06-29T19:38:53.135584+00:00`

**Baseline backup:** `/Users/ravikumar/Cayden's Projects/Okta Projects/01-okta-config-backup/output/okta-config-backup-20260626T193825Z`

**Comparison backup:** `/Users/ravikumar/Cayden's Projects/Okta Projects/01-okta-config-backup/output/okta-config-backup-20260629T192942Z`

## Summary

| Added | Removed | Changed | Unchanged | Duplicate Keys | Warnings | Errors |
| --- | --- | --- | --- | --- | --- | --- |
| 2 | 3 | 13 | 13 | 0 | 0 | 0 |

## Resource Summary

| Resource | Baseline | Comparison | Added | Removed | Changed | Dupes | Warnings | Errors |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| org | 1 | 1 | 0 | 0 | 1 | 0 | 0 | 0 |
| applications | 8 | 7 | 0 | 1 | 7 | 0 | 0 | 0 |
| groups | 2 | 2 | 0 | 0 | 0 | 0 | 0 | 0 |
| group_rules | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| policies | 5 | 5 | 0 | 0 | 4 | 0 | 0 | 0 |
| identity_providers | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| authorization_servers | 1 | 1 | 0 | 0 | 1 | 0 | 0 | 0 |
| trusted_origins | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| network_zones | 4 | 4 | 0 | 0 | 0 | 0 | 0 | 0 |
| domains | 1 | 1 | 1 | 1 | 0 | 0 | 0 | 0 |
| brands | 1 | 1 | 1 | 1 | 0 | 0 | 0 | 0 |
| authenticators | 6 | 6 | 0 | 0 | 0 | 0 | 0 | 0 |
| event_hooks | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| inline_hooks | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |

## Changes

| Resource | Type | Key | Baseline ID | Comparison ID | Changed Paths | Message |
| --- | --- | --- | --- | --- | --- | --- |
| org | changed | org | 00o12rbljxj8EbvI9698 | 00o14igebb9XzvK0b698 | $.companyName; $.subdomain |  |
| applications | removed | My API Services App1 | 0oa14jw2jexR0cddS698 |  |  |  |
| applications | changed | Okta Access Certification Reviews | 0oa12rbv0xoyPhkAV698 | 0oa14igmbhnEDhWYf698 | $.credentials.signing.kid; $.orn |  |
| applications | changed | Okta Admin Console | 0oa12rbljxtCxUtTr698 | 0oa14igebbjjOrvHg698 | $.credentials.signing.kid; $.orn |  |
| applications | changed | Okta Browser Plugin | 0oa12rblk0lJUiVFJ698 | 0oa14igebft0JLR64698 | $.credentials.signing.kid; $.orn |  |
| applications | changed | Okta Dashboard | 0oa12rbljylGLVxDK698 | 0oa14igebcb37syUE698 | $.credentials.signing.kid; $.orn |  |
| applications | changed | Okta OIN Submission Tester | 0oa12rblkdwxrsPJm698 | 0oa14igjtd3RlpNVb698 | $.credentials.signing.kid; $.orn |  |
| applications | changed | Okta Workflows | 0oa12rbvtykLQboWH698 | 0oa14igmxoeJmeFCi698 | $.credentials.signing.kid; $.orn; $.settings.app.initiateLoginURI; $.settings.app.redirectURI |  |
| applications | changed | Okta Workflows OAuth | 0oa12rbvxg0HMgbfe698 | 0oa14igmxpbK1BYrn698 | $.credentials.signing.kid; $.orn |  |
| policies | changed | MFA_ENROLL::Default Policy | 00p12rblk6hXMiLHH698 | 00p14igjt8kIKU1HX698 | $.conditions.people.groups.include[0] |  |
| policies | changed | OKTA_SIGN_ON::Default Policy | 00p12rbljzrV59ac5698 | 00p14igebdcAqI91x698 | $.conditions.people.groups.include[0] |  |
| policies | changed | PASSWORD::Default Policy | 00p12rblk1twKW1bp698 | 00p14igebh0Cwrtqm698 | $.conditions.people.groups.include[0] |  |
| policies | changed | PROFILE_ENROLLMENT::Default Policy | rst12rblk2xK0mFoS698 | rst14igebi9XzTHCW698 | $._rules[0].actions.profileEnrollment.uiSchemaId |  |
| authorization_servers | changed | default | aus12rblk7jW5131Z698 | aus14igjt70jcfQm9698 | $.credentials.signing.kid; $.credentials.signing.lastRotated; $.credentials.signing.nextRotation; $.issuer |  |
| domains | added | integrator-1703705.okta.com |  | default |  |  |
| domains | removed | integrator-3799871.okta.com | default |  |  |  |
| brands | added | navarsecurity-integrator-1703705 |  | bnd14igebbg02N8Vf698 |  |  |
| brands | removed | navarsecurity-integrator-3799871 | bnd12rbljxqHf40PF698 |  |  |  |

## Notes

This utility compares local backup files only. It does not connect to Okta and does not change either environment. Review generated differences before using the result for migration, restore, or cutover decisions.
