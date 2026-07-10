# 31-okta-policy-drift-detector

# WARNING

These utilities have limited testing and are provided as-is with no warranty. Use at your own risk.

## Purpose

`okta-policy-drift-detector` compares two Okta policy exports and reports policy drift between environments, tenants, or backup snapshots.

It is designed to consume the `policies_full.json` output created by utility 30, `okta-policy-exporter`.

Use this when you need to answer questions like:

- Did production policy behavior drift from development or staging?
- Did a migration miss a sign-on, password, MFA enrollment, app sign-in, or authorization server access policy?
- Did a post-change validation find unexpected rule, condition, action, priority, or status differences?
- Are extra policies or rules present in the target org?
- Are expected policies or rules missing from the target org?

This utility is read-only and offline. It does not call the Okta API and does not require an Okta API token.

## What It Compares

The utility compares both policy-level and rule-level configuration from utility 30 exports.

Default policy fields compared:

```text
status
name
description
priority
system
type
conditions
actions
settings
```

Default rule fields compared:

```text
status
name
priority
system
type
conditions
actions
```

Default volatile fields ignored:

```text
id
created
lastUpdated
_links
links
```

This lets the utility compare two different Okta orgs without reporting normal object ID and timestamp differences as drift.

## Included Files

```text
31-okta-policy-drift-detector/
  README.md
  package.json
  .env.example
  .gitignore
  config.example.json
  src/
    index.js
    lib/
      config.js
      loadExport.js
      normalize.js
      diff.js
      reporters.js
  samples/
    config.sample.json
    source-policies_full.json
    target-policies_full.json
  tests/
    normalize.test.js
    diff.test.js
  output/
    .gitkeep
```

## Setup

Install dependencies:

```bash
npm install
```

This utility currently uses only Node.js built-in modules, so `npm install` should complete quickly.

## Run the Sample Comparison

Copy the sample config to `config.json`:

```bash
cp samples/config.sample.json config.json
```

Run the sample drift check:

```bash
node src/index.js --config config.json
```

Or run the same sample directly through the package script:

```bash
npm run sample
```

The sample intentionally contains drift. It should report modified sign-on rule behavior, changed token scope rules, and extra target policy/rule objects.

## Run Against Real Utility 30 Exports

Copy the example config:

```bash
cp config.example.json config.json
```

Edit these values in `config.json`:

```json
{
  "sourceLabel": "dev",
  "targetLabel": "prod",
  "sourceExportPath": "../30-okta-policy-exporter/output/dev-export/policies_full.json",
  "targetExportPath": "../30-okta-policy-exporter/output/prod-export/policies_full.json",
  "outputDir": "output"
}
```

You can point `sourceExportPath` and `targetExportPath` either to the `policies_full.json` file or to a utility 30 export directory that contains `policies_full.json`.

Run the detector:

```bash
node src/index.js --config config.json
```

Run in strict mode if you want the command to return exit code `2` when drift is found:

```bash
node src/index.js --config config.json --strict
```

You can also set this behavior permanently in `config.json`:

```json
{
  "failOnDrift": true
}
```

## Output Files

Each run creates a timestamped output folder:

```text
output/policy-drift-<timestamp>/
  drift_details.json
  drift_summary.csv
  policy_drift.csv
  rule_drift.csv
  policy_drift_report.md
  execution_report.json
  manifest.json
```

### `drift_details.json`

Full structured drift output, including every changed path and source/target value.

### `drift_summary.csv`

Flat CSV containing all policy and rule drift items.

### `policy_drift.csv`

Policy-level drift only.

### `rule_drift.csv`

Rule-level drift only.

### `policy_drift_report.md`

Readable Markdown report for review, ticket attachment, or client evidence.

### `execution_report.json`

Run metadata, input paths, counts, warnings, and generated files.

### `manifest.json`

Machine-readable file manifest for automation.

## Drift Types

```text
MODIFIED
MISSING_IN_TARGET
EXTRA_IN_TARGET
MATCHED
```

`MATCHED` items are excluded by default. To include matched items in the detailed output, set:

```json
{
  "includeEqualItems": true
}
```

## Severity Model

The utility assigns severity based on the changed paths:

```text
HIGH    actions, conditions, settings, or status changed
MEDIUM  priority, type, or system changed
LOW     name, description, or other low-impact fields changed
INFO    matched item when includeEqualItems is enabled
```

Treat severity as a review aid, not as an approval decision.

## Identity Matching

By default, policies are matched by stable names and scope instead of raw Okta object IDs.

Org policy identity format:

```text
orgPolicy::<policyType>::<policyName>
```

Authorization server policy identity format:

```text
authorizationServerPolicy::AUTHORIZATION_SERVER_ACCESS_POLICY::<authorizationServerName>::<policyName>
```

Rule identity format:

```text
<policyIdentity>::rule::<ruleType>::<ruleName>
```

This avoids false drift when comparing two different Okta orgs where object IDs are expected to differ.

If you are comparing two exports from the same org and want to match by policy ID, set:

```json
{
  "identityMode": "id"
}
```

## Reference Mapping

Some policy conditions contain environment-specific IDs, such as group IDs, client IDs, app IDs, or network zone IDs. When comparing two different Okta orgs, use a reference map to translate known source values to target values before comparison.

Create a reference map file:

```bash
cat > reference-map.json <<'EOF'
{
  "00gSOURCEEVERYONE": "00gTARGETEVERYONE",
  "0oaSOURCEAPP": "0oaTARGETAPP",
  "nzSOURCEZONE": "nzTARGETZONE"
}
EOF
```

Then reference it in `config.json`:

```json
{
  "compare": {
    "referenceMapPath": "reference-map.json"
  }
}
```

## Ignoring Known Differences

Use `ignoreFields` to ignore fields anywhere they appear:

```json
{
  "compare": {
    "ignoreFields": [
      "id",
      "created",
      "lastUpdated",
      "_links",
      "links"
    ]
  }
}
```

Use `ignorePaths` to ignore exact normalized paths:

```json
{
  "compare": {
    "ignorePaths": [
      "issuer",
      "metadata.orgUrl"
    ]
  }
}
```

For policy/rule comparisons, paths are relative to the selected policy or rule object. Examples:

```json
{
  "compare": {
    "ignorePaths": [
      "description",
      "conditions.people.groups.include"
    ]
  }
}
```

## Recommended Workflow

1. Run utility 30 against the source org.
2. Run utility 30 against the target org.
3. Copy `config.example.json` to `config.json`.
4. Point `sourceExportPath` and `targetExportPath` to the two utility 30 exports.
5. Run this utility.
6. Review `policy_drift_report.md` first.
7. Review `drift_details.json` for exact changed values.
8. Decide whether each difference is expected, acceptable, or a remediation item.

Commands:

```bash
cp config.example.json config.json
node src/index.js --config config.json
```

## Testing

Run the unit tests:

```bash
npm test
```

Run the sample comparison:

```bash
npm run sample
```

## Exit Codes

```text
0  Completed successfully, or drift found while failOnDrift is false
1  Execution error
2  Drift found while failOnDrift or --strict is enabled
```

## Notes

- This utility does not mutate Okta.
- This utility does not require `.env` values.
- This utility does not redact input files. Use utility 30 and the backup redactor workflow carefully before sharing exports.
- Do not commit real client policy exports unless they have been approved for storage in the repository.
