# Project Context — v8.5 (Pine Script Indicators + Pattern R&D)

**Read this file at the start of every session.**

## Vision

Build a trading system where Claude finds market movers, analyzes charts, and executes paper trades using 5 competing strategies. The winning strategy becomes v9.0 "Maria" for live trading.

```
Finviz + CoinGecko (free) → Claude (brain) → TradingView MCP (charts + trades)
Pine Script indicator → BUY_SIGNAL/SELL_SIGNAL → Claude reads → places trade
Pattern scanner (K-Means) → find repeatable setups → build personal strategy
```

## Current State (April 17, 2026)

- **Account:** $99,367 | Realized P&L: -$633
- **Phase:** 1 (Paper Trading R&D)
- **Strategies:** 5 running in parallel + TradingLab v8.5 Supply/Demand
- **Transcripts:** 30 videos scraped (476K+ chars) from 4 channels
- **Mistakes tracked:** 30 (27 fixed, 3 pending)
- **Open positions:** 0
- **New:** Pine Script indicators for signal detection, K-Means pattern scanner

## 5 Competing Strategies

| Strategy | Source | Market | Key Rule | Journal |
|----------|--------|--------|----------|---------|
| v8.0 Baseline | Warrior Trading | All | EMA 8 momentum | journal-v80.json |
| v8.1 Rayner | Rayner Teo (7 vids) | Stocks | Buildup, retest, EMA 21 | journal-v81.json |
| v8.2 Cowen | Benjamin Cowen (7 vids) | Crypto | 21w EMA cycle, BTC dominance | journal-v82.json |
| v8.3 Wysetrade | Wysetrade (7 vids) | Forex | Liquidity sweeps, smart money | journal-v83.json |
| v8.4 Range | YouTube short | All | 15-min range breakout + pullback | journal-v84.json |

## TradingLab v8.5 Supply/Demand (NEW)

Based on TradingLab YouTube: "The Only Strategy You Will Ever Need"

**How it works:**
1. Pivot-based swing tracking (swing highs/lows, length=10)
2. Trend direction from price vs swing levels
3. Supply/Demand zones from impulse candles (body > 2x average)
4. Signal fires when price retests zone with R:R >= 2.5:1
5. "Sticky signals" — BUY_SIGNAL/SELL_SIGNAL persist ~60 min (adaptive to any timeframe)

**Key finding:** Works on **1H timeframe**, NOT 5m. 5m signals are noisy/weak.

**Files:**
- `scripts/v85_indicator.pine` — indicator version (used for live scanning)
- `scripts/v85_strategy.pine` — strategy version (backtest only)

**Important:** Pine Script strategies CANNOT auto-trade on Paper Trading. Must use indicator + manual order placement.

## Pattern R&D Pipeline (NEW — April 17-18)

Mathematical pattern recognition on OHLCV data for strategy discovery.

**Approach evolution:**
1. K-Means clustering on 5-candle OHLCV windows
2. Cross-correlation template matching (V-reversals)
3. Statistical validation (binomial test + Bonferroni correction)
4. Out-of-sample backtest (70/30 train/test split)
5. Multi-asset generalization testing

**Final result — ONE validated strategy emerged:**
- **EURGBP 1H Mean-Reversion v1.0** — see `strategies/forex-meanrev-eurgbp/`
- Bonferroni p < 5.1e-06, OOS WR 57.3%, +1.43% return on 192 trades
- Time-of-day mean reversion using RSI + EMA20 + ATR + hour

**Process learnings:**
- 4,156 patterns tested with raw OHLCV → 0 survived Bonferroni (curve fitting noise)
- Adding indicators (RSI, EMAs, ATR, time) → 2 EURGBP patterns survived
- Cross-pair testing (EURJPY, USDCHF, etc.) → only EURGBP held in OOS
- Stocks/crypto produced no statistically valid edges at this data scale

**Files:**
- `scripts/pattern_scanner.py` — original K-Means + cross-correlation scanner
- `scripts/statistical_validation.py` — v1 Bonferroni testing (zero survivors)
- `scripts/statistical_validation_v2.py` — v2 with indicators (2 survivors)
- `scripts/test_forex_crosses.py` — cross-pair generalization
- `scripts/backtest_forex_meanrev.py` — out-of-sample backtest
- `scripts/download_watchlist.py` — yfinance batch downloader (2y 1H)
- `data/ohlcv/` — raw 1H OHLCV for 82 assets
- `data/statistical-validation-v2.json` — full pattern test results
- `data/backtest-meanrev.json` — backtest output
- `charts/batch-summary.png` — per-asset-class performance map
- `charts/eurgbp-survivors.png` — visual of the 2 surviving patterns

## Chart Visualizer

`scripts/chart_visualizer.py` — generates candlestick + volume charts from CSV. Index-based x-axis (no weekend gaps), dark theme.

**Data:**
- `data/nvda-1h-ohlcv.csv` — 443 bars NVDA 1H (Jan 15 - Apr 17, 2026)
- `charts/nvda-1h-chart.png` — rendered chart

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
11. **1H timeframe** for TradingLab v8.5 strategy (not 5m)

## Key Files

| File | Purpose |
|------|---------|
| `TRADER_WORKFLOW.md` | Primary execution workflow |
| `AB_TEST.md` | 5-strategy comparison framework |
| `MISTAKES_AUDIT.md` | 30 mistakes tracked |
| `scanner/trader-scan.js` | Finviz + CoinGecko scanner |
| `scripts/v85_indicator.pine` | TradingLab Supply/Demand indicator |
| `scripts/v85_strategy.pine` | Backtest strategy version |
| `scripts/pattern_scanner.py` | K-Means pattern clustering |
| `scripts/chart_visualizer.py` | Candlestick chart generator |
| `data/nvda-1h-ohlcv.csv` | NVDA 1H historical data |
| `data/pattern-results.json` | Pattern scanner results |
| `journal-v8*.json` | Per-strategy trade journals |

## Phase 2 Gate

Before live trading: collect 100+ trades → data mine all journals → find best rules per condition → build v9.0 hybrid → paper trade 10 days → THEN go live on Bitget.
