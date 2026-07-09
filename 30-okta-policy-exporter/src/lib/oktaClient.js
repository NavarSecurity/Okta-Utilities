const { setTimeout: sleep } = require('timers/promises');
const { normalizeOrgUrl } = require('./utils');

class OktaClient {
  constructor({ orgUrl, apiToken, requestConfig = {}, verbose = false }) {
    this.orgUrl = normalizeOrgUrl(orgUrl);
    this.apiToken = apiToken;
    this.maxRetries = requestConfig.maxRetries ?? 5;
    this.baseDelayMs = requestConfig.baseDelayMs ?? 750;
    this.timeoutMs = requestConfig.timeoutMs ?? 30000;
    this.verbose = verbose;
  }

  async get(pathOrUrl) {
    return this.request('GET', pathOrUrl);
  }

  async getAll(pathOrUrl) {
    const results = [];
    let nextUrl = pathOrUrl;

    while (nextUrl) {
      const { data, headers } = await this.get(nextUrl);
      if (Array.isArray(data)) {
        results.push(...data);
      } else if (data && Array.isArray(data.items)) {
        results.push(...data.items);
      } else if (data) {
        results.push(data);
      }
      nextUrl = getNextLink(headers.get('link'));
    }

    return results;
  }

  async request(method, pathOrUrl) {
    if (!this.orgUrl) throw new Error('OKTA_ORG_URL is required.');
    if (!this.apiToken) throw new Error('OKTA_API_TOKEN is required.');

    const url = buildUrl(this.orgUrl, pathOrUrl);
    let lastError;

    for (let attempt = 0; attempt <= this.maxRetries; attempt += 1) {
      const controller = new AbortController();
      const timeout = setTimeout(() => controller.abort(), this.timeoutMs);

      try {
        if (this.verbose) {
          console.log(`[okta] ${method} ${redactUrl(url)}`);
        }

        const response = await fetch(url, {
          method,
          headers: {
            Accept: 'application/json',
            'Content-Type': 'application/json',
            Authorization: `SSWS ${this.apiToken}`
          },
          signal: controller.signal
        });

        clearTimeout(timeout);

        if (response.ok) {
          const text = await response.text();
          const data = text ? JSON.parse(text) : null;
          return { data, headers: response.headers, status: response.status };
        }

        const errorBody = await safeReadResponse(response);
        const retryAfterMs = parseRetryAfter(response.headers.get('retry-after'));
        const retriable = response.status === 429 || response.status >= 500;

        lastError = new Error(
          `Okta API request failed: ${method} ${redactUrl(url)} returned ${response.status} ${response.statusText}. ${errorBody}`.trim()
        );
        lastError.status = response.status;
        lastError.body = errorBody;

        if (!retriable || attempt === this.maxRetries) {
          throw lastError;
        }

        await sleep(retryAfterMs ?? backoffMs(this.baseDelayMs, attempt));
      } catch (err) {
        clearTimeout(timeout);
        lastError = err;

        if (err.name === 'AbortError') {
          lastError = new Error(`Okta API request timed out after ${this.timeoutMs}ms: ${method} ${redactUrl(url)}`);
        }

        if (attempt === this.maxRetries) {
          throw lastError;
        }

        await sleep(backoffMs(this.baseDelayMs, attempt));
      }
    }

    throw lastError;
  }
}

function buildUrl(orgUrl, pathOrUrl) {
  if (/^https?:\/\//i.test(pathOrUrl)) return pathOrUrl;
  const normalizedPath = pathOrUrl.startsWith('/') ? pathOrUrl : `/${pathOrUrl}`;
  return `${orgUrl}${normalizedPath}`;
}

function getNextLink(linkHeader) {
  if (!linkHeader) return null;
  const links = linkHeader.split(',').map((part) => part.trim());
  for (const link of links) {
    const match = link.match(/<([^>]+)>;\s*rel="next"/i);
    if (match) return match[1];
  }
  return null;
}

function parseRetryAfter(value) {
  if (!value) return null;
  const seconds = Number.parseInt(value, 10);
  if (!Number.isNaN(seconds)) return seconds * 1000;
  const date = Date.parse(value);
  if (!Number.isNaN(date)) return Math.max(0, date - Date.now());
  return null;
}

function backoffMs(baseDelayMs, attempt) {
  const jitter = Math.floor(Math.random() * 250);
  return baseDelayMs * (2 ** attempt) + jitter;
}

async function safeReadResponse(response) {
  try {
    const text = await response.text();
    if (!text) return '';
    const parsed = JSON.parse(text);
    return JSON.stringify(parsed);
  } catch (_err) {
    return '';
  }
}

function redactUrl(value) {
  try {
    const url = new URL(value);
    return `${url.origin}${url.pathname}${url.search}`;
  } catch (_err) {
    return value;
  }
}

module.exports = {
  OktaClient,
  getNextLink,
  parseRetryAfter,
  buildUrl
};
