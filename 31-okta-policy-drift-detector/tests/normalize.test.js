const test = require('node:test');
const assert = require('node:assert/strict');
const {
  normalizeValue,
  pickFields,
  buildPolicyIdentity,
  buildRuleIdentity
} = require('../src/lib/normalize');

test('normalizeValue removes volatile fields and sorts primitive arrays', () => {
  const input = {
    id: '00p123',
    name: 'Policy',
    created: '2026-01-01T00:00:00.000Z',
    conditions: {
      clients: {
        include: ['b', 'a']
      }
    },
    _links: {
      self: {
        href: 'https://example.okta.com/api/v1/policies/00p123'
      }
    }
  };

  const normalized = normalizeValue(input, {
    ignoreFields: ['id', 'created', '_links'],
    ignorePaths: [],
    sortPrimitiveArrays: true,
    normalizeOrgUrls: true,
    referenceMap: {}
  });

  assert.deepEqual(normalized, {
    conditions: {
      clients: {
        include: ['a', 'b']
      }
    },
    name: 'Policy'
  });
});

test('normalizeValue applies reference map', () => {
  const normalized = normalizeValue(
    { conditions: { people: { groups: { include: ['00gSource'] } } } },
    {
      ignoreFields: [],
      ignorePaths: [],
      sortPrimitiveArrays: true,
      normalizeOrgUrls: true,
      referenceMap: {
        '00gSource': '00gTarget'
      }
    }
  );

  assert.equal(normalized.conditions.people.groups.include[0], '00gTarget');
});

test('pickFields only keeps requested fields', () => {
  assert.deepEqual(pickFields({ a: 1, b: 2, c: 3 }, ['a', 'c', 'z']), { a: 1, c: 3 });
});

test('policy and rule identities use names and scope by default', () => {
  const row = {
    source: 'authorizationServerPolicy',
    policyType: 'AUTHORIZATION_SERVER_ACCESS_POLICY',
    authorizationServer: {
      name: 'Example API'
    },
    policy: {
      name: 'Default API Access Policy'
    }
  };
  const policyKey = buildPolicyIdentity(row, 'name_type_scope');
  const ruleKey = buildRuleIdentity(policyKey, { type: 'RESOURCE_ACCESS', name: 'Authorization Code Access' });

  assert.equal(policyKey, 'authorizationServerPolicy::AUTHORIZATION_SERVER_ACCESS_POLICY::Example API::Default API Access Policy');
  assert.equal(ruleKey, 'authorizationServerPolicy::AUTHORIZATION_SERVER_ACCESS_POLICY::Example API::Default API Access Policy::rule::RESOURCE_ACCESS::Authorization Code Access');
});
