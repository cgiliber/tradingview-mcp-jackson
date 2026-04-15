# Project Context — Why This Exists

This file exists so that Claude (or any future AI assistant) understands the goal and vision behind this project across sessions. **Read this file at the start of every session.**

---

## The Vision

Build a trading system where **Claude Code sits between TradingView and a crypto exchange**, acting as the brain that reads the market, applies strategy rules, and executes trades — all with strict safety controls.

```
Twelve Data Scanner (eyes)  →  Claude Code (brain)  →  TradingView Paper Trading (hands)
```

Phase 1: Paper trading to prove strategies. Phase 2: Live broker (Bitget) after journal proves consistent positive R.

---

## What Was Built (April 13-15, 2026)

### Multi-Strategy Architecture — 6 Strategies in `/strategies/`

| Strategy | Label | Tier | Session (Oslo) | Assets |
|----------|-------|------|----------------|--------|
| Gap and Go | GAP-AND-GO | Tier 1 | NY 15:30-16:00 | US stocks gapping >4% |
| Swing Trade | SWING-TRADE | Tier 2 | London + NY | All watchlist |
| Overnight Swing | OVERNIGHT-SWING | Tier 2 | 22:00 → 10:00 | Gold, Oil, forex, BTC, ETH |
| Crypto Momentum | CRYPTO-MOMENTUM | Tier 1/2 | 20:00+ | 16 crypto assets |
| Resource Commodity | RESOURCE-COMMODITY | Tier 2 | London + NY | Gold, Oil, Copper, Uranium stocks |
| Penny Stock Momentum | PENNY-STOCK-MOMENTUM | Tier 1 | NY 15:30-17:00 | Dynamic daily via Finviz scanner |

**Trigger words:** `"briefing"` (auto-detect time), `"full briefing"` (all), `"run [LABEL]"` (specific), `"penny scan"` / `"gap scan"` / `"crypto scan"` / etc.

### Market Data Scanner (`scanner/`)
- Provider-agnostic — swap by changing `scanner/config.json` → `active_provider`
- Current: Twelve Data (tested — stocks, forex, crypto, gold)
- Credit tracking: 800/day, session-based budget allocation
- Commands: `node scanner/index.js quote SYMBOLS` / `scan session ny` / `movers 1` / `credits`
- `scanner/format.py` — consistent output formatting

### Watchlist — 93 Assets
- London: 11 forex + commodities
- EU stocks: 21 via US ADR (UK, Germany, France, Italy, Norway, Sweden, Switzerland)
- NY stocks: 38 (AI ecosystem layers 1-7 + high-news)
- Crypto: 16 (majors + AI tokens)
- Macro: 7 (SPY, QQQ, DXY, Oil, Copper, Silver, NatGas)

### Automated Daily Schedule (`daily-schedule.json`)
- Overnight (22:00-07:00): 45 credits — priority assets
- Pre-London (07:00-10:00): 32 credits — forex prep
- London (10:00-14:00): 156 credits — forex + commodities
- Pre-NY (14:00-15:30): 38 credits — EU ADR gaps + penny scan
- NY (15:30-20:00): 326 credits — ALL stocks (64 assets)
- Crypto (20:00-22:00): 68 credits — 16 crypto assets
- Total: 665/800 with 135 buffer
- **Always check local time with `date` before scheduling**

### rules.json v6.0 — Key Features
- Position sizing: Units = (Portfolio × Risk%) ÷ Stop Distance. NEVER 1 unit.
- Market regime: BULL (limits 1-2%, market orders for breakouts) / BEAR (limits at support)
- ATR stops: 1.5x ATR(14) minimum
- Auto-execute: no score threshold, risk limits only, no daily trade limit
- Max portfolio allocation: 10% (Maria approved)
- Portfolio stretch: alert Maria at 4%+ with good opportunity
- Breakout detection: prev day high break + volume
- Tier conflict: check higher TF to decide

---

## Current State (Updated April 15, 07:00 Oslo)

### Open Positions
- USDJPY SHORT — entry 159.85, TP 158.50 (0.48 away), SL 160.35
- RENDERUSD LONG — entry 1.88, TP 2.45, SL 1.70 (**RenderCon TODAY Apr 16-17**)

### Pending Orders (v6.0 proper sizing)
- Gold LONG — 25 units @ 4,810, TP 4,900, SL 4,770 ($14 from market)
- ETH LONG — 10 units @ 2,300, TP 2,500, SL 2,200 ($29 from market)
- AMD LONG — 83 units @ 250, TP 274, SL 238 (market closed)
- META LONG — 66 units @ 655, TP 700, SL 640 (market closed)

### Account
- Balance: ~$100,005
- Performance tier: 0.5% risk (last 3 trades net negative)

### Tomorrow's Priority
- ARAI (Arrive AI) — penny stock, 8/9 score, earnings today before open
- TSM — earnings April 16 (tomorrow)
- RenderCon — April 16-17 (today/tomorrow)

---

## Key Files

| File | Purpose |
|------|---------|
| `PROJECT_CONTEXT.md` | This file — read first every session |
| `daily-schedule.json` | Automated daily trading schedule |
| `session-briefing.md` | Multi-strategy session briefing |
| `TIMED_BRIEFING.md` | 15-min market monitor |
| `PAPER_TRADING_ORDERS.md` | Order placement — MANDATORY TP/SL verification |
| `rules.json` (v6.0) | Master rules |
| `watchlist.json` | 93 assets by session |
| `journal.json` | Trade journal — 17 trades |
| `auto-trades.json` | Auto-trade log |
| `scanner/config.json` | Scanner provider config + credit budget |
| `scanner/index.js` | Market scanner script |
| `scanner-sources.json` | External URLs (Finviz, Fear&Greed, Yahoo) |
| `strategies/` | 6 strategy subfolders |

---

## Critical Rules — Never Forget

1. **Every order MUST have TP and SL** — verify after placement
2. **Scan watchlist.json directly** — never limit to today.json
3. **Proper position sizing** — Units = (Portfolio × Risk%) ÷ Stop Distance
4. **Check local time** — run `date` before every scheduled action
5. **No asking permission** — execute per rules, notify after
6. **Market regime** — check BULL/BEAR before setting limits
7. **EU ADRs trade at 15:30+ Oslo** — not during London
8. **Credit budget** — 800/day, save most for NY peak
9. **Auto-trade** — no score threshold, risk limits only, 10% max allocation
10. **Log everything** — journal.json + auto-trades.json

---

## API Keys Location
- Twelve Data: `/Users/mariashchekanenko/claude-trading-broker/.env` → `TWELVE_DATA_API_KEY`
- Apify: same file → `APIFY_API_KEY`
- SSH: `~/.ssh/id_ed25519_github` → repo `cgiliber/tradingview-mcp-jackson` branch `maria-dev`
