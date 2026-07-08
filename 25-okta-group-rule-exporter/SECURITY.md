# SECURITY.md

## Secret handling

This utility reads Okta credentials from `.env` or environment variables. Do not commit `.env` to source control.

## Sensitive output

The utility is read-only, but group rule exports can reveal internal group names, profile attributes, and Okta Expression Language business logic. Review output before sharing.

## Recommended usage

Use a least-privilege token or OAuth client that can read group rules. Run in a sandbox before running against a production org.
