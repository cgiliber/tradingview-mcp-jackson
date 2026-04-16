#!/usr/bin/env node
/**
 * TRADER SCAN v3 — What a real trader does. 100% FREE.
 *
 * Stocks:  Finviz (free) → top gainers + losers sorted by % change
 * Crypto:  CoinGecko (free) → top movers by 24h change
 * Charts:  TradingView MCP (free) → Claude analyzes each chart
 *
 * Usage:
 *   node scanner/trader-scan.js              # Stocks (gainers + losers)
 *   node scanner/trader-scan.js --crypto     # Crypto movers from CoinGecko
 *   node scanner/trader-scan.js --all        # Both stocks + crypto
 *   node scanner/trader-scan.js --top 20     # Top 20 per list
 *
 * ZERO API credits. Everything is free.
 */

import { readFileSync, writeFileSync, existsSync } from 'fs';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';

const __dirname = dirname(fileURLToPath(import.meta.url));
const ROOT = join(__dirname, '..');

const args = process.argv.slice(2);
const topN = args.includes('--top') ? parseInt(args[args.indexOf('--top') + 1]) || 10 : 10;
const scanCrypto = args.includes('--crypto') || args.includes('--all');
const scanStocks = !args.includes('--crypto') || args.includes('--all');

// ── Oslo time ──
function getOsloTime() {
  const now = new Date();
  const oslo = new Intl.DateTimeFormat('en-GB', { timeZone: 'Europe/Oslo', hour: '2-digit', minute: '2-digit', hour12: false }).format(now);
  const [h, m] = oslo.split(':').map(Number);
  return { hour: h, minute: m, totalMinutes: h * 60 + m, formatted: oslo.padStart(5, '0') };
}

// ── Finviz Screener (FREE — zero credits) ──
async function fetchFinvizMovers(direction = 'gainers') {
  // gainers: sorted by biggest positive change first
  // losers: sorted by biggest negative change first (short candidates)
  const url = direction === 'losers'
    ? 'https://finviz.com/screener.ashx?v=111&o=change&ft=4'
    : 'https://finviz.com/screener.ashx?v=111&o=-change&ft=4';
  const res = await fetch(url, {
    headers: { 'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36' }
  });
  const html = await res.text();

  // Parse the screener table
  // Each row has: No, Ticker, Company, Sector, Industry, Country, Market Cap, P/E, Price, Change, Volume
  const movers = [];

  // Match table rows with class "styled-row"
  const rowPattern = /<tr[^>]*class="styled-row[^"]*"[^>]*>([\s\S]*?)<\/tr>/g;
  let match;
  while ((match = rowPattern.exec(html)) !== null) {
    const row = match[1];
    // Extract cells
    const cellPattern = /<td[^>]*>([\s\S]*?)<\/td>/g;
    const cells = [];
    let cell;
    while ((cell = cellPattern.exec(row)) !== null) {
      // Strip HTML tags
      const text = cell[1].replace(/<[^>]+>/g, '').trim();
      cells.push(text);
    }
    // cells: [No, Ticker, Company, Sector, Industry, Country, MarketCap, P/E, Price, Change, Volume]
    if (cells.length >= 11) {
      const ticker = cells[1];
      const company = cells[2];
      const sector = cells[3];
      const price = parseFloat(cells[8]);
      const changePct = parseFloat(cells[9]);
      const volume = cells[10];

      if (ticker && !isNaN(price) && !isNaN(changePct)) {
        movers.push({ symbol: ticker, name: company, sector, price, change_pct: changePct, volume });
      }
    }
  }

  return movers;
}

// ── CoinGecko Screener (FREE — zero credits) ──
async function fetchCryptoMovers() {
  // CoinGecko API v3 — free, no key needed, returns top coins by market cap with 24h change
  const url = 'https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&order=volume_desc&per_page=250&page=1&sparkline=false&price_change_percentage=24h';
  const res = await fetch(url, {
    headers: { 'User-Agent': 'Mozilla/5.0' }
  });
  const data = await res.json();
  if (!Array.isArray(data)) return [];

  // Filter: min $1 price, min $10M market cap — no micro tokens
  const filtered = data.filter(c =>
    c.price_change_percentage_24h != null &&
    c.current_price >= 1.0 &&
    c.market_cap >= 10_000_000
  );

  // Sort by absolute 24h change
  filtered.sort((a, b) => Math.abs(b.price_change_percentage_24h) - Math.abs(a.price_change_percentage_24h));

  return filtered.map(c => ({
    symbol: (c.symbol || '').toUpperCase(),
    name: c.name,
    price: c.current_price,
    change_pct: c.price_change_percentage_24h,
    volume: c.total_volume?.toLocaleString() || '?',
    sector: 'Crypto',
    market_cap: c.market_cap,
    mcap_label: c.market_cap >= 1e9 ? (c.market_cap / 1e9).toFixed(1) + 'B' : (c.market_cap / 1e6).toFixed(0) + 'M',
    direction: c.price_change_percentage_24h >= 0 ? 'LONG' : 'SHORT'
  }));
}

// ── Filters ──
function filterMovers(movers) {
  return movers.filter(m => {
    // Skip leveraged ETFs (2x, 3x, Bull, Bear in name or common leveraged tickers)
    if (m.name && /\b(2[xX]|3[xX]|Bull|Bear|Leveraged|Daily.*ETF|Long.*ETF|Short.*ETF)\b/.test(m.name)) return false;
    if (m.sector === 'Financial' && m.name && /ETF/i.test(m.name)) return false;

    // Skip sub-$0.50 stocks (too risky)
    if (m.price < 0.50) return false;

    // Skip warrants and rights
    if (m.symbol && /[WR]$/.test(m.symbol) && m.symbol.length > 4) return false;

    return true;
  });
}

// ── Main ──
const oslo = getOsloTime();
const bar = '='.repeat(60);

console.log(bar);
console.log(`TRADER SCAN v3 — ${oslo.formatted} Oslo`);
console.log(`Source: ${scanStocks ? 'Finviz' : ''}${scanStocks && scanCrypto ? ' + ' : ''}${scanCrypto ? 'CoinGecko' : ''} (FREE)`);
console.log(bar);

try {
  // Fetch all sources in parallel
  const promises = [];
  if (scanStocks) {
    promises.push(fetchFinvizMovers('gainers'));
    promises.push(fetchFinvizMovers('losers'));
  }
  if (scanCrypto) {
    promises.push(fetchCryptoMovers());
  }
  const results = await Promise.all(promises);

  let topGainers = [], topLosers = [], topCrypto = [];
  let idx = 0;
  if (scanStocks) {
    topGainers = filterMovers(results[idx++]).slice(0, topN);
    topLosers = filterMovers(results[idx++]).slice(0, topN);
  }
  if (scanCrypto) {
    const cryptoAll = results[idx++];
    topCrypto = cryptoAll.slice(0, topN); // already filtered by $1 min + $10M mcap in fetchCryptoMovers
  }

  const printTable = (list, label) => {
    const isCrypto = label.includes('CRYPTO');
    console.log(`\n${label} (${list.length} after filters)`);
    if (isCrypto) {
      console.log(`  #   ${'Symbol'.padEnd(8)} ${'Price'.padStart(10)} ${'Change'.padStart(9)}  ${'MCap'.padStart(6)}  ${'Volume'.padStart(14)}  Company`);
    } else {
      console.log(`  #   ${'Symbol'.padEnd(8)} ${'Price'.padStart(8)} ${'Change'.padStart(9)}  ${'Volume'.padStart(12)}  ${'Sector'.padEnd(20)} Company`);
    }
    console.log(`  ${'─'.repeat(90)}`);
    list.forEach((m, i) => {
      const dir = m.change_pct >= 0 ? '+' : '';
      const action = Math.abs(m.change_pct) >= 20 ? ' *** HIGH PRIORITY' :
                     Math.abs(m.change_pct) >= 5 ? ' ** ANALYZE' : '';
      if (isCrypto) {
        console.log(`  ${String(i + 1).padStart(2)}  ${m.symbol.padEnd(8)} ${('$' + m.price.toFixed(2)).padStart(10)} ${(dir + m.change_pct.toFixed(2) + '%').padStart(9)}  ${(m.mcap_label || '?').padStart(6)}  ${(m.volume || '?').padStart(14)}  ${(m.name || '').substring(0, 25)}${action}`);
      } else {
        console.log(`  ${String(i + 1).padStart(2)}  ${m.symbol.padEnd(8)} ${('$' + m.price.toFixed(2)).padStart(8)} ${(dir + m.change_pct.toFixed(2) + '%').padStart(9)}  ${(m.volume || '?').padStart(12)}  ${(m.sector || '').padEnd(20).substring(0, 20)} ${(m.name || '').substring(0, 30)}${action}`);
      }
    });
  };

  if (scanStocks) {
    printTable(topGainers, 'STOCKS — LONG candidates (Finviz)');
    printTable(topLosers, 'STOCKS — SHORT candidates (Finviz)');
  }
  if (scanCrypto) {
    printTable(topCrypto, 'CRYPTO — biggest movers (CoinGecko)');
  }

  console.log(`\n${bar}`);
  console.log(`Cost: $0 | All sources FREE`);
  console.log(`Next: Open TradingView charts — start from #1, work down`);
  console.log(bar);

  // Machine-readable data for Claude
  const scanData = { time: oslo.formatted, credits_used: 0 };
  if (scanStocks) {
    scanData.source = 'finviz';
    scanData.top_gainers = topGainers.map(m => ({ symbol: m.symbol, price: m.price, change_pct: m.change_pct, volume: m.volume, sector: m.sector, name: m.name, direction: 'LONG' }));
    scanData.top_losers = topLosers.map(m => ({ symbol: m.symbol, price: m.price, change_pct: m.change_pct, volume: m.volume, sector: m.sector, name: m.name, direction: 'SHORT' }));
  }
  if (scanCrypto) {
    scanData.crypto_source = 'coingecko';
    scanData.top_crypto = topCrypto.map(m => ({ symbol: m.symbol, price: m.price, change_pct: m.change_pct, volume: m.volume, name: m.name, direction: m.direction }));
  }
  console.log('\n__TRADER_SCAN_DATA__');
  console.log(JSON.stringify(scanData));

} catch (e) {
  console.error('Finviz fetch failed:', e.message);
  console.log('Fallback: use node scanner/index.js auto');
  process.exit(1);
}
