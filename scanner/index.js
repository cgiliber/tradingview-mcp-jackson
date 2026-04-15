#!/usr/bin/env node
/**
 * Market Scanner — lightweight quote tool
 *
 * Primary scanning is now done by trader-scan.js (Finviz, free).
 * This file is kept for quick Twelve Data quotes when needed.
 *
 * Usage:
 *   node scanner/index.js quote META,AMD,NVDA    # Get quotes for specific symbols
 *   node scanner/index.js movers 1               # Find assets that moved >1%
 */

import { readFileSync } from 'fs';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';

const __dirname = dirname(fileURLToPath(import.meta.url));
const ROOT = join(__dirname, '..');

// Load config
const config = JSON.parse(readFileSync(join(__dirname, 'config.json'), 'utf8'));
const activeProvider = config.active_provider;
const providerConfig = config.providers[activeProvider];

// Load API key from .env
function loadApiKey() {
  try {
    const envFile = readFileSync(providerConfig.env_file, 'utf8');
    const match = envFile.match(new RegExp(`${providerConfig.env_key}=(.+)`));
    return match ? match[1].trim() : null;
  } catch (e) {
    console.error(`Cannot read env file: ${providerConfig.env_file}`);
    return null;
  }
}

// Map internal symbol to provider format
function mapSymbol(internalSymbol) {
  const mapping = config.symbol_mapping[activeProvider] || {};
  if (mapping[internalSymbol]) return mapping[internalSymbol];
  const bare = internalSymbol.includes(':') ? internalSymbol.split(':')[1] : internalSymbol;
  for (const [k, v] of Object.entries(mapping)) {
    if (k.endsWith(bare)) return v;
  }
  return bare;
}

// Load watchlist
function loadWatchlist(session = null) {
  const watchlist = JSON.parse(readFileSync(join(ROOT, 'watchlist.json'), 'utf8'));
  const assets = [];
  if (!session || session === 'all') {
    for (const key of ['london_session', 'ny_session', 'crypto_session', 'all_day']) {
      if (watchlist[key]?.assets) assets.push(...watchlist[key].assets);
    }
  } else {
    const sessionKey = { london: 'london_session', ny: 'ny_session', crypto: 'crypto_session', allday: 'all_day' }[session];
    if (sessionKey && watchlist[sessionKey]?.assets) assets.push(...watchlist[sessionKey].assets);
  }
  return assets;
}

// Twelve Data quote
async function twelveDataQuote(symbols, apiKey) {
  const results = [];
  const batchSize = 6;
  const batches = [];
  for (let i = 0; i < symbols.length; i += batchSize) {
    batches.push(symbols.slice(i, i + batchSize));
  }
  for (const batch of batches) {
    const symbolStr = batch.map(s => mapSymbol(s)).join(',');
    const url = `${providerConfig.base_url}/quote?symbol=${symbolStr}&apikey=${apiKey}`;
    try {
      const res = await fetch(url);
      const data = await res.json();
      if (data.status === 'error' && data.code === 429) {
        console.error(`Rate limited: ${data.message}`);
        batch.forEach(sym => results.push({ symbol: sym, error: 'rate limited' }));
        continue;
      }
      if (batch.length === 1) {
        const sym = batch[0];
        if (data.status === 'error') { results.push({ symbol: sym, error: data.message }); }
        else { results.push({ symbol: sym, mapped: mapSymbol(sym), name: data.name, price: parseFloat(data.close), open: parseFloat(data.open), high: parseFloat(data.high), low: parseFloat(data.low), change: parseFloat(data.change), change_pct: parseFloat(data.percent_change), prev_close: parseFloat(data.previous_close), is_market_open: data.is_market_open }); }
      } else {
        for (const sym of batch) {
          const mapped = mapSymbol(sym);
          const d = data[mapped];
          if (!d || d.status === 'error') { results.push({ symbol: sym, mapped, error: d?.message || 'not found' }); }
          else { results.push({ symbol: sym, mapped, name: d.name, price: parseFloat(d.close), open: parseFloat(d.open), high: parseFloat(d.high), low: parseFloat(d.low), change: parseFloat(d.change), change_pct: parseFloat(d.percent_change), prev_close: parseFloat(d.previous_close), is_market_open: d.is_market_open }); }
        }
      }
      if (batches.length > 1) await new Promise(r => setTimeout(r, 8000));
    } catch (e) {
      batch.forEach(sym => results.push({ symbol: sym, error: e.message }));
    }
  }
  return results;
}

// ════════════════════════════════════════
// CLI
// ════════════════════════════════════════

const args = process.argv.slice(2);
const command = args[0];

const apiKey = loadApiKey();
if (!apiKey) {
  console.error(`No API key found. Set ${providerConfig.env_key} in ${providerConfig.env_file}`);
  process.exit(1);
}

if (command === 'quote') {
  const symbols = args[1]?.split(',') || [];
  if (symbols.length === 0) { console.error('Usage: quote SYMBOL1,SYMBOL2,...'); process.exit(1); }
  const results = await twelveDataQuote(symbols, apiKey);
  console.log(JSON.stringify(results, null, 2));

} else if (command === 'movers') {
  const threshold = parseFloat(args[1] || '1');
  const assets = loadWatchlist('all');
  const symbols = [...new Set(assets.map(a => a.symbol))];
  console.log(`Scanning ${symbols.length} assets for moves >${threshold}%...`);
  const results = await twelveDataQuote(symbols, apiKey);
  const movers = results.filter(r => r.change_pct && Math.abs(r.change_pct) >= threshold);
  movers.sort((a, b) => Math.abs(b.change_pct) - Math.abs(a.change_pct));
  movers.forEach(m => {
    const dir = m.change_pct > 0 ? '+' : '';
    console.log(`  ${m.symbol.padEnd(20)} ${m.price?.toFixed(2).padStart(10)}  ${dir}${m.change_pct?.toFixed(2)}%  ${m.name || ''}`);
  });

} else {
  console.log(`
Market Scanner — ${providerConfig.name}

Commands:
  quote META,AMD,NVDA    Get quotes (Twelve Data)
  movers 1               Find watchlist movers >1%

PRIMARY SCANNER: node scanner/trader-scan.js (Finviz, FREE)
  `);
}
