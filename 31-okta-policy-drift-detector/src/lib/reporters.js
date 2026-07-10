const fs = require('fs');
const path = require('path');

function timestampForPath(date = new Date()) {
  return date.toISOString().replace(/[:.]/g, '-');
}

function ensureDir(dirPath) {
  fs.mkdirSync(dirPath, { recursive: true });
}

function writeJson(filePath, data) {
  fs.writeFileSync(filePath, `${JSON.stringify(data, null, 2)}\n`, 'utf8');
}

function writeCsv(filePath, rows, columns) {
  const lines = [columns.map((column) => csvEscape(column.header)).join(',')];
  for (const row of rows) {
    lines.push(columns.map((column) => csvEscape(resolveColumn(row, column.key))).join(','));
  }
  fs.writeFileSync(filePath, `${lines.join('\n')}\n`, 'utf8');
}

function resolveColumn(row, key) {
  if (typeof key === 'function') {
    return key(row);
  }
  return key.split('.').reduce((value, part) => (value == null ? undefined : value[part]), row);
}

function csvEscape(value) {
  if (value === null || value === undefined) return '';
  const stringValue = typeof value === 'string' ? value : JSON.stringify(value);
  if (/[",\n\r]/.test(stringValue)) {
    return `"${stringValue.replace(/"/g, '""')}"`;
  }
  return stringValue;
}

function writeReports(result, config, startedAt, finishedAt) {
  const runDir = path.join(config.outputDir, `policy-drift-${timestampForPath(startedAt)}`);
  ensureDir(runDir);

  const files = {
    driftDetails: path.join(runDir, 'drift_details.json'),
    driftSummaryCsv: path.join(runDir, 'drift_summary.csv'),
    policyDriftCsv: path.join(runDir, 'policy_drift.csv'),
    ruleDriftCsv: path.join(runDir, 'rule_drift.csv'),
    reportMarkdown: path.join(runDir, 'policy_drift_report.md'),
    executionReport: path.join(runDir, 'execution_report.json'),
    manifest: path.join(runDir, 'manifest.json')
  };

  writeJson(files.driftDetails, {
    summary: result.summary,
    duplicateWarnings: result.duplicateWarnings,
    policyDrift: result.policyDrift,
    ruleDrift: result.ruleDrift
  });

  writeCsv(files.driftSummaryCsv, result.driftItems.filter((item) => item.driftType !== 'MATCHED'), driftColumns());
  writeCsv(files.policyDriftCsv, result.policyDrift, driftColumns());
  writeCsv(files.ruleDriftCsv, result.ruleDrift, driftColumns());
  fs.writeFileSync(files.reportMarkdown, buildMarkdownReport(result, config, startedAt, finishedAt), 'utf8');

  const executionReport = {
    utility: '31-okta-policy-drift-detector',
    startedAt: startedAt.toISOString(),
    finishedAt: finishedAt.toISOString(),
    sourceLabel: config.sourceLabel,
    targetLabel: config.targetLabel,
    sourceExportPath: config.sourceExportPath,
    targetExportPath: config.targetExportPath,
    outputDirectory: runDir,
    counts: result.summary,
    warnings: result.duplicateWarnings,
    files
  };

  writeJson(files.executionReport, executionReport);
  writeJson(files.manifest, {
    utility: '31-okta-policy-drift-detector',
    generatedAt: finishedAt.toISOString(),
    files,
    sourceExportPath: config.sourceExportPath,
    targetExportPath: config.targetExportPath,
    driftFound: result.summary.driftFound,
    driftItemCount: result.summary.driftItemCount
  });

  return {
    runDir,
    files,
    executionReport
  };
}

function driftColumns() {
  return [
    { header: 'itemType', key: 'itemType' },
    { header: 'driftType', key: 'driftType' },
    { header: 'severity', key: 'severity' },
    { header: 'policyType', key: 'policyType' },
    { header: 'policyName', key: 'policyName' },
    { header: 'ruleType', key: 'ruleType' },
    { header: 'name', key: 'name' },
    { header: 'authorizationServerName', key: 'authorizationServerName' },
    { header: 'source', key: 'source' },
    { header: 'diffCount', key: 'diffCount' },
    { header: 'message', key: 'message' },
    {
      header: 'changedPaths',
      key: (row) => (row.differences || []).map((diff) => diff.path).join('; ')
    },
    { header: 'key', key: 'key' }
  ];
}

function buildMarkdownReport(result, config, startedAt, finishedAt) {
  const summary = result.summary;
  const driftRows = result.driftItems.filter((item) => item.driftType !== 'MATCHED');
  const topRows = driftRows.slice(0, 50);

  const lines = [];
  lines.push('# Okta Policy Drift Report');
  lines.push('');
  lines.push(`Generated: ${finishedAt.toISOString()}`);
  lines.push(`Source: ${config.sourceLabel}`);
  lines.push(`Target: ${config.targetLabel}`);
  lines.push('');
  lines.push('## Summary');
  lines.push('');
  lines.push(`- Drift found: ${summary.driftFound ? 'YES' : 'NO'}`);
  lines.push(`- Drift items: ${summary.driftItemCount}`);
  lines.push(`- Policy drift items: ${summary.policyDriftCount}`);
  lines.push(`- Rule drift items: ${summary.ruleDriftCount}`);
  lines.push(`- Duplicate identity warnings: ${summary.duplicateWarningCount}`);
  lines.push(`- Runtime seconds: ${((finishedAt.getTime() - startedAt.getTime()) / 1000).toFixed(2)}`);
  lines.push('');
  lines.push('## Drift by Type');
  lines.push('');
  lines.push('| Drift Type | Count |');
  lines.push('|---|---:|');
  for (const [key, count] of Object.entries(summary.byType)) {
    lines.push(`| ${escapePipe(key)} | ${count} |`);
  }
  if (Object.keys(summary.byType).length === 0) {
    lines.push('| None | 0 |');
  }
  lines.push('');
  lines.push('## Drift by Severity');
  lines.push('');
  lines.push('| Severity | Count |');
  lines.push('|---|---:|');
  for (const [key, count] of Object.entries(summary.bySeverity)) {
    lines.push(`| ${escapePipe(key)} | ${count} |`);
  }
  if (Object.keys(summary.bySeverity).length === 0) {
    lines.push('| None | 0 |');
  }
  lines.push('');
  lines.push('## Top Drift Items');
  lines.push('');
  lines.push('| Severity | Type | Policy Type | Policy / Rule | Drift | Changed Paths |');
  lines.push('|---|---|---|---|---|---|');
  for (const item of topRows) {
    const changedPaths = (item.differences || []).map((diff) => diff.path).slice(0, 8).join('<br>');
    lines.push(`| ${escapePipe(item.severity)} | ${escapePipe(item.itemType)} | ${escapePipe(item.policyType)} | ${escapePipe(item.policyName || item.name)} | ${escapePipe(item.driftType)} | ${escapePipe(changedPaths)} |`);
  }
  if (topRows.length === 0) {
    lines.push('| INFO | None | None | None | MATCHED | None |');
  }
  lines.push('');
  if (driftRows.length > 50) {
    lines.push(`Only the first 50 drift items are shown here. Review drift_details.json for all ${driftRows.length} items.`);
    lines.push('');
  }
  if (result.duplicateWarnings.length > 0) {
    lines.push('## Warnings');
    lines.push('');
    for (const warning of result.duplicateWarnings) {
      lines.push(`- ${warning.message} Key: ${warning.key}`);
    }
    lines.push('');
  }
  return `${lines.join('\n')}\n`;
}

function escapePipe(value) {
  return String(value || '').replace(/\|/g, '\\|');
}

module.exports = {
  timestampForPath,
  ensureDir,
  writeJson,
  writeCsv,
  writeReports,
  buildMarkdownReport
};
