#!/usr/bin/env node
/**
 * Market Scanner — Provider-agnostic market data scanner
 *
 * Usage:
 *   node scanner/index.js quote META,AMD,NVDA          # Get quotes for specific symbols
 *   node scanner/index.js scan watchlist                 # Scan all watchlist assets
 *   node scanner/index.js scan penny                    # Scan penny stock candidates
 *   node scanner/index.js scan session london           # Scan London session assets
 *   node scanner/index.js scan session ny               # Scan NY session assets
 *   node scanner/index.js scan session crypto           # Scan crypto session assets
 *   node scanner/index.js movers 1                      # Find assets that moved >1%
 *
 * To switch providers: edit scanner/config.json → active_provider
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
  // Try exact match first
  if (mapping[internalSymbol]) return mapping[internalSymbol];
  // Try without exchange prefix
  const bare = internalSymbol.includes(':') ? internalSymbol.split(':')[1] : internalSymbol;
  for (const [k, v] of Object.entries(mapping)) {
    if (k.endsWith(bare)) return v;
  }
  // Default: return bare symbol (works for US stocks)
  return bare;
}

// Load watchlist
function loadWatchlist(session = null) {
  const watchlist = JSON.parse(readFileSync(join(ROOT, 'watchlist.json'), 'utf8'));
  const assets = [];

  if (!session || session === 'all') {
    for (const key of ['london_session', 'ny_session', 'crypto_session', 'all_day']) {
      if (watchlist[key]?.assets) {
        assets.push(...watchlist[key].assets);
      }
    }
  } else {
    const sessionKey = {
      london: 'london_session',
      ny: 'ny_session',
      crypto: 'crypto_session',
      allday: 'all_day'
    }[session];
    if (sessionKey && watchlist[sessionKey]?.assets) {
      assets.push(...watchlist[sessionKey].assets);
    }
  }

  return assets;
}

// ════════════════════════════════════════
// PROVIDER: Twelve Data
// ════════════════════════════════════════

async function twelveDataQuote(symbols, apiKey) {
  const results = [];
  // Twelve Data allows up to 12 symbols per batch request
  const batches = [];
  for (let i = 0; i < symbols.length; i += 12) {
    batches.push(symbols.slice(i, i + 12));
  }

  for (const batch of batches) {
    const symbolStr = batch.map(s => mapSymbol(s)).join(',');
    const url = `${providerConfig.base_url}/quote?symbol=${symbolStr}&apikey=${apiKey}`;

    try {
      const res = await fetch(url);
      const data = await res.json();

      if (batch.length === 1) {
        // Single symbol returns object directly
        const sym = batch[0];
        if (data.status === 'error') {
          results.push({ symbol: sym, error: data.message });
        } else {
          results.push({
            symbol: sym,
            mapped: mapSymbol(sym),
            name: data.name,
            price: parseFloat(data.close),
            open: parseFloat(data.open),
            high: parseFloat(data.high),
            low: parseFloat(data.low),
            change: parseFloat(data.change),
            change_pct: parseFloat(data.percent_change),
            prev_close: parseFloat(data.previous_close),
            is_market_open: data.is_market_open
          });
        }
      } else {
        // Multiple symbols returns object keyed by symbol
        for (const sym of batch) {
          const mapped = mapSymbol(sym);
          const d = data[mapped];
          if (!d || d.status === 'error') {
            results.push({ symbol: sym, mapped, error: d?.message || 'not found' });
          } else {
            results.push({
              symbol: sym,
              mapped,
              name: d.name,
              price: parseFloat(d.close),
              open: parseFloat(d.open),
              high: parseFloat(d.high),
              low: parseFloat(d.low),
              change: parseFloat(d.change),
              change_pct: parseFloat(d.percent_change),
              prev_close: parseFloat(d.previous_close),
              is_market_open: d.is_market_open
            });
          }
        }
      }

      // Rate limit: small delay between batches
      if (batches.length > 1) await new Promise(r => setTimeout(r, 500));
    } catch (e) {
      batch.forEach(sym => results.push({ symbol: sym, error: e.message }));
    }
  }

  return results;
}

// ════════════════════════════════════════
// GENERIC INTERFACE — add new providers here
// ════════════════════════════════════════

async function getQuotes(symbols, apiKey) {
  switch (activeProvider) {
    case 'twelve-data':
      return twelveDataQuote(symbols, apiKey);
    case 'polygon':
      console.error('Polygon provider not implemented yet. Switch to twelve-data in config.json.');
      return [];
    case 'alpha-vantage':
      console.error('Alpha Vantage provider not implemented yet. Switch to twelve-data in config.json.');
      return [];
    default:
      console.error(`Unknown provider: ${activeProvider}`);
      return [];
  }
}

// ════════════════════════════════════════
// CLI COMMANDS
// ════════════════════════════════════════

const args = process.argv.slice(2);
const command = args[0];

const apiKey = loadApiKey();
if (!apiKey) {
  console.error(`No API key found for ${activeProvider}. Set ${providerConfig.env_key} in ${providerConfig.env_file}`);
  process.exit(1);
}

if (command === 'quote') {
  // node scanner/index.js quote META,AMD,NVDA
  const symbols = args[1]?.split(',') || [];
  if (symbols.length === 0) { console.error('Usage: quote SYMBOL1,SYMBOL2,...'); process.exit(1); }
  const results = await getQuotes(symbols, apiKey);
  console.log(JSON.stringify(results, null, 2));

} else if (command === 'scan') {
  const target = args[1] || 'watchlist';

  if (target === 'watchlist') {
    const assets = loadWatchlist('all');
    const symbols = [...new Set(assets.map(a => a.symbol))];
    console.log(`Scanning ${symbols.length} assets using ${providerConfig.name}...`);
    const results = await getQuotes(symbols, apiKey);
    console.log(JSON.stringify(results, null, 2));

  } else if (target === 'session') {
    const session = args[2] || 'all';
    const assets = loadWatchlist(session);
    const symbols = [...new Set(assets.map(a => a.symbol))];
    console.log(`Scanning ${session} session: ${symbols.length} assets...`);
    const results = await getQuotes(symbols, apiKey);
    console.log(JSON.stringify(results, null, 2));

  } else if (target === 'penny') {
    console.log('Penny stock scan requires Finviz. Use: node scanner/index.js scan session ny');
  }

} else if (command === 'movers') {
  // Find assets that moved more than X%
  const threshold = parseFloat(args[1] || '1');
  const assets = loadWatchlist('all');
  const symbols = [...new Set(assets.map(a => a.symbol))];
  console.log(`Scanning ${symbols.length} assets for moves >${threshold}%...`);
  const results = await getQuotes(symbols, apiKey);
  const movers = results.filter(r => r.change_pct && Math.abs(r.change_pct) >= threshold);
  movers.sort((a, b) => Math.abs(b.change_pct) - Math.abs(a.change_pct));
  console.log(`\n🔥 ${movers.length} assets moved >${threshold}%:\n`);
  movers.forEach(m => {
    const dir = m.change_pct > 0 ? '📈' : '📉';
    console.log(`  ${dir} ${m.symbol.padEnd(20)} ${m.price?.toFixed(2).padStart(10)}  ${m.change_pct > 0 ? '+' : ''}${m.change_pct?.toFixed(2)}%  ${m.name || ''}`);
  });

} else {
  console.log(`
Market Scanner — Provider: ${providerConfig.name}

Commands:
  quote META,AMD,NVDA          Get quotes for specific symbols
  scan watchlist                Scan all watchlist assets
  scan session london           Scan London session assets
  scan session ny               Scan NY session assets
  scan session crypto           Scan crypto session assets
  movers 1                      Find assets that moved >1%
  movers 2                      Find assets that moved >2%

Config: scanner/config.json
Provider: ${activeProvider}
  `);
}
