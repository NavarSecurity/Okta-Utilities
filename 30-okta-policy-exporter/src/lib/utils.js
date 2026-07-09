const fs = require('fs');
const path = require('path');

function normalizeOrgUrl(value) {
  if (!value || typeof value !== 'string') return '';
  return value.trim().replace(/\/+$/, '').replace(/\/admin$/, '');
}

function sanitizeOrgUrl(value) {
  const normalized = normalizeOrgUrl(value);
  try {
    const url = new URL(normalized);
    return `${url.protocol}//${url.host}`;
  } catch (_err) {
    return normalized ? '[INVALID_ORG_URL]' : '';
  }
}

function timestampForPath(date = new Date()) {
  return date.toISOString().replace(/[:.]/g, '-');
}

function ensureDir(dirPath) {
  fs.mkdirSync(dirPath, { recursive: true });
}

function readJsonFile(filePath) {
  const fullPath = path.resolve(filePath);
  const raw = fs.readFileSync(fullPath, 'utf8');
  try {
    return JSON.parse(raw);
  } catch (err) {
    throw new Error(`Unable to parse JSON file ${fullPath}: ${err.message}`);
  }
}

function writeJsonFile(filePath, data) {
  ensureDir(path.dirname(filePath));
  fs.writeFileSync(filePath, `${JSON.stringify(data, null, 2)}\n`, 'utf8');
}

function csvEscape(value) {
  if (value === null || value === undefined) return '';
  const stringValue = typeof value === 'string' ? value : JSON.stringify(value);
  if (/[",\n\r]/.test(stringValue)) {
    return `"${stringValue.replace(/"/g, '""')}"`;
  }
  return stringValue;
}

function writeCsvFile(filePath, rows, columns) {
  ensureDir(path.dirname(filePath));
  const lines = [];
  lines.push(columns.map(csvEscape).join(','));
  for (const row of rows) {
    lines.push(columns.map((column) => csvEscape(row[column])).join(','));
  }
  fs.writeFileSync(filePath, `${lines.join('\n')}\n`, 'utf8');
}

function flattenForSummary(value, maxLength = 12000) {
  if (value === undefined || value === null) return '';
  const raw = typeof value === 'string' ? value : JSON.stringify(value);
  if (raw.length <= maxLength) return raw;
  return `${raw.slice(0, maxLength)}...[TRUNCATED]`;
}

function redactSensitive(value) {
  if (Array.isArray(value)) {
    return value.map(redactSensitive);
  }

  if (value && typeof value === 'object') {
    const output = {};
    for (const [key, nestedValue] of Object.entries(value)) {
      if (isSensitiveKey(key)) {
        output[key] = '[REDACTED]';
      } else if (typeof nestedValue === 'string' && looksLikeSensitiveValue(nestedValue)) {
        output[key] = '[REDACTED]';
      } else {
        output[key] = redactSensitive(nestedValue);
      }
    }
    return output;
  }

  if (typeof value === 'string' && looksLikeSensitiveValue(value)) {
    return '[REDACTED]';
  }

  return value;
}

function isSensitiveKey(key) {
  return /^(api[_-]?token|client[_-]?secret|secret|private[_-]?key|authorization|bearer|cookie|session[_-]?token|passcode|shared[_-]?secret)$/i.test(key);
}

function looksLikeSensitiveValue(value) {
  const trimmed = value.trim();
  return /^SSWS\s+[A-Za-z0-9._-]+$/i.test(trimmed) || /^Bearer\s+[A-Za-z0-9._-]+$/i.test(trimmed);
}

function parseArgs(argv) {
  const args = {
    config: 'config.json',
    dryRun: false,
    verbose: false
  };

  for (let i = 0; i < argv.length; i += 1) {
    const arg = argv[i];
    if (arg === '--config' || arg === '-c') {
      args.config = argv[i + 1];
      i += 1;
    } else if (arg === '--dry-run') {
      args.dryRun = true;
    } else if (arg === '--verbose') {
      args.verbose = true;
    } else if (arg === '--help' || arg === '-h') {
      args.help = true;
    } else {
      throw new Error(`Unknown argument: ${arg}`);
    }
  }

  return args;
}

function printHelp() {
  console.log(`okta-policy-exporter\n\nUsage:\n  node src/index.js --config config.json\n  node src/index.js --config config.json --dry-run\n\nOptions:\n  --config, -c   Path to JSON config file. Default: config.json\n  --dry-run      Validate config and show planned export without calling Okta\n  --verbose      Print progress details\n  --help, -h     Show this help text\n`);
}

function validateConfig(config) {
  const warnings = [];

  if (!config || typeof config !== 'object') {
    throw new Error('Config must be a JSON object.');
  }

  if (config.includeOrgPolicies === undefined) config.includeOrgPolicies = true;
  if (config.includeAuthorizationServerPolicies === undefined) config.includeAuthorizationServerPolicies = true;
  if (config.includeRules === undefined) config.includeRules = true;
  if (config.includeRawObjects === undefined) config.includeRawObjects = true;
  if (!config.outputDir) config.outputDir = './output';
  if (!Array.isArray(config.policyTypes)) config.policyTypes = [];
  if (!Array.isArray(config.authorizationServerIds)) config.authorizationServerIds = [];
  if (!config.pageLimit) config.pageLimit = 200;
  if (!config.request) config.request = {};
  if (!config.request.maxRetries && config.request.maxRetries !== 0) config.request.maxRetries = 5;
  if (!config.request.baseDelayMs) config.request.baseDelayMs = 750;
  if (!config.request.timeoutMs) config.request.timeoutMs = 30000;

  if (!config.includeOrgPolicies && !config.includeAuthorizationServerPolicies) {
    throw new Error('At least one of includeOrgPolicies or includeAuthorizationServerPolicies must be true.');
  }

  if (config.includeOrgPolicies && config.policyTypes.length === 0) {
    warnings.push('includeOrgPolicies is true, but policyTypes is empty. No org policy types will be exported.');
  }

  return warnings;
}

function summarizePolicyType(policyType) {
  const map = {
    OKTA_SIGN_ON: 'Global Session / Okta Sign-On Policy',
    ACCESS_POLICY: 'Authentication / App Sign-In Policy',
    PASSWORD: 'Password Policy',
    MFA_ENROLL: 'Authenticator / MFA Enrollment Policy',
    IDP_DISCOVERY: 'Identity Provider Discovery Policy',
    PROFILE_ENROLLMENT: 'Profile Enrollment Policy',
    ACCOUNT_MANAGEMENT: 'Okta Account Management Policy'
  };
  return map[policyType] || policyType;
}

module.exports = {
  normalizeOrgUrl,
  sanitizeOrgUrl,
  timestampForPath,
  ensureDir,
  readJsonFile,
  writeJsonFile,
  writeCsvFile,
  csvEscape,
  flattenForSummary,
  redactSensitive,
  parseArgs,
  printHelp,
  validateConfig,
  summarizePolicyType
};
