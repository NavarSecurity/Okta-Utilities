const fs = require('fs');
const path = require('path');

function readJsonFile(filePath) {
  try {
    return JSON.parse(fs.readFileSync(filePath, 'utf8'));
  } catch (error) {
    throw new Error(`Unable to read JSON file ${filePath}: ${error.message}`);
  }
}

function parseArgs(argv) {
  const args = {
    configPath: 'config.json',
    strict: false,
    help: false
  };

  for (let i = 2; i < argv.length; i += 1) {
    const token = argv[i];
    if (token === '--config') {
      args.configPath = argv[i + 1];
      i += 1;
    } else if (token === '--strict') {
      args.strict = true;
    } else if (token === '--help' || token === '-h') {
      args.help = true;
    } else {
      throw new Error(`Unknown argument: ${token}`);
    }
  }

  return args;
}

function mergeDefaults(config, configPath, strictFlag = false) {
  const baseDir = path.dirname(path.resolve(configPath));
  const merged = {
    sourceLabel: config.sourceLabel || 'source',
    targetLabel: config.targetLabel || 'target',
    sourceExportPath: config.sourceExportPath,
    targetExportPath: config.targetExportPath,
    outputDir: config.outputDir || 'output',
    identityMode: config.identityMode || 'name_type_scope',
    failOnDrift: Boolean(config.failOnDrift || strictFlag),
    includeEqualItems: Boolean(config.includeEqualItems),
    compare: {
      includePolicyFields: [
        'status',
        'name',
        'description',
        'priority',
        'system',
        'type',
        'conditions',
        'actions',
        'settings'
      ],
      includeRuleFields: [
        'status',
        'name',
        'priority',
        'system',
        'type',
        'conditions',
        'actions'
      ],
      ignorePaths: [],
      ignoreFields: ['id', 'created', 'lastUpdated', '_links', 'links'],
      sortPrimitiveArrays: true,
      normalizeOrgUrls: true,
      referenceMapPath: '',
      ...(config.compare || {})
    }
  };

  if (!merged.sourceExportPath) {
    throw new Error('config.sourceExportPath is required.');
  }
  if (!merged.targetExportPath) {
    throw new Error('config.targetExportPath is required.');
  }

  merged.sourceExportPath = resolveInputPath(baseDir, merged.sourceExportPath);
  merged.targetExportPath = resolveInputPath(baseDir, merged.targetExportPath);
  merged.outputDir = resolveOutputPath(merged.outputDir);

  if (merged.compare.referenceMapPath) {
    merged.compare.referenceMapPath = resolveInputPath(baseDir, merged.compare.referenceMapPath);
    merged.compare.referenceMap = readJsonFile(merged.compare.referenceMapPath);
  } else {
    merged.compare.referenceMap = {};
  }

  return merged;
}

function resolveInputPath(baseDir, maybeRelative) {
  if (!maybeRelative) return maybeRelative;
  if (path.isAbsolute(maybeRelative)) return maybeRelative;

  const fromCwd = path.resolve(process.cwd(), maybeRelative);
  if (fs.existsSync(fromCwd)) return fromCwd;

  return path.resolve(baseDir, maybeRelative);
}

function resolveOutputPath(maybeRelative) {
  if (!maybeRelative) return maybeRelative;
  return path.isAbsolute(maybeRelative) ? maybeRelative : path.resolve(process.cwd(), maybeRelative);
}

function showHelp() {
  return `Usage:\n  node src/index.js --config config.json\n\nOptions:\n  --config <path>   Path to config JSON. Defaults to config.json.\n  --strict          Return exit code 2 when drift is found.\n  --help, -h        Show this message.\n`;
}

module.exports = {
  parseArgs,
  readJsonFile,
  mergeDefaults,
  showHelp
};
