# Project Context — v8.4 (5-Strategy Parallel Testing)

**Read this file at the start of every session.**

## Vision

Build a trading system where Claude finds market movers, analyzes charts, and executes paper trades using 5 competing strategies. The winning strategy becomes v9.0 "Maria" for live trading.

```
Finviz + CoinGecko (free) → Claude (brain) → TradingView MCP (charts + trades)
```

## Current State (April 16, 2026 end of day)

- **Account:** $99,428.46 | Realized P&L: -$571.54
- **Phase:** 1 (Paper Trading R&D)
- **Strategies:** 5 running in parallel
- **Transcripts:** 30 videos scraped (476K+ chars) from 4 channels
- **Mistakes tracked:** 30 (27 fixed, 3 pending)
- **Open positions:** RENDER 51u only (overnight)

## 5 Competing Strategies

| Strategy | Source | Market | Key Rule | Journal |
|----------|--------|--------|----------|---------|
| v8.0 Baseline | Warrior Trading | All | EMA 8 momentum | journal-v80.json |
| v8.1 Rayner | Rayner Teo (7 vids) | Stocks | Buildup, retest, EMA 21 | journal-v81.json |
| v8.2 Cowen | Benjamin Cowen (7 vids) | Crypto | 21w EMA cycle, BTC dominance | journal-v82.json |
| v8.3 Wysetrade | Wysetrade (7 vids) | Forex | Liquidity sweeps, smart money | journal-v83.json |
| v8.4 Range | YouTube short | All | 15-min range breakout + pullback | journal-v84.json |

## Rules (compact — in memory, not files)

See `memory/rules_compact.md` — loaded once at session start, never re-read during scans.

## Daily Schedule

| Time | What |
|------|------|
| 10:00-14:59 | Pre-market scan (Finviz), identify targets |
| 15:30:00 | GAP SCALP sniper — market orders on all targets (v8.0-v8.3) |
| 15:33 | Gap scalp check — sell winners |
| 15:35 | Gap scalp close ALL |
| 15:45 | v8.4 Range — mark HIGH/LOW of first 15-min candle |
| 15:50-16:15 | v8.4 Range — check breakouts every 5 min |
| 15:31-15:40 | Opening burst — 1 min scans for new movers |
| 15:40-17:00 | Power hour — 5 min scans, all 5 strategies |
| 17:00-20:00 | Regular — 15 min scans |
| 20:00-21:55 | Closing hour — 5 min scans, close all stocks by 21:55 |
| 20:00-00:00 | Crypto — 15 min CoinGecko scans |
| 00:00-07:00 | Overnight crypto — 30 min scans |

## Critical Rules

1. **FLASH MODE** — zero text between trades, tool calls only, summary after
2. **RULE ZERO** — timing is everything, place order FIRST, write after
3. **Both directions** — alternate long/short, shorts are 50% of opportunities
4. **Top 30 movers** — not 10, go wider
5. **$10 risk** per trade, breakeven at +$10, close at +$20
6. **All 5 strategies** evaluate every mover independently
7. **Close positions** via aria-label="Close" button → "Close position" confirm
8. **Paper mode** — no budget limits, trade freely for data
9. **Verify** every action — screenshot + check positions
10. **Phase 2 gate** — data mining REQUIRED before live trading

## Key Files

| File | Purpose |
|------|---------|
| `TRADER_WORKFLOW.md` | Primary execution workflow |
| `strategies/rules-compact.json` | All rules in compact format |
| `AB_TEST.md` | 5-strategy comparison framework |
| `MISTAKES_AUDIT.md` | 30 mistakes tracked |
| `SPEED_BOTTLENECK.md` | Performance analysis |
| `scanner/trader-scan.js` | Finviz + CoinGecko scanner |
| `journal-v8*.json` | Per-strategy trade journals |

## Phase 2 Gate

Before live trading: collect 100+ trades → data mine all journals → find best rules per condition → build v9.0 hybrid → paper trade 10 days → THEN go live on Bitget.
