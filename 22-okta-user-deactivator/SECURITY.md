# Security Notes

This utility can modify Okta user lifecycle state. Treat it as a high-impact operational tool.

Do not commit or share:

```text
.env
local config files with tokens
output folders with real user data
CSV files containing real users unless approved
```

Use a sandbox org first. Start with one test user. Review dry-run output before apply mode.

Delete actions are intentionally disabled by default and should only be used for already deprovisioned users after approval.
