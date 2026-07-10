const test = require('node:test');
const assert = require('node:assert/strict');
const { compareExports, diffValues } = require('../src/lib/diff');

function baseConfig() {
  return {
    identityMode: 'name_type_scope',
    includeEqualItems: false,
    compare: {
      includePolicyFields: ['status', 'name', 'priority', 'type', 'conditions'],
      includeRuleFields: ['status', 'name', 'priority', 'type', 'conditions', 'actions'],
      ignoreFields: ['id', 'created', 'lastUpdated', '_links'],
      ignorePaths: [],
      sortPrimitiveArrays: true,
      normalizeOrgUrls: true,
      referenceMap: {}
    }
  };
}

function exportWithRule(requireFactor) {
  return {
    label: requireFactor ? 'target' : 'source',
    path: '/tmp/export.json',
    policies: [
      {
        source: 'orgPolicy',
        policyType: 'OKTA_SIGN_ON',
        authorizationServer: null,
        policy: {
          id: requireFactor ? 'target-policy-id' : 'source-policy-id',
          status: 'ACTIVE',
          name: 'Default Policy',
          priority: 1,
          type: 'OKTA_SIGN_ON'
        },
        rules: [
          {
            id: requireFactor ? 'target-rule-id' : 'source-rule-id',
            status: 'ACTIVE',
            name: 'Default Rule',
            priority: 1,
            type: 'SIGN_ON',
            actions: {
              signon: {
                access: 'ALLOW',
                requireFactor
              }
            }
          }
        ]
      }
    ]
  };
}

test('diffValues returns only changed leaf paths for objects', () => {
  const diffs = diffValues(
    { actions: { signon: { requireFactor: false, access: 'ALLOW' } } },
    { actions: { signon: { requireFactor: true, access: 'ALLOW' } } }
  );

  assert.deepEqual(diffs, [
    {
      path: '$.actions.signon.requireFactor',
      sourceValue: false,
      targetValue: true
    }
  ]);
});

test('compareExports detects modified rule drift after ignoring IDs', () => {
  const result = compareExports(exportWithRule(false), exportWithRule(true), baseConfig());
  assert.equal(result.summary.driftFound, true);
  assert.equal(result.summary.policyDriftCount, 0);
  assert.equal(result.summary.ruleDriftCount, 1);
  assert.equal(result.ruleDrift[0].driftType, 'MODIFIED');
  assert.equal(result.ruleDrift[0].severity, 'HIGH');
  assert.equal(result.ruleDrift[0].differences[0].path, '$.actions.signon.requireFactor');
});

test('compareExports detects missing policy', () => {
  const source = exportWithRule(false);
  const target = { ...exportWithRule(false), policies: [] };
  const result = compareExports(source, target, baseConfig());

  assert.equal(result.summary.driftFound, true);
  assert.equal(result.policyDrift[0].driftType, 'MISSING_IN_TARGET');
  assert.equal(result.ruleDrift[0].driftType, 'MISSING_IN_TARGET');
});
