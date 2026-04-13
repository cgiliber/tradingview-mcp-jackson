# Project Context — Why This Exists

This file exists so that Claude (or any future AI assistant) understands the goal and vision behind this project across sessions.

---

## The Vision

Build a trading system where **Claude Code sits between TradingView and a crypto exchange (Bitget)**, acting as the brain that reads the market, applies strategy rules, and executes trades — all with strict safety controls.

```
TradingView Desktop  →  Claude Code (the brain)  →  Bitget Exchange (the hands)
```

TradingView and the exchange never talk directly. Claude is the middleman. This is NOT screenshot-based chart reading — Claude reads live data from TradingView via Chrome DevTools Protocol (CDP on port 9222), seeing exact prices, indicator values, and candle data in real-time.

---

## Origin

This project follows **Lewis Jackson's YouTube video series** on connecting Claude Code to TradingView via MCP.

### Part 1 — Connecting Claude to TradingView
- One-shot setup prompt clones repo, installs deps, configures MCP
- Natural language chart control ("show me Bitcoin on the weekly")
- Research a trader's strategy (Van de Poppe, Tone Vays), write it into `rules.json`, create a Pine Script, apply it to the chart
- Watchlist scanning across multiple assets (BTC, ETH, SOL, XRP, LINK, PEPE)
- Morning brief: one command scans entire watchlist and generates session bias

### Part 2 — Broker Execution (Actual Trades)
- Connect to Bitget via API (key + secret + passphrase)
- Safety check: **every condition in the strategy must pass** before a trade fires
- If any condition fails → no trade, log exactly why
- Deploy to Railway for 24/7 cloud execution with cron schedule
- Every trade logged for tax accounting
- Paper trading by default — switch to live when confident

### Bigger Vision
Scrape transcripts from trading YouTubers (CoinsKid, Blockchain Backer, etc.) via Apify, extract their strategy, turn it into a Pine Script, and get daily bias signals based on someone else's proven methodology.

---

## Architecture

```
Claude Code  ←→  MCP Server (stdio)  ←→  CDP (localhost:9222)  ←→  TradingView Desktop (Electron)
Claude Code  ←→  Bitget REST API (HMAC-signed requests)  ←→  Bitget Exchange
```

- **78+ MCP tools** for chart reading, Pine Script dev, replay, alerts, drawings, multi-pane layouts
- **rules.json** — structured strategy rules that the morning brief and safety checks use
- **safety-check-log.json** — every trade decision logged with indicator values and pass/fail conditions
- **scalper-run.js** — execution script that reads market data, computes signals, places orders on Bitget

---

## Safety Rules (Non-Negotiable)

These were emphasized in the videos and must always be followed:

1. **All conditions must PASS** — if any condition fails, the trade is BLOCKED
2. **Max trade size cap** — never exceed the configured maximum
3. **Max trades per day** — hard cap on trade count
4. **1% portfolio risk per trade** — never risk more
5. **Full decision logging** — every decision recorded with reasons
6. **Paper trading by default** — live trading is opt-in, never the default
7. **Never skip safety checks** — no matter how confident the signal looks

---

## What's Been Built

| Component | Purpose |
|-----------|---------|
| `rules.json` | Strategy definition — watchlist, bias criteria, entry/exit rules, risk rules |
| `scalper-run.js` | XRP/USDT spot scalper using VWAP + RSI(3) + EMA(8) on Bitget |
| `safety-check-log.json` | Trade decision audit trail |
| Morning brief | Scan watchlist, read indicators, apply rules, output session bias |
| `CLAUDE.md` | Decision tree for which MCP tool to use when |
| `SETUP_GUIDE.md` | Step-by-step setup for new users |
| Launch scripts | Start TradingView with CDP enabled (Mac/Win/Linux) |

---

## Key Lessons Learned

- **Bitget asset locking**: Newly purchased assets get locked against immediate resale (anti-wash-trading). The sell retry logic with lock-aware error parsing handles this.
- **Context management matters**: Chart data can easily blow up context windows. Always use `summary: true` on OHLCV, `study_filter` on pine tools.
- **Pine Script is the strongest AI use case**: The compile → error → fix loop is where Claude provides the most value.

---

## For Claude: How to Work on This Project

1. **Always check `rules.json` first** — it defines the active strategy
2. **Never bypass safety checks** — every trade must pass all conditions
3. **Log everything** — decisions, reasons, indicator values
4. **Paper trading first** — never default to live
5. **Keep context small** — use summary modes, filter by study name
6. **Read this file at the start of each session** — it's your project briefing
