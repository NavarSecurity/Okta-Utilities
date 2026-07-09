#!/usr/bin/env node
const path = require('path');
const fs = require('fs');

tryLoadDotenv();

const { OktaClient } = require('./lib/oktaClient');
const {
  parseArgs,
  printHelp,
  readJsonFile,
  validateConfig,
  normalizeOrgUrl,
  sanitizeOrgUrl,
  summarizePolicyType
} = require('./lib/utils');
const { exportPolicies } = require('./lib/exporter');

async function main() {
  const args = parseArgs(process.argv.slice(2));

  if (args.help) {
    printHelp();
    return;
  }

  const configPath = path.resolve(args.config);
  if (!fs.existsSync(configPath)) {
    throw new Error(`Config file not found: ${configPath}`);
  }

  const config = readJsonFile(configPath);
  const configWarnings = validateConfig(config);
  const orgUrl = normalizeOrgUrl(process.env.OKTA_ORG_URL);
  const apiToken = process.env.OKTA_API_TOKEN;

  if (!orgUrl) {
    throw new Error('OKTA_ORG_URL is required. Create .env from .env.example or export OKTA_ORG_URL in your shell.');
  }

  if (!apiToken && !args.dryRun) {
    throw new Error('OKTA_API_TOKEN is required for export runs. Create .env from .env.example or export OKTA_API_TOKEN in your shell.');
  }

  if (args.dryRun) {
    printDryRun({ config, orgUrl, configPath, configWarnings });
    return;
  }

  for (const warning of configWarnings) {
    console.warn(`[config warning] ${warning}`);
  }

  const client = new OktaClient({
    orgUrl,
    apiToken,
    requestConfig: config.request,
    verbose: args.verbose
  });

  const result = await exportPolicies({
    client,
    config,
    orgUrl,
    startedAt: new Date(),
    verbose: args.verbose
  });

  console.log(`Policy export complete: ${result.outputDirectory}`);
  console.log(`Policies: ${result.report.counts.totalPolicies}`);
  console.log(`Rules: ${result.report.counts.totalRules}`);
  console.log(`Warnings: ${result.report.counts.warnings}`);
  console.log(`Errors: ${result.report.counts.errors}`);

  if (result.hasErrors) {
    process.exitCode = 1;
  }
}

function printDryRun({ config, orgUrl, configPath, configWarnings }) {
  console.log('Dry run only. No Okta API calls were made.');
  console.log(`Config: ${configPath}`);
  console.log(`Org: ${sanitizeOrgUrl(orgUrl)}`);
  console.log(`Output directory: ${path.resolve(config.outputDir)}`);
  console.log(`Include org policies: ${config.includeOrgPolicies}`);
  console.log(`Include authorization server policies: ${config.includeAuthorizationServerPolicies}`);
  console.log(`Include rules: ${config.includeRules}`);

  if (config.includeOrgPolicies) {
    console.log('Planned org policy types:');
    for (const type of config.policyTypes) {
      console.log(`  - ${type}: ${summarizePolicyType(type)}`);
    }
  }

  if (config.includeAuthorizationServerPolicies) {
    const ids = config.authorizationServerIds.length > 0 ? config.authorizationServerIds.join(', ') : 'all authorization servers visible to the token';
    console.log(`Planned authorization server policy export: ${ids}`);
  }

  for (const warning of configWarnings) {
    console.warn(`[config warning] ${warning}`);
  }
}

function tryLoadDotenv() {
  try {
    // Optional dependency during test/lint. Installed by npm install for normal use.
    require('dotenv').config();
  } catch (_err) {
    // dotenv is optional for environments that export variables directly.
  }
}

main().catch((err) => {
  console.error(`ERROR: ${err.message}`);
  process.exitCode = 1;
});
