#!/usr/bin/env node
const { parseArgs, readJsonFile, mergeDefaults, showHelp } = require('./lib/config');
const { loadPolicyExport } = require('./lib/loadExport');
const { compareExports } = require('./lib/diff');
const { writeReports } = require('./lib/reporters');

async function main() {
  const startedAt = new Date();
  const args = parseArgs(process.argv);

  if (args.help) {
    console.log(showHelp());
    return;
  }

  const rawConfig = readJsonFile(args.configPath);
  const config = mergeDefaults(rawConfig, args.configPath, args.strict);

  console.log('Okta Policy Drift Detector');
  console.log(`Source: ${config.sourceLabel}`);
  console.log(`Target: ${config.targetLabel}`);
  console.log(`Source export: ${config.sourceExportPath}`);
  console.log(`Target export: ${config.targetExportPath}`);

  const sourceExport = loadPolicyExport(config.sourceExportPath, config.sourceLabel);
  const targetExport = loadPolicyExport(config.targetExportPath, config.targetLabel);

  const result = compareExports(sourceExport, targetExport, config);
  const finishedAt = new Date();
  const reportInfo = writeReports(result, config, startedAt, finishedAt);

  console.log('');
  console.log('Comparison complete.');
  console.log(`Drift found: ${result.summary.driftFound ? 'YES' : 'NO'}`);
  console.log(`Drift items: ${result.summary.driftItemCount}`);
  console.log(`Policy drift: ${result.summary.policyDriftCount}`);
  console.log(`Rule drift: ${result.summary.ruleDriftCount}`);
  console.log(`Output: ${reportInfo.runDir}`);

  if (config.failOnDrift && result.summary.driftFound) {
    process.exitCode = 2;
  }
}

main().catch((error) => {
  console.error(`ERROR: ${error.message}`);
  process.exitCode = 1;
});
