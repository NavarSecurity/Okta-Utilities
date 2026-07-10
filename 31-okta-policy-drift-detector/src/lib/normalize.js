function pickFields(object, fields) {
  const picked = {};
  for (const field of fields) {
    if (Object.prototype.hasOwnProperty.call(object, field)) {
      picked[field] = object[field];
    }
  }
  return picked;
}

function normalizeValue(value, options = {}, currentPath = '') {
  const ignoreFields = new Set(options.ignoreFields || []);
  const ignorePaths = new Set(options.ignorePaths || []);
  const referenceMap = options.referenceMap || {};

  if (ignorePaths.has(currentPath)) {
    return undefined;
  }

  if (value === null || typeof value !== 'object') {
    return normalizeScalar(value, options, referenceMap);
  }

  if (Array.isArray(value)) {
    const normalizedArray = value
      .map((item, index) => normalizeValue(item, options, joinPath(currentPath, String(index))))
      .filter((item) => item !== undefined);

    if (options.sortPrimitiveArrays && normalizedArray.every(isPrimitiveComparable)) {
      return normalizedArray.sort((a, b) => JSON.stringify(a).localeCompare(JSON.stringify(b)));
    }

    return normalizedArray;
  }

  const result = {};
  for (const key of Object.keys(value).sort()) {
    if (ignoreFields.has(key)) {
      continue;
    }

    const childPath = joinPath(currentPath, key);
    if (ignorePaths.has(childPath)) {
      continue;
    }

    const normalized = normalizeValue(value[key], options, childPath);
    if (normalized !== undefined) {
      result[key] = normalized;
    }
  }
  return result;
}

function normalizeScalar(value, options, referenceMap) {
  if (typeof value === 'string') {
    let normalized = Object.prototype.hasOwnProperty.call(referenceMap, value) ? referenceMap[value] : value;
    if (options.normalizeOrgUrls) {
      normalized = normalized.replace(/https:\/\/[^/\s"']+\.okta(?:preview)?\.com/g, '<OKTA_ORG_URL>');
      normalized = normalized.replace(/https:\/\/[^/\s"']+\.okta-emea\.com/g, '<OKTA_ORG_URL>');
      normalized = normalized.replace(/https:\/\/[^/\s"']+\.okta-gov\.com/g, '<OKTA_ORG_URL>');
    }
    return normalized;
  }
  return value;
}

function isPrimitiveComparable(value) {
  return value === null || ['string', 'number', 'boolean'].includes(typeof value);
}

function joinPath(parent, child) {
  return parent ? `${parent}.${child}` : child;
}

function canonicalJson(value) {
  return JSON.stringify(value, null, 2);
}

function hashComparable(value) {
  return JSON.stringify(value);
}

function buildPolicyIdentity(row, identityMode = 'name_type_scope') {
  const policyName = row.policy?.name || '<unnamed-policy>';
  const policyType = row.policyType || row.policy?.type || 'UNKNOWN';
  const source = row.source || 'policy';
  const authServerName = row.authorizationServer?.name || '';
  const authServerAudience = Array.isArray(row.authorizationServer?.audience)
    ? row.authorizationServer.audience.join(',')
    : row.authorizationServer?.audience || '';

  if (identityMode === 'id') {
    return row.policy?.id || `${source}::${policyType}::${authServerName}::${policyName}`;
  }

  if (source === 'authorizationServerPolicy') {
    return `${source}::${policyType}::${authServerName || authServerAudience || '<unknown-auth-server>'}::${policyName}`;
  }

  return `${source}::${policyType}::${policyName}`;
}

function buildRuleIdentity(policyIdentity, rule) {
  const ruleName = rule?.name || '<unnamed-rule>';
  const ruleType = rule?.type || 'UNKNOWN_RULE_TYPE';
  return `${policyIdentity}::rule::${ruleType}::${ruleName}`;
}

module.exports = {
  pickFields,
  normalizeValue,
  canonicalJson,
  hashComparable,
  buildPolicyIdentity,
  buildRuleIdentity
};
