# WARNING

These utilities have limited testing and are provided as-is with no warranty. Use at your own risk.

# okta-security-event-detector

Python utility for analyzing Okta System Log exports for risky or suspicious activity.

This utility is intended for IAM operations, post-change review, security investigation support, and Okta audit evidence review. It works offline from exported Okta System Log data, usually produced by utility 41, `okta-system-log-exporter`.

---

## What This Utility Does

The `okta-security-event-detector` utility reads Okta System Log event exports and produces detection reports for security-relevant activity.

It can detect and summarize events such as:

| Detection Area | Example |
|---|---|
| Failed sign-in spikes | Multiple failed sign-ins by actor or IP address. |
| MFA failure spikes | Multiple failed authenticator or MFA events. |
| Suspicious countries | Events from countries outside the configured allow list. |
| Multiple countries per actor | Same actor appearing from multiple countries in the analyzed data set. |
| Suspicious IPs | Events from configured suspicious IP addresses. |
| Admin activity | Admin role, privilege, or administrative access activity. |
| Policy changes | Policy or policy rule updates. |
| MFA or authenticator changes | Factor reset, enrollment, or authenticator lifecycle activity. |
| API token activity | API token or OAuth client secret activity. |
| User lifecycle activity | User suspension, deactivation, account lock, unlock, or password reset activity. |
| App configuration activity | Application configuration or assignment activity. |
| Rate limit events | Rate limit or throttling warnings. |

The utility does not call the Okta API directly. It analyzes exported log files.

---

## Safety Model

This utility is read-only and offline.

It does not:

- Modify Okta configuration
- Create users
- Update users
- Change policies
- Reset MFA
- Call live Okta APIs

Dry run creates an evidence folder showing what would be analyzed.

```bash
okta-security-event-detector --config config.json --dry-run
```

Real analysis reads the configured input file and writes detection outputs.

```bash
okta-security-event-detector --config config.json
```

---

## Folder Structure

```text
42-okta-security-event-detector/
  README.md
  pyproject.toml
  .env.example
  .gitignore
  config.example.json
  src/
    okta_security_event_detector/
      __init__.py
      __main__.py
      cli.py
      config.py
      detector.py
      filters.py
      loader.py
      normalize.py
      redact.py
      reports.py
      utils.py
  samples/
    config.detect.sample.json
    config.filtered.sample.json
    config.high-signal.sample.json
    sample-system-log-events.json
  tests/
    test_config.py
    test_detector.py
    test_loader.py
    test_normalize.py
    test_redact.py
    test_reports.py
  input/
    .gitkeep
  output/
    .gitkeep
```

---

## Requirements

- Python 3.10 or newer
- Okta System Log export JSON file
- Utility 41 output, or another Okta System Log export in compatible JSON format

No Okta API token is required for this utility.

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
cp samples/config.detect.sample.json config.json
```

---

## Input File

The utility expects an Okta System Log event export.

Typical input from utility 41:

```text
output/system-log-export-<timestamp>/system_log_events_full.json
```

For this utility, copy that file into `input/` or point `config.json` directly to it.

Example copy command:

```bash
cp ../41-okta-system-log-exporter/output/system-log-export-<timestamp>/system_log_events_full.json input/system_log_events_full.json
```

Then set `config.json` to:

```json
{
  "inputFile": "input/system_log_events_full.json",
  "outputDirectory": "output"
}
```

The input file can be:

```text
A JSON array of Okta System Log events
A JSON object with an events list
A JSONL or NDJSON file with one event per line
```

---

## Configuration

The utility is driven by `config.json`.

Example configuration:

```json
{
  "inputFile": "input/system_log_events_full.json",
  "outputDirectory": "output",
  "redactSensitiveValues": true,
  "includeLowSeverity": true,
  "includeInformationalFindings": false,
  "filters": {
    "eventTypes": [],
    "actors": [],
    "excludeActors": [],
    "ipAddresses": [],
    "startTime": null,
    "endTime": null
  },
  "detections": {
    "failedSignInSpike": {
      "enabled": true,
      "threshold": 5,
      "severity": "medium"
    },
    "mfaFailureSpike": {
      "enabled": true,
      "threshold": 3,
      "severity": "high"
    },
    "suspiciousCountry": {
      "enabled": true,
      "allowedCountries": [
        "United States"
      ],
      "severity": "medium"
    },
    "multipleCountriesPerActor": {
      "enabled": true,
      "threshold": 2,
      "severity": "medium"
    },
    "suspiciousIpAddresses": {
      "enabled": true,
      "ipAddresses": [],
      "severity": "high"
    }
  }
}
```

---

## Filters

Filters reduce which events are analyzed.

Filter by event type:

```json
{
  "filters": {
    "eventTypes": [
      "user.authentication.failed",
      "policy.lifecycle.update"
    ]
  }
}
```

Filter by actor:

```json
{
  "filters": {
    "actors": [
      "admin@example.com"
    ]
  }
}
```

Exclude noisy service accounts:

```json
{
  "filters": {
    "excludeActors": [
      "service.account@example.com"
    ]
  }
}
```

Filter by time range:

```json
{
  "filters": {
    "startTime": "2026-07-16T00:00:00Z",
    "endTime": "2026-07-17T00:00:00Z"
  }
}
```

---

## Detection Tuning

### Failed Sign-In Spike

```json
{
  "detections": {
    "failedSignInSpike": {
      "enabled": true,
      "threshold": 5,
      "severity": "medium"
    }
  }
}
```

This creates findings when the same actor or IP address has at least five failed sign-in related events in the analyzed data set.

### MFA Failure Spike

```json
{
  "detections": {
    "mfaFailureSpike": {
      "enabled": true,
      "threshold": 3,
      "severity": "high"
    }
  }
}
```

This creates findings when an actor has repeated MFA or authenticator failure events.

### Suspicious Country

```json
{
  "detections": {
    "suspiciousCountry": {
      "enabled": true,
      "allowedCountries": [
        "United States"
      ],
      "severity": "medium"
    }
  }
}
```

This creates findings for events from countries outside the configured list.

### Suspicious IP Addresses

```json
{
  "detections": {
    "suspiciousIpAddresses": {
      "enabled": true,
      "ipAddresses": [
        "203.0.113.77"
      ],
      "severity": "high"
    }
  }
}
```

This creates findings when events originate from specific configured IP addresses.

---

## Dry Run

Run a dry run first:

```bash
okta-security-event-detector --config config.json --dry-run
```

Expected output:

```text
output/security-event-dry-run-<timestamp>/
  dry_run_report.json
  config_summary.json
  execution_report.json
  manifest.json
```

Dry run validates configuration and writes evidence about what the utility would analyze.

---

## Run Analysis

Run the detector:

```bash
okta-security-event-detector --config config.json
```

Expected output:

```text
output/security-event-detection-<timestamp>/
  security_detections.json
  security_detections.csv
  detection_summary.json
  severity_summary.csv
  rule_summary.csv
  actor_risk_summary.csv
  ip_risk_summary.csv
  security_event_report.md
  execution_report.json
  manifest.json
  detections_by_rule/
```

---

## Output Files

| File | Purpose |
|---|---|
| `security_detections.json` | Full detection output, including supporting event context. |
| `security_detections.csv` | Flat detection list for review. |
| `detection_summary.json` | Summary counts and top actors. |
| `severity_summary.csv` | Count of findings by severity. |
| `rule_summary.csv` | Count of findings by detection rule. |
| `actor_risk_summary.csv` | Aggregated findings by actor. |
| `ip_risk_summary.csv` | Aggregated findings by IP address. |
| `security_event_report.md` | Markdown report for quick review. |
| `execution_report.json` | Run status, counts, warnings, and errors. |
| `manifest.json` | Output manifest and run metadata. |
| `detections_by_rule/` | Per-rule detection CSVs. |

---

## How to Read `security_detections.csv`

Each row is one detection.

Important fields:

| Field | Meaning |
|---|---|
| `detectionId` | Unique ID assigned by the utility for this run. |
| `ruleId` | Detection rule that created the finding. |
| `severity` | Severity assigned by configuration. |
| `category` | General category such as Authentication, MFA, Geo, Policy, or API Access. |
| `published` | Timestamp of the example event. |
| `actor` | User, admin, or client actor involved. |
| `clientIpAddress` | Source IP address. |
| `country` | Geo country if present in the event. |
| `eventType` | Okta System Log event type. |
| `reason` | Human-readable explanation. |
| `evidence` | Why the utility generated the detection. |

Example interpretation:

```text
ruleId: FAILED_SIGN_IN_SPIKE_BY_ACTOR
actor: alex@example.com
reason: Actor had 6 failed sign-in related events.
```

This means the analyzed System Log data contained repeated sign-in failures for that actor above the configured threshold.

---

## Recommended Workflow

Export logs with utility 41:

```bash
okta-system-log-exporter --config config.json
```

Copy the full System Log export into this utility:

```bash
cp ../41-okta-system-log-exporter/output/system-log-export-<timestamp>/system_log_events_full.json input/system_log_events_full.json
```

Copy the detector sample config:

```bash
cp samples/config.detect.sample.json config.json
```

Run dry run:

```bash
okta-security-event-detector --config config.json --dry-run
```

Run analysis:

```bash
okta-security-event-detector --config config.json
```

Review these files first:

```text
output/security-event-detection-<timestamp>/security_event_report.md
output/security-event-detection-<timestamp>/security_detections.csv
output/security-event-detection-<timestamp>/actor_risk_summary.csv
```

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

### Input file not found

Confirm that `config.json` points to a real file.

```json
{
  "inputFile": "input/system_log_events_full.json"
}
```

### No events remained after filters

Your filters may be too narrow.

Check:

```json
{
  "filters": {
    "eventTypes": [],
    "actors": [],
    "excludeActors": [],
    "ipAddresses": []
  }
}
```

Empty arrays mean no filtering for that field.

### No detections were produced

This can mean one of three things:

```text
The log export does not contain suspicious activity for the configured rules.
Thresholds are too high.
Detection rules are disabled or too narrow.
```

Lower the thresholds for testing:

```json
{
  "detections": {
    "failedSignInSpike": {
      "enabled": true,
      "threshold": 2,
      "severity": "medium"
    }
  }
}
```

### Too many detections

Use a high-signal config:

```bash
cp samples/config.high-signal.sample.json config.json
```

Or exclude known service accounts:

```json
{
  "filters": {
    "excludeActors": [
      "service.account@example.com"
    ]
  }
}
```

---

## Security Notes

- Treat System Log exports as sensitive.
- Do not commit raw client System Log exports to Git.
- Do not commit generated detection outputs without review.
- `redactSensitiveValues` should remain `true` unless there is a documented reason to disable it.
- Findings are indicators for review, not final incident conclusions.
- Tune thresholds and allow lists for each client environment.

---

## Practical Use Cases

Use this utility to:

- Review Okta System Log exports after an incident.
- Find repeated failed sign-ins.
- Identify unusual geo activity.
- Review risky admin or policy changes.
- Summarize MFA failures.
- Produce evidence for IAM operations review.
- Compare security signal before and after a policy change.
- Support weekly or monthly Okta security review packages.

---

## Notes

This utility is not a SIEM replacement. It is a lightweight offline detector for Okta System Log exports.

Use it to produce reviewable evidence, then validate high-risk findings manually in Okta, SIEM logs, endpoint logs, network logs, and ticketing records as appropriate.
