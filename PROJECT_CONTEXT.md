# Project Context — Why This Exists

This file exists so that Claude (or any future AI assistant) understands the goal and vision behind this project across sessions. **Read this file at the start of every session.**

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

### Part 1 — Connecting Claude to TradingView (COMPLETED)
- One-shot setup prompt clones repo, installs deps, configures MCP
- Natural language chart control ("show me Bitcoin on the weekly")
- Research a trader's strategy, write it into `rules.json`, create Pine Script, apply to chart
- Watchlist scanning, morning brief, paper trading order placement

### Part 2 — Broker Execution (FUTURE — Phase 2)
- Connect to Bitget via API for real trade execution
- Deploy to Railway for 24/7 cloud execution

---

## Project Phases

### Phase 1 — R&D (CURRENT)
- Paper trading on TradingView to test strategies
- Multi-strategy system with 5 independent strategies
- 15-minute timed briefing loop monitors markets
- Auto-trade system active — no score threshold, risk limits only
- Scraping YouTuber transcripts via Apify to extract strategies
- Collecting results in journal.json to prove strategy works over 1-2 months

### Phase 2 — Live Broker Execution (FUTURE)
- Only after Phase 1 journal proves consistent positive R
- Connect to Bitget, deploy to Railway for 24/7

---

## Multi-Strategy Architecture (Added April 14-15)

5 independent strategies, each with own rules and watchlist in `/strategies/`:

| Strategy | Label | Tier | Session (Oslo) | Direction |
|----------|-------|------|----------------|-----------|
| **Gap and Go** | GAP-AND-GO | Tier 1 | NY 15:30-16:00 | LONG only |
| **Swing Trade** | SWING-TRADE | Tier 2 | London + NY | Buy + Sell |
| **Overnight Swing** | OVERNIGHT-SWING | Tier 2 | NY close → London open | Buy + Sell |
| **Crypto Momentum** | CRYPTO-MOMENTUM | Tier 1 (BTC/ETH) + Tier 2 (AI tokens) | 20:00+ | Buy + Sell |
| **Resource Commodity** | RESOURCE-COMMODITY | Tier 2 | London + NY | Buy + Sell |
| **Penny Stock Momentum** | PENNY-STOCK-MOMENTUM | Tier 1 | NY 15:30-17:00 | LONG only |

**Trigger words:**
- `"briefing"` → auto-detect Oslo time → run relevant strategies
- `"full briefing"` → run ALL 6 strategies
- `"run [STRATEGY-LABEL]"` → run only that strategy
- `"penny scan"` / `"gap scan"` / `"crypto scan"` / `"resource scan"` / `"swing scan"` / `"overnight scan"` → shortcuts

**Scanner sources** (tested April 15):
- Finviz screener: WORKS via WebFetch — penny stocks + gap scanner
- Warrior Trading penny stocks: needs Apify (403 on direct)
- Crypto Fear & Greed API: WORKS via WebFetch (value 21, Extreme Fear)
- Yahoo earnings calendar: check daily

See `session-briefing.md` and `scanner-sources.json` for details.

---

## Key Files

| File | Purpose |
|------|---------|
| `PROJECT_CONTEXT.md` | This file — read first every session |
| `session-briefing.md` | Multi-strategy session briefing — triggered by "briefing" |
| `MORNING_BRIEF.md` | Legacy 13-step morning briefing |
| `TIMED_BRIEFING.md` | 15-min market monitor — scans watchlist directly, breakout detection |
| `PAPER_TRADING_ORDERS.md` | How to place orders — MANDATORY TP/SL verification |
| `rules.json` (v6.0) | Master rules — position sizing, ATR stops, market regime, scoring |
| `watchlist.json` | Master watchlist — all assets by session |
| `today.json` | Morning snapshot only — NOT the limiter for scanning |
| `journal.json` | Trade journal — all trades with results |
| `auto-trades.json` | Log for auto-executed trades |
| `strategy-learnings.json` | YouTuber strategy extractions |
| `scripts/maria_universal_strategy.pine` | Pine Script — auto-detects asset type |
| `strategies/` | 6 strategy subfolders with own rules.json and watchlist.json |
| `scanner-sources.json` | External scanner URLs (Finviz, Warrior Trading, Yahoo, Fear&Greed API) |

---

## Current State (Updated April 15, 01:30 Oslo)

### rules.json Version: 6.0

Key features:
- **Proper position sizing**: Units = (Portfolio × Risk%) ÷ Stop Distance. NEVER default to 1 unit.
- **Market regime detection**: Check SPY/QQQ/DXY/BTC vs 20 EMA → BULL/BEAR/NEUTRAL
- **Bull regime**: limits 1-2% below market, market orders for breakouts 8+
- **Bear regime**: limits at support, no market orders
- **ATR-based stops**: minimum 1.5x ATR(14), reduce position size for wider stops
- **Performance-based sizing**: 1% (winning) / 0.75% (neutral) / 0.5% (losing) / 0.25% (heavy losing)
- **Auto-execute**: no score threshold, risk limits only (0.5% max, ATR stop, portfolio <5%)
- **Max auto-trades per day**: 5
- **Swing monitoring**: overnight alerts, tiered limits at support, standing orders
- **Tier conflict resolution**: check higher TF when Tier 1 conflicts with Tier 2
- **Momentum strategy MOM-1**: buy 20-day highs with volume (catches runners like META)
- **Breakout/gap detection**: prev day high break with volume, gaps >2%

### Open Positions (as of April 15 01:30 Oslo)
- USDJPY SHORT — entry 159.85, current ~158.72, TP 158.50 (0.22 away!), SL 160.35
- RENDERUSD LONG — entry 1.880, current ~1.857, TP 2.450, SL 1.700 (RenderCon Apr 16-17)

### Pending Orders (v6.0 proper sizing)
- Gold LONG — 25 units @ 4,810, TP 4,900, SL 4,770 ($25 from market)
- ETH LONG — 10 units @ 2,300, TP 2,500, SL 2,200 ($36 from market)
- AMD LONG — 83 units @ 250, TP 274, SL 238 (market closed)
- META LONG — 66 units @ 655, TP 700, SL 640 (market closed)

### Tomorrow's Priority: ARAI (Arrive AI)
- Penny stock scan found ARAI scoring **8/9** — patent news + earnings Apr 15 before open
- At 14:00 Oslo: check pre-market price and mark pre-market high
- At 15:30 Oslo: if breaks pre-market high → auto-execute penny stock momentum entry

### Account
- Balance: ~$100,005
- Started: $100,008
- Realized P&L: -$3.34 (WTI + EURUSD stopped out April 14)

### Journal Stats
- 17 trades total (4 closed, 2 active, 11 pending/cancelled/expired/replaced)
- Win rate: 50% (2/4 closed)
- Total R: -1.26R
- Performance tier: 0.5% risk

---

## Key Lessons Learned

1. **Position sizing is #1 priority**: Trading 1 unit on $100K portfolio = $1 profit per trade. Fix: proper unit calculation.
2. **Orders MUST have TP and SL**: April 14 — Gold/AMD/ETH placed without TP/SL. Fixed with mandatory verification.
3. **Scan watchlist.json, not today.json**: Missed META +20% because timed briefing only checked today.json.
4. **Market regime changes entry style**: Bull = limits close + market orders for breakouts. Bear = limits at support.
5. **ATR-based stops**: WTI $2.80 stop on $10/day asset = noise kill. Min 1.5x ATR.
6. **Don't exit manually before stop**: SOL was right direction but manual exit lost money.
7. **Tier conflict resolution**: 5-min signal vs daily trade — check higher TF to decide.
8. **Breakout strategy needed**: Pullback-only system misses runners. Added MOM-1 + gap detection.

---

## Apify Setup
- API key in `/Users/mariashchekanenko/claude-trading-broker/.env` as `APIFY_API_KEY`
- Actor: `pintostudio~youtube-transcript-scraper`
- 7 Warrior Trading transcripts scraped, strategies applied to rules.json
- 4 channels remaining: Benjamin Cowen, Rayner Teo, Kitco News, Coin Bureau

## SSH / Git
- SSH key: `~/.ssh/id_ed25519_github`
- Repo: `cgiliber/tradingview-mcp-jackson`
- Branch: `maria-dev`

---

## For Claude: How to Work on This Project

1. **Read this file first** — it's your complete project briefing
2. **Read session-briefing.md** — for strategy execution triggers
3. **Read rules.json** — v6.0 master rules with proper position sizing
4. **Scan watchlist.json directly** — never limit to today.json
5. **Every order MUST have TP and SL** — verify after placement
6. **Calculate proper units** — Units = (Portfolio × Risk%) ÷ Stop Distance
7. **Check market regime** — BULL/BEAR/NEUTRAL before setting limits
8. **Log everything** — journal.json for all trades, auto-trades.json for auto-executed
9. **Paper trading only** — Phase 1 R&D, no real money
