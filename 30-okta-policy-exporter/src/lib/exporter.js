const path = require('path');
const {
  ensureDir,
  writeJsonFile,
  writeCsvFile,
  flattenForSummary,
  redactSensitive,
  timestampForPath,
  sanitizeOrgUrl,
  summarizePolicyType
} = require('./utils');

async function exportPolicies({ client, config, orgUrl, startedAt = new Date(), verbose = false }) {
  const warnings = [];
  const errors = [];
  const orgPolicies = [];
  const authorizationServerPolicies = [];
  const byType = {};

  if (config.includeOrgPolicies) {
    for (const policyType of config.policyTypes) {
      if (verbose) console.log(`[export] Exporting org policies for type ${policyType}`);
      try {
        const policies = await client.getAll(`/api/v1/policies?type=${encodeURIComponent(policyType)}&limit=${config.pageLimit}`);
        byType[policyType] = [];

        for (const policy of policies) {
          const item = {
            source: 'orgPolicy',
            policyType,
            policyTypeLabel: summarizePolicyType(policyType),
            policy: redactSensitive(policy),
            rules: []
          };

          if (config.includeRules && policy.id) {
            try {
              const rules = await client.getAll(`/api/v1/policies/${encodeURIComponent(policy.id)}/rules?limit=${config.pageLimit}`);
              item.rules = redactSensitive(rules);
            } catch (err) {
              warnings.push({
                area: 'orgPolicyRules',
                policyType,
                policyId: policy.id,
                policyName: policy.name,
                message: err.message
              });
            }
          }

          orgPolicies.push(item);
          byType[policyType].push(item);
        }
      } catch (err) {
        const message = `Unable to export org policies for type ${policyType}: ${err.message}`;
        const warning = { area: 'orgPolicies', policyType, message };
        if (config.failOnPolicyTypeError) {
          errors.push(warning);
        } else {
          warnings.push(warning);
        }
      }
    }
  }

  if (config.includeAuthorizationServerPolicies) {
    if (verbose) console.log('[export] Exporting authorization server access policies');
    try {
      const authorizationServers = await client.getAll(`/api/v1/authorizationServers?limit=${config.pageLimit}`);
      const filteredAuthorizationServers = filterAuthorizationServers(authorizationServers, config.authorizationServerIds);

      for (const authorizationServer of filteredAuthorizationServers) {
        try {
          const policies = await client.getAll(
            `/api/v1/authorizationServers/${encodeURIComponent(authorizationServer.id)}/policies?limit=${config.pageLimit}`
          );

          for (const policy of policies) {
            const item = {
              source: 'authorizationServerPolicy',
              policyType: 'AUTHORIZATION_SERVER_ACCESS_POLICY',
              policyTypeLabel: 'Custom Authorization Server Access Policy',
              authorizationServer: redactSensitive(minimizeAuthorizationServer(authorizationServer)),
              policy: redactSensitive(policy),
              rules: []
            };

            if (config.includeRules && policy.id) {
              try {
                const rules = await client.getAll(
                  `/api/v1/authorizationServers/${encodeURIComponent(authorizationServer.id)}/policies/${encodeURIComponent(policy.id)}/rules?limit=${config.pageLimit}`
                );
                item.rules = redactSensitive(rules);
              } catch (err) {
                warnings.push({
                  area: 'authorizationServerPolicyRules',
                  authorizationServerId: authorizationServer.id,
                  authorizationServerName: authorizationServer.name,
                  policyId: policy.id,
                  policyName: policy.name,
                  message: err.message
                });
              }
            }

            authorizationServerPolicies.push(item);
          }
        } catch (err) {
          warnings.push({
            area: 'authorizationServerPolicies',
            authorizationServerId: authorizationServer.id,
            authorizationServerName: authorizationServer.name,
            message: err.message
          });
        }
      }
    } catch (err) {
      warnings.push({
        area: 'authorizationServers',
        message: `Unable to list authorization servers. This can happen if API Access Management is unavailable or the token lacks permission. ${err.message}`
      });
    }
  }

  const finishedAt = new Date();
  const counts = buildCounts(orgPolicies, authorizationServerPolicies, warnings, errors);
  const run = buildRunPaths(config.outputDir, startedAt);
  ensureDir(run.runDir);
  ensureDir(run.byTypeDir);

  const fullExport = {
    metadata: {
      utility: '30-okta-policy-exporter',
      generatedAt: finishedAt.toISOString(),
      orgUrl: sanitizeOrgUrl(orgUrl),
      includeOrgPolicies: config.includeOrgPolicies,
      includeAuthorizationServerPolicies: config.includeAuthorizationServerPolicies,
      includeRules: config.includeRules,
      includeRawObjects: config.includeRawObjects,
      policyTypes: config.policyTypes,
      authorizationServerIds: config.authorizationServerIds,
      counts
    },
    orgPolicies: config.includeRawObjects ? orgPolicies : undefined,
    authorizationServerPolicies: config.includeRawObjects ? authorizationServerPolicies : undefined,
    warnings,
    errors
  };

  writeJsonFile(path.join(run.runDir, 'policies_full.json'), fullExport);
  writeJsonFile(path.join(run.runDir, 'manifest.json'), buildManifest(fullExport.metadata, run));

  for (const [policyType, items] of Object.entries(byType)) {
    writeJsonFile(path.join(run.byTypeDir, `${policyType}.json`), {
      policyType,
      policyTypeLabel: summarizePolicyType(policyType),
      count: items.length,
      policies: items
    });
  }

  if (authorizationServerPolicies.length > 0) {
    writeJsonFile(path.join(run.byTypeDir, 'AUTHORIZATION_SERVER_ACCESS_POLICY.json'), {
      policyType: 'AUTHORIZATION_SERVER_ACCESS_POLICY',
      policyTypeLabel: 'Custom Authorization Server Access Policy',
      count: authorizationServerPolicies.length,
      policies: authorizationServerPolicies
    });
  }

  const policyRows = buildPolicyRows(orgPolicies, authorizationServerPolicies);
  const ruleRows = buildRuleRows(orgPolicies, authorizationServerPolicies);

  writeCsvFile(path.join(run.runDir, 'policies_summary.csv'), policyRows, [
    'source',
    'policyType',
    'policyTypeLabel',
    'authorizationServerId',
    'authorizationServerName',
    'id',
    'name',
    'status',
    'priority',
    'system',
    'created',
    'lastUpdated',
    'ruleCount',
    'description'
  ]);

  writeCsvFile(path.join(run.runDir, 'policy_rules.csv'), ruleRows, [
    'source',
    'policyType',
    'policyTypeLabel',
    'authorizationServerId',
    'authorizationServerName',
    'policyId',
    'policyName',
    'id',
    'name',
    'status',
    'priority',
    'created',
    'lastUpdated',
    'conditionSummary',
    'actionSummary'
  ]);

  const report = {
    utility: '30-okta-policy-exporter',
    startedAt: startedAt.toISOString(),
    finishedAt: finishedAt.toISOString(),
    orgUrl: sanitizeOrgUrl(orgUrl),
    outputDirectory: run.runDir,
    counts,
    warnings,
    errors,
    files: {
      fullExport: path.join(run.runDir, 'policies_full.json'),
      policiesSummaryCsv: path.join(run.runDir, 'policies_summary.csv'),
      policyRulesCsv: path.join(run.runDir, 'policy_rules.csv'),
      manifest: path.join(run.runDir, 'manifest.json'),
      policiesByTypeDirectory: run.byTypeDir
    }
  };

  writeJsonFile(path.join(run.runDir, 'execution_report.json'), report);

  return {
    report,
    hasErrors: errors.length > 0,
    outputDirectory: run.runDir
  };
}

function buildRunPaths(outputDir, startedAt) {
  const runName = `policy-export-${timestampForPath(startedAt)}`;
  const runDir = path.resolve(outputDir, runName);
  return {
    runName,
    runDir,
    byTypeDir: path.join(runDir, 'policies_by_type')
  };
}

function filterAuthorizationServers(authorizationServers, requestedIds = []) {
  if (!requestedIds || requestedIds.length === 0) return authorizationServers;
  const requested = new Set(requestedIds.map((id) => String(id).toLowerCase()));
  return authorizationServers.filter((server) => requested.has(String(server.id).toLowerCase()) || requested.has(String(server.name).toLowerCase()));
}

function minimizeAuthorizationServer(server) {
  return {
    id: server.id,
    name: server.name,
    description: server.description,
    audience: server.audiences || server.audience,
    issuer: server.issuer,
    issuerMode: server.issuerMode,
    status: server.status,
    created: server.created,
    lastUpdated: server.lastUpdated
  };
}

function buildCounts(orgPolicies, authorizationServerPolicies, warnings, errors) {
  const countsByType = {};
  let orgPolicyRuleCount = 0;
  let authorizationServerPolicyRuleCount = 0;

  for (const item of orgPolicies) {
    countsByType[item.policyType] = (countsByType[item.policyType] || 0) + 1;
    orgPolicyRuleCount += item.rules.length;
  }

  for (const item of authorizationServerPolicies) {
    countsByType[item.policyType] = (countsByType[item.policyType] || 0) + 1;
    authorizationServerPolicyRuleCount += item.rules.length;
  }

  return {
    orgPolicies: orgPolicies.length,
    orgPolicyRules: orgPolicyRuleCount,
    authorizationServerPolicies: authorizationServerPolicies.length,
    authorizationServerPolicyRules: authorizationServerPolicyRuleCount,
    totalPolicies: orgPolicies.length + authorizationServerPolicies.length,
    totalRules: orgPolicyRuleCount + authorizationServerPolicyRuleCount,
    warnings: warnings.length,
    errors: errors.length,
    byPolicyType: countsByType
  };
}

function buildPolicyRows(orgPolicies, authorizationServerPolicies) {
  return [...orgPolicies, ...authorizationServerPolicies].map((item) => {
    const policy = item.policy || {};
    const server = item.authorizationServer || {};
    return {
      source: item.source,
      policyType: item.policyType,
      policyTypeLabel: item.policyTypeLabel,
      authorizationServerId: server.id || '',
      authorizationServerName: server.name || '',
      id: policy.id || '',
      name: policy.name || '',
      status: policy.status || '',
      priority: policy.priority ?? '',
      system: policy.system ?? '',
      created: policy.created || '',
      lastUpdated: policy.lastUpdated || '',
      ruleCount: Array.isArray(item.rules) ? item.rules.length : 0,
      description: policy.description || ''
    };
  });
}

function buildRuleRows(orgPolicies, authorizationServerPolicies) {
  const rows = [];
  for (const item of [...orgPolicies, ...authorizationServerPolicies]) {
    const policy = item.policy || {};
    const server = item.authorizationServer || {};
    for (const rule of item.rules || []) {
      rows.push({
        source: item.source,
        policyType: item.policyType,
        policyTypeLabel: item.policyTypeLabel,
        authorizationServerId: server.id || '',
        authorizationServerName: server.name || '',
        policyId: policy.id || '',
        policyName: policy.name || '',
        id: rule.id || '',
        name: rule.name || '',
        status: rule.status || '',
        priority: rule.priority ?? '',
        created: rule.created || '',
        lastUpdated: rule.lastUpdated || '',
        conditionSummary: flattenForSummary(rule.conditions || ''),
        actionSummary: flattenForSummary(rule.actions || '')
      });
    }
  }
  return rows;
}

function buildManifest(metadata, run) {
  return {
    utility: metadata.utility,
    generatedAt: metadata.generatedAt,
    orgUrl: metadata.orgUrl,
    runName: run.runName,
    files: [
      'policies_full.json',
      'policies_summary.csv',
      'policy_rules.csv',
      'execution_report.json',
      'manifest.json',
      'policies_by_type/'
    ],
    counts: metadata.counts
  };
}

module.exports = {
  exportPolicies,
  buildPolicyRows,
  buildRuleRows,
  filterAuthorizationServers,
  minimizeAuthorizationServer,
  buildCounts
};
