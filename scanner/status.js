#!/usr/bin/env node
/**
 * Live countdown display — shows session and next-scan progress bars
 * Updates every second in-place. Run: node scanner/status.js
 * Press Ctrl+C to stop.
 */

import { readFileSync } from 'fs';
import { dirname, join } from 'path';
import { fileURLToPath } from 'url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const ROOT = join(__dirname, '..');

function getOsloTime() {
  const now = new Date();
  const oslo = new Intl.DateTimeFormat('en-GB', {
    timeZone: 'Europe/Oslo',
    hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false
  }).format(now);
  const [h, m, s] = oslo.split(':').map(Number);
  return { hour: h, minute: m, second: s, totalMinutes: h * 60 + m, totalSeconds: h * 3600 + m * 60 + s, formatted: oslo };
}

function getSession(totalMinutes) {
  const sessions = [
    { name: 'PRE-LONDON',       start: 7*60,     end: 10*60,    strategy: 'OVERNIGHT RESULTS + LONDON PREP' },
    { name: 'LONDON + US PRE',  start: 10*60,    end: 13*60,    strategy: 'SWING-TRADE + US PRE-MARKET' },
    { name: 'ROSS CAMERON',     start: 13*60,    end: 15*60+30, strategy: 'GAP-AND-GO + PENNY-STOCK' },
    { name: 'NY SESSION',       start: 15*60+30, end: 20*60,    strategy: 'ALL NY STRATEGIES (rotating)' },
    { name: 'CRYPTO',           start: 20*60,    end: 22*60,    strategy: 'CRYPTO-MOMENTUM' },
  ];
  for (const s of sessions) {
    if (totalMinutes >= s.start && totalMinutes < s.end) return s;
  }
  return { name: 'OVERNIGHT', start: 22*60, end: 7*60, strategy: 'OVERNIGHT-SWING' };
}

function getNextStrategy(nextMinute, sessionName) {
  if (sessionName === 'NY SESSION') {
    const ri = Math.floor(nextMinute / 15) % 3;
    return ['SWING-TRADE (NY)', 'SWING-TRADE (EU ADR)', 'RESOURCE-COMMODITY'][ri];
  }
  if (sessionName === 'CRYPTO') {
    const ri = Math.floor(nextMinute / 15) % 2;
    return ['Tier 1 (BTC/ETH/SOL)', 'Tier 2 (AI tokens)'][ri];
  }
  return null;
}

function loadCredits() {
  try {
    const log = JSON.parse(readFileSync(join(__dirname, 'credit-log.json'), 'utf8'));
    return { used: log.used, limit: 800 };
  } catch { return { used: 0, limit: 800 }; }
}

function makeBar(pct, width = 40) {
  const filled = Math.round((pct / 100) * width);
  return '\u2588'.repeat(filled) + '\u2591'.repeat(width - filled);
}

function formatTime(mins) {
  const h = Math.floor(mins / 60) % 24;
  const m = mins % 60;
  return `${String(h).padStart(2,'0')}:${String(m).padStart(2,'0')}`;
}

function render() {
  const oslo = getOsloTime();
  const session = getSession(oslo.totalMinutes);

  // Session progress
  const sessionEnd = session.end < session.start ? session.end + 24*60 : session.end;
  const sessionLength = sessionEnd - session.start;
  const sessionElapsed = oslo.totalMinutes >= session.start
    ? oslo.totalMinutes - session.start
    : oslo.totalMinutes + (24*60 - session.start);
  const sessionPct = Math.min(100, Math.round((sessionElapsed / sessionLength) * 100));
  const sessionRemainMin = sessionLength - sessionElapsed;

  // Next scan countdown (15 min intervals)
  const nextScanMinute = Math.ceil((oslo.totalMinutes + 1) / 15) * 15;
  const secsUntilNext = (nextScanMinute * 60) - oslo.totalSeconds;
  const scanPct = Math.min(100, Math.round(((15*60 - secsUntilNext) / (15*60)) * 100));
  const nextMM = Math.floor(secsUntilNext / 60);
  const nextSS = secsUntilNext % 60;
  const nextStrategy = getNextStrategy(nextScanMinute, session.name);

  const credits = loadCredits();

  // Clear and draw
  process.stdout.write('\x1B[2J\x1B[H'); // clear screen

  const w = 56;
  const line = '═'.repeat(w);
  console.log(line);
  console.log(`  SCANNER STATUS — ${oslo.formatted} Oslo`);
  console.log(`  ${session.name} | ${session.strategy}`);
  console.log(`  Credits: ${credits.used}/${credits.limit}`);
  console.log(line);
  console.log();

  // Session bar
  console.log(`  SESSION  ${formatTime(session.start)}                              ${formatTime(session.end % (24*60))}`);
  console.log(`  [${makeBar(sessionPct, 48)}]`);
  console.log(`   ${sessionPct}% done — ${sessionRemainMin} min remaining`);
  console.log();

  // Next scan bar
  console.log(`  NEXT SCAN in ${String(nextMM).padStart(2,'0')}:${String(nextSS).padStart(2,'0')}`);
  console.log(`  [${makeBar(scanPct, 48)}]`);
  if (nextStrategy) {
    console.log(`   -> ${nextStrategy}`);
  }
  console.log();

  console.log(line);
  console.log(`  You can message Claude anytime — scans fire when idle`);
  console.log(`  Press Ctrl+C to close this display`);
  console.log(line);
}

// Initial render + update every second
render();
const interval = setInterval(render, 1000);

process.on('SIGINT', () => {
  clearInterval(interval);
  process.stdout.write('\x1B[2J\x1B[H');
  console.log('Status display closed.');
  process.exit(0);
});
