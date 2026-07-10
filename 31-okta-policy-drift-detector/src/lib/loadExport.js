const fs = require('fs');
const path = require('path');
const { readJsonFile } = require('./config');

function resolveExportPath(inputPath) {
  if (!fs.existsSync(inputPath)) {
    throw new Error(`Export path does not exist: ${inputPath}`);
  }

  const stats = fs.statSync(inputPath);
  if (stats.isDirectory()) {
    const fullExportPath = path.join(inputPath, 'policies_full.json');
    if (!fs.existsSync(fullExportPath)) {
      throw new Error(`Directory does not contain policies_full.json: ${inputPath}`);
    }
    return fullExportPath;
  }

  return inputPath;
}

function loadPolicyExport(inputPath, label) {
  const resolvedPath = resolveExportPath(inputPath);
  const data = readJsonFile(resolvedPath);

  const exportShapeErrors = [];
  if (!Array.isArray(data.orgPolicies)) {
    exportShapeErrors.push('orgPolicies array is missing.');
  }
  if (!Array.isArray(data.authorizationServerPolicies)) {
    exportShapeErrors.push('authorizationServerPolicies array is missing.');
  }
  if (exportShapeErrors.length > 0) {
    throw new Error(`Input ${label} does not look like a utility 30 policies_full.json export: ${exportShapeErrors.join(' ')}`);
  }

  return {
    label,
    path: resolvedPath,
    metadata: data.metadata || {},
    warnings: data.warnings || [],
    errors: data.errors || [],
    raw: data,
    policies: flattenPolicies(data)
  };
}

function flattenPolicies(data) {
  const rows = [];

  for (const item of data.orgPolicies || []) {
    rows.push({
      source: item.source || 'orgPolicy',
      policyType: item.policyType || item.policy?.type || 'UNKNOWN',
      policyTypeLabel: item.policyTypeLabel || '',
      authorizationServer: null,
      policy: item.policy || {},
      rules: Array.isArray(item.rules) ? item.rules : [],
      raw: item
    });
  }

  for (const item of data.authorizationServerPolicies || []) {
    rows.push({
      source: item.source || 'authorizationServerPolicy',
      policyType: item.policyType || 'AUTHORIZATION_SERVER_ACCESS_POLICY',
      policyTypeLabel: item.policyTypeLabel || '',
      authorizationServer: item.authorizationServer || null,
      policy: item.policy || {},
      rules: Array.isArray(item.rules) ? item.rules : [],
      raw: item
    });
  }

  return rows;
}

module.exports = {
  loadPolicyExport,
  flattenPolicies,
  resolveExportPath
};
