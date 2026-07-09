const test = require('node:test');
const assert = require('node:assert/strict');

const {
  csvEscape,
  normalizeOrgUrl,
  redactSensitive,
  validateConfig,
  summarizePolicyType
} = require('../src/lib/utils');
const { filterAuthorizationServers, buildPolicyRows, buildRuleRows } = require('../src/lib/exporter');
const { getNextLink } = require('../src/lib/oktaClient');

test('normalizeOrgUrl removes trailing slash and admin suffix', () => {
  assert.equal(normalizeOrgUrl('https://example.okta.com/'), 'https://example.okta.com');
  assert.equal(normalizeOrgUrl('https://example.okta.com/admin'), 'https://example.okta.com');
});

test('csvEscape quotes commas, newlines, and double quotes', () => {
  assert.equal(csvEscape('plain'), 'plain');
  assert.equal(csvEscape('a,b'), '"a,b"');
  assert.equal(csvEscape('a"b'), '"a""b"');
  assert.equal(csvEscape('a\nb'), '"a\nb"');
});

test('redactSensitive redacts secrets but keeps password policy content', () => {
  const redacted = redactSensitive({
    clientSecret: 'abc123',
    type: 'PASSWORD',
    actions: {
      passwordChange: {
        access: 'ALLOW'
      },
      accessTokenLifetimeMinutes: 60
    }
  });

  assert.equal(redacted.clientSecret, '[REDACTED]');
  assert.equal(redacted.type, 'PASSWORD');
  assert.equal(redacted.actions.passwordChange.access, 'ALLOW');
  assert.equal(redacted.actions.accessTokenLifetimeMinutes, 60);
});

test('getNextLink extracts next URL from Okta Link header', () => {
  const header = '<https://example.okta.com/api/v1/policies?after=abc>; rel="next", <https://example.okta.com/api/v1/policies>; rel="self"';
  assert.equal(getNextLink(header), 'https://example.okta.com/api/v1/policies?after=abc');
});

test('validateConfig applies defaults', () => {
  const config = { includeOrgPolicies: true, policyTypes: ['PASSWORD'] };
  const warnings = validateConfig(config);
  assert.deepEqual(warnings, []);
  assert.equal(config.includeRules, true);
  assert.equal(config.outputDir, './output');
  assert.equal(config.request.maxRetries, 5);
});

test('summarizePolicyType maps common Okta policy types', () => {
  assert.equal(summarizePolicyType('MFA_ENROLL'), 'Authenticator / MFA Enrollment Policy');
  assert.equal(summarizePolicyType('CUSTOM'), 'CUSTOM');
});

test('filterAuthorizationServers filters by id or name', () => {
  const servers = [
    { id: 'default', name: 'default' },
    { id: 'aus123', name: 'Partner API' }
  ];
  assert.deepEqual(filterAuthorizationServers(servers, ['partner api']), [{ id: 'aus123', name: 'Partner API' }]);
  assert.deepEqual(filterAuthorizationServers(servers, ['default']), [{ id: 'default', name: 'default' }]);
});

test('buildPolicyRows and buildRuleRows create flat evidence rows', () => {
  const items = [
    {
      source: 'orgPolicy',
      policyType: 'PASSWORD',
      policyTypeLabel: 'Password Policy',
      policy: { id: 'pol1', name: 'Default Password', status: 'ACTIVE', priority: 1 },
      rules: [
        { id: 'r1', name: 'Default Rule', status: 'ACTIVE', priority: 1, conditions: { people: {} }, actions: { passwordChange: { access: 'ALLOW' } } }
      ]
    }
  ];

  const policyRows = buildPolicyRows(items, []);
  const ruleRows = buildRuleRows(items, []);

  assert.equal(policyRows[0].id, 'pol1');
  assert.equal(policyRows[0].ruleCount, 1);
  assert.equal(ruleRows[0].policyId, 'pol1');
  assert.match(ruleRows[0].actionSummary, /passwordChange/);
});
