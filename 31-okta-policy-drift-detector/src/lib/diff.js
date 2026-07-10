const {
  pickFields,
  normalizeValue,
  hashComparable,
  buildPolicyIdentity,
  buildRuleIdentity
} = require('./normalize');

function compareExports(sourceExport, targetExport, config) {
  const policyComparisons = comparePolicyMaps(sourceExport, targetExport, config);
  const ruleComparisons = compareRuleMaps(sourceExport, targetExport, config);
  const duplicateWarnings = [
    ...policyComparisons.duplicateWarnings,
    ...ruleComparisons.duplicateWarnings
  ];

  const driftItems = [
    ...policyComparisons.items,
    ...ruleComparisons.items
  ];

  const summary = summarizeDrift(driftItems, duplicateWarnings, sourceExport, targetExport);

  return {
    summary,
    policyDrift: policyComparisons.items,
    ruleDrift: ruleComparisons.items,
    duplicateWarnings,
    driftItems
  };
}

function comparePolicyMaps(sourceExport, targetExport, config) {
  const sourceMap = buildPolicyMap(sourceExport.policies, config, sourceExport.label);
  const targetMap = buildPolicyMap(targetExport.policies, config, targetExport.label);
  const items = compareMaps({
    itemType: 'policy',
    sourceMap: sourceMap.map,
    targetMap: targetMap.map,
    sourceLabel: sourceExport.label,
    targetLabel: targetExport.label,
    includeEqualItems: config.includeEqualItems
  });
  return {
    items,
    duplicateWarnings: [...sourceMap.duplicateWarnings, ...targetMap.duplicateWarnings]
  };
}

function compareRuleMaps(sourceExport, targetExport, config) {
  const sourceMap = buildRuleMap(sourceExport.policies, config, sourceExport.label);
  const targetMap = buildRuleMap(targetExport.policies, config, targetExport.label);
  const items = compareMaps({
    itemType: 'rule',
    sourceMap: sourceMap.map,
    targetMap: targetMap.map,
    sourceLabel: sourceExport.label,
    targetLabel: targetExport.label,
    includeEqualItems: config.includeEqualItems
  });
  return {
    items,
    duplicateWarnings: [...sourceMap.duplicateWarnings, ...targetMap.duplicateWarnings]
  };
}

function buildPolicyMap(policies, config, label) {
  const map = new Map();
  const duplicateWarnings = [];
  for (const row of policies) {
    const key = buildPolicyIdentity(row, config.identityMode);
    const selected = pickFields(row.policy || {}, config.compare.includePolicyFields || []);
    const normalized = normalizeValue(selected, config.compare);
    addMapEntry(map, key, {
      key,
      label,
      name: row.policy?.name || '',
      policyType: row.policyType || '',
      source: row.source || '',
      authorizationServerName: row.authorizationServer?.name || '',
      normalized,
      raw: row.policy || {}
    }, duplicateWarnings, 'policy', label);
  }
  return { map, duplicateWarnings };
}

function buildRuleMap(policies, config, label) {
  const map = new Map();
  const duplicateWarnings = [];
  for (const row of policies) {
    const policyKey = buildPolicyIdentity(row, config.identityMode);
    for (const rule of row.rules || []) {
      const key = buildRuleIdentity(policyKey, rule);
      const selected = pickFields(rule || {}, config.compare.includeRuleFields || []);
      const normalized = normalizeValue(selected, config.compare);
      addMapEntry(map, key, {
        key,
        label,
        name: rule?.name || '',
        policyName: row.policy?.name || '',
        policyType: row.policyType || '',
        ruleType: rule?.type || '',
        source: row.source || '',
        authorizationServerName: row.authorizationServer?.name || '',
        normalized,
        raw: rule || {}
      }, duplicateWarnings, 'rule', label);
    }
  }
  return { map, duplicateWarnings };
}

function addMapEntry(map, key, value, duplicateWarnings, itemType, label) {
  if (map.has(key)) {
    duplicateWarnings.push({
      label,
      itemType,
      key,
      message: `Duplicate ${itemType} identity detected in ${label}. The first item was kept and the duplicate was ignored.`
    });
    return;
  }
  map.set(key, value);
}

function compareMaps({ itemType, sourceMap, targetMap, sourceLabel, targetLabel, includeEqualItems }) {
  const allKeys = new Set([...sourceMap.keys(), ...targetMap.keys()]);
  const items = [];

  for (const key of [...allKeys].sort()) {
    const sourceItem = sourceMap.get(key);
    const targetItem = targetMap.get(key);

    if (!sourceItem) {
      items.push({
        itemType,
        driftType: 'EXTRA_IN_TARGET',
        severity: 'HIGH',
        key,
        name: targetItem.name,
        policyName: targetItem.policyName || targetItem.name,
        policyType: targetItem.policyType,
        ruleType: targetItem.ruleType || '',
        source: targetItem.source,
        authorizationServerName: targetItem.authorizationServerName || '',
        message: `${itemType} exists in ${targetLabel} but not in ${sourceLabel}.`,
        diffCount: 1,
        differences: [
          {
            path: '$',
            sourceValue: null,
            targetValue: targetItem.normalized
          }
        ]
      });
      continue;
    }

    if (!targetItem) {
      items.push({
        itemType,
        driftType: 'MISSING_IN_TARGET',
        severity: 'HIGH',
        key,
        name: sourceItem.name,
        policyName: sourceItem.policyName || sourceItem.name,
        policyType: sourceItem.policyType,
        ruleType: sourceItem.ruleType || '',
        source: sourceItem.source,
        authorizationServerName: sourceItem.authorizationServerName || '',
        message: `${itemType} exists in ${sourceLabel} but not in ${targetLabel}.`,
        diffCount: 1,
        differences: [
          {
            path: '$',
            sourceValue: sourceItem.normalized,
            targetValue: null
          }
        ]
      });
      continue;
    }

    if (hashComparable(sourceItem.normalized) !== hashComparable(targetItem.normalized)) {
      const differences = diffValues(sourceItem.normalized, targetItem.normalized);
      items.push({
        itemType,
        driftType: 'MODIFIED',
        severity: calculateSeverity(differences),
        key,
        name: sourceItem.name || targetItem.name,
        policyName: sourceItem.policyName || targetItem.policyName || sourceItem.name || targetItem.name,
        policyType: sourceItem.policyType || targetItem.policyType,
        ruleType: sourceItem.ruleType || targetItem.ruleType || '',
        source: sourceItem.source || targetItem.source,
        authorizationServerName: sourceItem.authorizationServerName || targetItem.authorizationServerName || '',
        message: `${itemType} exists in both exports but has configuration drift.`,
        diffCount: differences.length,
        differences
      });
    } else if (includeEqualItems) {
      items.push({
        itemType,
        driftType: 'MATCHED',
        severity: 'INFO',
        key,
        name: sourceItem.name || targetItem.name,
        policyName: sourceItem.policyName || targetItem.policyName || sourceItem.name || targetItem.name,
        policyType: sourceItem.policyType || targetItem.policyType,
        ruleType: sourceItem.ruleType || targetItem.ruleType || '',
        source: sourceItem.source || targetItem.source,
        authorizationServerName: sourceItem.authorizationServerName || targetItem.authorizationServerName || '',
        message: `${itemType} exists in both exports and matched after normalization.`,
        diffCount: 0,
        differences: []
      });
    }
  }

  return items;
}

function diffValues(sourceValue, targetValue, path = '$') {
  if (hashComparable(sourceValue) === hashComparable(targetValue)) {
    return [];
  }

  if (!isObjectLike(sourceValue) || !isObjectLike(targetValue)) {
    return [{ path, sourceValue, targetValue }];
  }

  if (Array.isArray(sourceValue) || Array.isArray(targetValue)) {
    return [{ path, sourceValue, targetValue }];
  }

  const keys = new Set([...Object.keys(sourceValue), ...Object.keys(targetValue)]);
  const diffs = [];
  for (const key of [...keys].sort()) {
    diffs.push(...diffValues(sourceValue[key], targetValue[key], `${path}.${key}`));
  }
  return diffs;
}

function isObjectLike(value) {
  return value !== null && typeof value === 'object';
}

function calculateSeverity(differences) {
  const highPatterns = ['.actions', '.conditions', '.settings', '.status'];
  const mediumPatterns = ['.priority', '.type', '.system'];

  if (differences.some((diff) => highPatterns.some((pattern) => diff.path.includes(pattern)))) {
    return 'HIGH';
  }
  if (differences.some((diff) => mediumPatterns.some((pattern) => diff.path.includes(pattern)))) {
    return 'MEDIUM';
  }
  return 'LOW';
}

function summarizeDrift(items, duplicateWarnings, sourceExport, targetExport) {
  const driftOnly = items.filter((item) => item.driftType !== 'MATCHED');
  const byType = countBy(driftOnly, 'driftType');
  const bySeverity = countBy(driftOnly, 'severity');
  const byItemType = countBy(driftOnly, 'itemType');
  return {
    sourceLabel: sourceExport.label,
    targetLabel: targetExport.label,
    sourcePath: sourceExport.path,
    targetPath: targetExport.path,
    sourcePolicyCount: sourceExport.policies.length,
    targetPolicyCount: targetExport.policies.length,
    sourceRuleCount: sourceExport.policies.reduce((sum, row) => sum + (row.rules || []).length, 0),
    targetRuleCount: targetExport.policies.reduce((sum, row) => sum + (row.rules || []).length, 0),
    driftFound: driftOnly.length > 0,
    driftItemCount: driftOnly.length,
    policyDriftCount: driftOnly.filter((item) => item.itemType === 'policy').length,
    ruleDriftCount: driftOnly.filter((item) => item.itemType === 'rule').length,
    duplicateWarningCount: duplicateWarnings.length,
    byType,
    bySeverity,
    byItemType
  };
}

function countBy(items, field) {
  return items.reduce((acc, item) => {
    const key = item[field] || 'UNKNOWN';
    acc[key] = (acc[key] || 0) + 1;
    return acc;
  }, {});
}

module.exports = {
  compareExports,
  buildPolicyMap,
  buildRuleMap,
  diffValues,
  summarizeDrift
};
