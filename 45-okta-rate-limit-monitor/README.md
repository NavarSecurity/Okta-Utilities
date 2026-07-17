# WARNING

These utilities have limited testing and are provided as-is with no warranty. Use at your own risk.

# okta-rate-limit-monitor

Python utility for monitoring Okta API rate-limit risk using response headers, System Log events, and planned request estimates.

This utility is intended for Okta backup runs, imports, migrations, Terraform operations, large exports, and other automation work that can generate high API traffic.

---

## What This Utility Does

The `okta-rate-limit-monitor` utility collects read-only evidence about rate-limit posture before or during Okta automation work.

It can export:

| Export Area | Purpose |
|---|---|
| Rate-limit response headers | Captures `X-Rate-Limit-Limit`, `X-Rate-Limit-Remaining`, and `X-Rate-Limit-Reset` from selected Okta API probe requests. |
| System Log rate-limit events | Queries recent System Log events for rate-limit warnings and violations. |
| Planned operation estimates | Compares planned request volume against observed endpoint limits where matching probe data is available. |
| Risk findings | Flags low remaining capacity, recent rate-limit events, unknown limits, and planned request volume risk. |
| Request failures | Records endpoint failures without exposing tokens or authorization headers. |

This utility does not create, update, delete, import, assign, deactivate, revoke, rotate, or modify any Okta object. It is read-only.

---

## Safety Model

This utility is read-only.

It only sends selected `GET` requests to Okta APIs and writes local output files.

Dry-run validation:

```bash
okta-rate-limit-monitor --config config.json --dry-run
```

Real monitor run:

```bash
okta-rate-limit-monitor --config config.json
```

The utility should not print or write Okta API tokens, bearer tokens, client secrets, private keys, passwords, authorization headers, or session values.

---

## Folder Structure

```text
45-okta-rate-limit-monitor/
  README.md
  pyproject.toml
  .env.example
  .gitignore
  config.example.json
  src/
    okta_rate_limit_monitor/
      __init__.py
      __main__.py
      cli.py
      config.py
      okta_client.py
      exporter.py
      normalize.py
      analyze.py
      redact.py
      reports.py
  samples/
    config.export.sample.json
    config.headers-only.sample.json
    config.system-log-only.sample.json
    planned-operations.sample.json
    sample-rate-limit-events.json
  tests/
    test_analyze.py
    test_config.py
    test_dry_run.py
    test_normalize.py
    test_redact.py
  input/
    .gitkeep
  output/
    .gitkeep
```

---

## Requirements

- Python 3.10 or newer
- Okta admin API token
- Okta org URL
- Network access to the Okta tenant

The API token should be generated from an Okta admin account with permission to call the selected read-only probe endpoints and read System Log events if System Log export is enabled.

---

## Setup

Run these commands from the utility folder.

Create a virtual environment:

```bash
python3 -m venv .venv
```

Activate the virtual environment on macOS or Linux:

```bash
source .venv/bin/activate
```

Activate the virtual environment on Windows PowerShell:

```powershell
.venv\Scripts\Activate.ps1
```

Install the utility:

```bash
python -m pip install -e .
```

Copy the environment example:

```bash
cp .env.example .env
```

Copy a sample configuration file:

```bash
cp samples/config.export.sample.json config.json
```

Open `.env` and update the Okta values.

---

## Environment Variables

Create a `.env` file using `.env.example`.

Example:

```env
OKTA_ORG_URL=https://your-org.okta.com
OKTA_API_TOKEN=replace-with-okta-api-token
```

Do not commit `.env` files.

The `.gitignore` file should exclude:

```text
.env
.venv/
output/*
!output/.gitkeep
```

---

## Configuration

The utility is driven by `config.json`.

Example full configuration:

```json
{
  "outputDirectory": "output",
  "timeoutSeconds": 30,
  "redactSensitiveValues": true,
  "continueOnRequestError": true,
  "includeHeaderProbes": true,
  "includeSystemLogEvents": true,
  "includePlannedOperationEstimate": true,
  "lookbackHours": 24,
  "systemLogFilters": [
    "displayMessage eq \"Rate limit warning\"",
    "displayMessage eq \"Rate limit violation\""
  ],
  "probeEndpoints": [
    {
      "name": "users-list",
      "method": "GET",
      "path": "/api/v1/users",
      "params": {
        "limit": "1"
      }
    },
    {
      "name": "apps-list",
      "method": "GET",
      "path": "/api/v1/apps",
      "params": {
        "limit": "1"
      }
    },
    {
      "name": "system-log",
      "method": "GET",
      "path": "/api/v1/logs",
      "params": {
        "limit": "1"
      }
    }
  ],
  "plannedOperations": [
    {
      "name": "tenant-backup-users",
      "endpoint": "/api/v1/users",
      "estimatedRequests": 50,
      "windowMinutes": 1
    }
  ],
  "riskThresholds": {
    "remainingPercentCritical": 10,
    "remainingPercentWarning": 25,
    "plannedUsagePercentCritical": 90,
    "plannedUsagePercentWarning": 70,
    "rateLimitEventsCritical": 1,
    "rateLimitEventsWarning": 1
  }
}
```

---

## Run Commands

Validate the config without calling Okta:

```bash
okta-rate-limit-monitor --config config.json --dry-run
```

Run the monitor:

```bash
okta-rate-limit-monitor --config config.json
```

Run a headers-only monitor:

```bash
okta-rate-limit-monitor --config samples/config.headers-only.sample.json --dry-run
okta-rate-limit-monitor --config samples/config.headers-only.sample.json
```

Run a System Log-only monitor:

```bash
okta-rate-limit-monitor --config samples/config.system-log-only.sample.json --dry-run
okta-rate-limit-monitor --config samples/config.system-log-only.sample.json
```

---

## Header Probes

Header probes make small read-only `GET` requests to selected endpoints and capture rate-limit response headers.

Example probe configuration:

```json
{
  "name": "users-list",
  "method": "GET",
  "path": "/api/v1/users",
  "params": {
    "limit": "1"
  }
}
```

The utility captures:

```text
X-Rate-Limit-Limit
X-Rate-Limit-Remaining
X-Rate-Limit-Reset
```

These values are written to:

```text
rate_limit_headers.json
rate_limit_headers.csv
```

---

## System Log Event Review

System Log review queries recent rate-limit warning and violation events.

Default filters:

```text
displayMessage eq "Rate limit warning"
displayMessage eq "Rate limit violation"
```

The lookback window is controlled by:

```json
{
  "lookbackHours": 24
}
```

System Log events are written to:

```text
system_log_rate_limit_events.json
system_log_rate_limit_events.csv
system_log_event_counts.json
```

---

## Planned Operation Estimates

Planned operation estimates help preview whether an upcoming automation run may create rate-limit pressure.

Example:

```json
{
  "name": "tenant-backup-users",
  "endpoint": "/api/v1/users",
  "estimatedRequests": 50,
  "windowMinutes": 1
}
```

The utility compares the planned request estimate against matching observed probe limits when possible.

Planned estimates are written to:

```text
planned_operation_estimates.json
planned_operation_estimates.csv
```

If no matching probe limit exists, the utility writes an informational finding instead of guessing.

---

## Output Reports

Each real run creates a timestamped output folder.

Expected output:

```text
output/rate-limit-monitor-<timestamp>/
  rate_limit_headers.json
  rate_limit_headers.csv
  system_log_rate_limit_events.json
  system_log_rate_limit_events.csv
  system_log_event_counts.json
  planned_operation_estimates.json
  planned_operation_estimates.csv
  rate_limit_findings.json
  rate_limit_findings.csv
  request_failures.json
  request_failures.csv
  rate_limit_monitor_report.md
  execution_report.json
  manifest.json
```

Each dry run creates:

```text
output/rate-limit-monitor-dry-run-<timestamp>/
  dry_run_report.json
  config_summary.json
  execution_report.json
  manifest.json
```

---

## Risk Findings

The utility writes findings to:

```text
rate_limit_findings.csv
rate_limit_findings.json
```

Finding categories include:

| Category | Meaning |
|---|---|
| `LOW_REMAINING_RATE_LIMIT` | A probe endpoint has low remaining capacity based on response headers. |
| `RATE_LIMIT_HEADERS_MISSING` | A probe response did not include parseable rate-limit headers. |
| `RATE_LIMIT_SYSTEM_LOG_EVENTS` | Recent rate-limit warning or violation events were found. |
| `PLANNED_OPERATION_LIMIT_UNKNOWN` | A planned operation has no matching probe limit. |
| `PLANNED_OPERATION_RATE_LIMIT_RISK` | Planned request volume is high compared to the observed limit. |

---

## Recommended Workflow

Use this utility before large Okta automation runs.

Run a dry run:

```bash
okta-rate-limit-monitor --config config.json --dry-run
```

Run the monitor:

```bash
okta-rate-limit-monitor --config config.json
```

Review:

```text
rate_limit_headers.csv
system_log_rate_limit_events.csv
planned_operation_estimates.csv
rate_limit_findings.csv
rate_limit_monitor_report.md
```

If the findings show recent violations or low remaining capacity, delay the automation, reduce concurrency, add backoff, reduce page size, split the run into batches, or schedule the run during a quieter window.

---

## Testing

Install test dependencies:

```bash
python -m pip install -e ".[dev]"
```

Run tests:

```bash
pytest
```

Run tests with verbose output:

```bash
pytest -v
```

---

## Troubleshooting

### 401 Unauthorized

Confirm the Okta org URL and API token in `.env`.

```bash
cat .env
```

The org URL should look like:

```text
https://your-org.okta.com
```

Do not include `/api/v1` in `OKTA_ORG_URL`.

---

### 403 Forbidden

The API token may not have permission to read one or more selected endpoints.

Disable the failing probe, use a token generated by an account with the right read permissions, or set `continueOnRequestError` to `true` so the utility records the failure and continues.

---

### No System Log Events Found

This can mean there were no rate-limit warnings or violations in the configured lookback window.

Increase the lookback window if needed:

```json
{
  "lookbackHours": 72
}
```

---

### Probe Response Has Missing Headers

Some responses may not expose expected rate-limit headers in every situation.

The utility records this as informational evidence and does not guess a limit.

---

## Security Notes

- Do not commit `.env`.
- Do not commit raw client output without review.
- Treat System Log exports as sensitive because they can contain usernames, IP addresses, request paths, user agents, actors, and operational patterns.
- Treat rate-limit reports as operational evidence.
- Use this utility before running high-volume scripts.
- Reduce concurrency and add retry/backoff logic in other utilities when rate-limit pressure is detected.

---

## Practical Use Cases

Use this utility to:

- Check rate-limit posture before a tenant backup.
- Check rate-limit posture before large imports or migrations.
- Review whether Terraform is close to rate-limit pressure.
- Find recent rate-limit warnings or violations in the System Log.
- Estimate whether a planned script run may create rate-limit risk.
- Create evidence for migration readiness or post-incident review.
- Tune script concurrency, page sizes, and retry/backoff settings.

---

## Notes

This utility provides operational evidence and estimates. It does not guarantee that a future run will avoid rate limits. Other active integrations, admins, users, scripts, and client-based limits can affect observed capacity during execution.
