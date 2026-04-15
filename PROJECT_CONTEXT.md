# Project Context — v8.0 Free Scanner Revolution

**Read this file at the start of every session.**

---

## The Vision

Build a trading system where Claude Code finds market movers, analyzes charts, and executes paper trades — all with strict risk controls and 100% free data sources.

```
Finviz + CoinGecko (free scanners)  →  Claude Code (brain)  →  TradingView MCP (charts + trades)
```

Phase 1: Paper trading to prove strategies. Phase 2: Live broker (Bitget) after journal proves consistent profit.

---

## Architecture — Everything is Free

| Need | Tool | Cost |
|------|------|------|
| Find stock movers | Finviz screener | Free |
| Find crypto movers | CoinGecko API | Free |
| Real-time charts | TradingView MCP | Free |
| Real-time quotes | TradingView quote_get | Free |
| Place trades | TradingView paper trading | Free |
| Backup quotes | Twelve Data API | Free tier (800/day, rarely needed) |

---

## Two Modes of Operation

### 1. Morning Briefing (long-term positions)
- **Trigger:** Maria says "morning briefing"
- **Source:** `watchlist.json` — 93 curated assets (London/NY/Crypto/EU)
- **Workflow:** `MORNING_BRIEF.md` — 13 steps, news research, scoring
- **Output:** `today.json` (read-only after morning)

### 2. Cash Flow Hunting (daily income)
- **Trigger:** Automatic cron every 5-15 min
- **Source:** Finviz (stocks) + CoinGecko (crypto) — DYNAMIC, changes daily
- **Workflow:** `TRADER_WORKFLOW.md` — scan movers → open charts → trade or skip
- **Goal:** $50-100/day from many small $20 wins

---

## Daily Schedule

| Window (Oslo) | Interval | What |
|---------------|----------|------|
| 15:30-17:00 | **Every 5 min** | NY open power hour — biggest moves happen here |
| 17:00-22:00 | Every 15 min | Regular session — monitor + late runners |
| 22:00 | **CLOSE ALL** | No overnight holds |
| 20:00-00:00 | Every 15 min | Crypto session (CoinGecko scanner) |

---

## Trading Rules — v7.0 v2

| Rule | Value |
|------|-------|
| Max loss per trade | **$10** |
| Target per trade | **$20** (1:2 R:R) |
| Breakeven lock | At **+$10 profit** → move SL to entry |
| Close rule | At **+$20** → close position |
| Daily loss limit | **-$50** → stop trading |
| Monthly goal | **$3,000** ($150/day, 20 trading days) |
| Position sizing | Units = FLOOR($10 / stop_distance) |
| Close all by | 22:00 Oslo (stocks) / 00:00 (crypto) |
| Default | **TRADE** (need reason NOT to trade) |
| Minimum trades/day | 5-8 |

### NOT valid skip reasons:
- "Above BB upper" — momentum stocks live there
- "Extended from EMA" — gap stocks ARE extended
- "Late in the day" — if 1+ hour left, trade it
- "Already have positions" — 5 × $10 = $50 total risk, fine
- "Too volatile" — that's the opportunity

---

## Scanner — `trader-scan.js`

```bash
node scanner/trader-scan.js              # Stock gainers + losers (Finviz)
node scanner/trader-scan.js --crypto     # Crypto movers (CoinGecko)
node scanner/trader-scan.js --all        # Both
node scanner/trader-scan.js --top 20     # Top 20 per list
```

Output: ranked lists of biggest movers. Start from #1, work down. Open each chart on TradingView. Analyze. Trade or skip with technical reason.

---

## Key Files

### Workflows
| File | Purpose |
|------|---------|
| `TRADER_WORKFLOW.md` | **PRIMARY** — scan → chart → trade. The daily cash flow playbook. |
| `MORNING_BRIEF.md` | Morning briefing with curated watchlist |
| `PAPER_TRADING_ORDERS.md` | How to place orders on TradingView via DOM |

### Scanner
| File | Purpose |
|------|---------|
| `scanner/trader-scan.js` | **PRIMARY** — Finviz + CoinGecko, free |
| `scanner/index.js` | Backup — Twelve Data quotes |
| `scanner/status.js` | Live countdown display |

### Rules & Strategies
| File | Purpose |
|------|---------|
| `strategies/goal-based-rules.json` | **CORE** — $10 loss, $20 target |
| `strategies/profit-lock-rules.json` | Breakeven + profit locking |
| `rules.json` | Master rules v7.0 |
| `strategies/*/` | 6 strategy folders with rules + watchlists |

### Data
| File | Purpose |
|------|---------|
| `watchlist.json` | 93 curated assets — morning briefing |
| `journal.json` | Trade journal — 20 trades |
| `today.json` | Morning briefing output (read-only) |

---

## 6 Strategies

| Strategy | Session (Oslo) | Assets |
|----------|----------------|--------|
| GAP-AND-GO | NY 15:30-16:00 | Finviz gappers >4% |
| PENNY-STOCK-MOMENTUM | NY 15:30-17:00 | Finviz $1-$20 stocks |
| SWING-TRADE | London + NY | S/R levels, both directions |
| RESOURCE-COMMODITY | London + NY | Gold, Oil, Uranium, Rare earth |
| OVERNIGHT-SWING | 22:00 → 10:00 | Forex, Gold, BTC |
| CRYPTO-MOMENTUM | 20:00+ | CoinGecko top movers |

---

## Critical Rules — Never Forget

1. **$10 max loss.** Units = FLOOR($10 / stop). No exceptions.
2. **Every order MUST have TP and SL.** Verify after placement.
3. **At +$10 → breakeven SL.** Immediately. Zero exceptions.
4. **At +$20 → CLOSE.** Take the cash. Find next trade.
5. **Close ALL by 22:00 Oslo.** No overnight holds.
6. **Always check chart.** Open TradingView for every mover.
7. **Default is TRADE.** Stop being scared. $10 is 0.01% of portfolio.
8. **Both directions.** Scan gainers (LONG) AND losers (SHORT).
9. **Start from #1.** Work down the Finviz/CoinGecko list.
10. **Log everything.** journal.json after every trade.

---

## Account
- Started: $100,000
- Current: ~$100,002
- Branch: `maria-dev`
- Tag: `v8.0`
- Repo: `cgiliber/tradingview-mcp-jackson`
- SSH: `~/.ssh/id_ed25519_github`
