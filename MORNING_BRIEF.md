# Morning Briefing — Workflow for Claude

When Maria says "morning briefing" or "morning brief", execute this workflow exactly.

---

## Step 1: Read Project Files

Read these files first:
- `watchlist.json` — master list of all assets to scan, organized by session
- `rules.json` — entry strategies, risk rules, session times, position sizing, tier definitions
- `today.json` — check for any existing open trades (never duplicate)
- `journal.json` — check recent trade history and pending trades

---

## Step 2: Research Market News

Search the web for news that could affect the watchlist assets. Searches to perform:

1. "biggest stock movers premarket today"
2. "semiconductor AI chip news today"
3. "nuclear energy uranium news today"
4. "copper commodities AI data center news today"
5. "geopolitical market impact news today"
6. "crypto news today"
7. "forex market news today"
8. "gold silver oil price news today"
9. "earnings reports this week"
10. "Federal Reserve ECB BOJ news today"

Note any asset from the watchlist that:
- Moved >2% overnight
- Has a major catalyst (earnings, news, policy change)
- Has geopolitical exposure that changed

---

## Step 3: Scan Watchlist by Session

Scan ALL assets in `watchlist.json` at the correct session. Never skip an asset. Always check for BOTH Buy AND Sell opportunities — never assume direction.

### London Session (10:00 Oslo)
- Scan: All `london_session` assets (forex pairs + commodities)
- Plus: `all_day` macro indicators (SPY, QQQ, DXY, Oil, Copper, Silver, NatGas)
- Apply: FX-1, FX-2, FX-3 strategies for forex; CMD-1, CMD-2, CMD-3 for commodities
- Check for BOTH Tier 1 (scalping) and Tier 2 (swing) setups

### New York Session (15:30 Oslo)
- Scan: All `ny_session` assets (AI ecosystem layers 1-7 + high-news stocks)
- Apply: IDX-1, IDX-2 for indices; individual stock analysis for AI ecosystem
- Check: Earnings calendar — any watchlist stock reporting this week?
- Check for BOTH Tier 1 (scalping) and Tier 2 (swing) setups

### Crypto Session (20:00 Oslo)
- Scan: All `crypto_session` assets (majors + AI tokens)
- Apply: BTC-1, BTC-2 for Bitcoin; ALT-1 for altcoins
- Check: BTC dominance — rising = avoid altcoins, falling = altcoins outperform
- Crypto Tier 1: BTC, ETH only (1m-15m charts) — automation only
- Crypto Tier 2: BTC, ETH, SOL, FET, RENDER, TAO (4H-Daily charts) — place manually

---

## Step 4: Rank and Select Trades

For each potential trade found, assign a tier and score it:

### Tier Assignment
- **Tier 1 (Scalping)**: 1m to 15m timeframe, tight stops, quick targets — FOR AUTOMATION ONLY
- **Tier 2 (Swing)**: 1H to Daily timeframe, S/R-based stops, R:R min 1:2 — FOR MANUAL PLACEMENT

### Selection Rules (Tier 2 only — these are the ones Maria places)
- Maximum 4 open Tier 2 trades at any time (check today.json for current count)
- Position size: $100 per trade
- Never enter if R:R is below 1:2
- Never trade against the weekly trend
- Never trade 30 min before/after major news releases
- Pick the BEST 1-3 Tier 2 trades for the day — quality over quantity

### Scoring Criteria
1. **Strategy match** — Does it cleanly match a strategy from rules.json?
2. **Risk/reward** — Minimum 1:2, preferred 1:3
3. **Catalyst strength** — Earnings, news, macro event driving the move?
4. **Technical alignment** — Higher timeframe trend agrees with entry timeframe?
5. **Session timing** — Is the best entry window during Maria's available hours?

---

## Step 5: Present Briefing to Maria

Every morning briefing MUST follow this exact 4-section structure:

### Section 1: MARKET OVERVIEW

Quick summary of macro conditions and news affecting the watchlist.

```
## MARKET OVERVIEW
- [2-4 bullet points on macro conditions, key news, DXY direction, risk sentiment]
```

### Section 2: OPEN TRADES STATUS

One line per existing open trade from today.json and the broker.

```
## OPEN TRADES STATUS
| Asset | Direction | Entry | Current | P&L | Stop | Target | Status |
```

### Section 3: TIER 2 TRADES — PLACE MANUALLY

Full trade cards for swing trades Maria will place. This is the main output.

```
## TIER 2 TRADES — PLACE MANUALLY

### RANK #1 — TIER 2 — PLACE MANUALLY — [ASSET NAME] ([SYMBOL])
Direction: LONG / SHORT
Timeframe: [1H / 4H / Daily]
Session: London / NY / Crypto
Strategy: [Which strategy from rules.json]
Why: [1-2 sentence catalyst/reason]

Entry: [price]
Stop Loss: [price] — [where: below support / above resistance / below EMA]
Take Profit: [price]
Risk/Reward: [ratio]
Position Size: $100
Units: [calculated from position size and entry price]

Order Type: LIMIT / MARKET
Window: [session time Oslo]
Skip If: [condition that invalidates the trade]

Alerts to Set:
  ENTRY — [condition] @ [price]
  STOP LOSS — [condition] @ [price]
  TAKE PROFIT — [condition] @ [price]
```

### Section 4: TIER 1 TRADES — AUTOMATION ONLY

Brief overview only. No full trade cards needed. These are for awareness and future automation.

```
## TIER 1 TRADES — AUTOMATION ONLY (do not place manually)

| Asset | Direction | Timeframe | Entry Zone | Stop | Target | Signal |
```

Label every Tier 1 trade: **"TIER 1 — AUTOMATION ONLY — do not place manually"**

---

## Step 6: Update today.json

After Maria confirms the Tier 2 trades, update `today.json` with the exact format. Only include Tier 2 trades in today.json (Tier 1 trades are not placed manually).

```json
{
  "date": "Day DD Month YYYY",
  "briefing": [
    "Summary line 1",
    "Summary line 2"
  ],
  "sessions": {
    "london": "10:00 Oslo",
    "new_york": "15:30 Oslo"
  },
  "trades": [
    {
      "name": "Asset Name (SYMBOL)",
      "tv_symbol": "SYMBOL",
      "tier": "TIER 2",
      "direction": "LONG or SHORT",
      "timeframe": "1H / 4H / Daily",
      "strategy": "Why this trade",
      "score": "High/Medium — reason",
      "entry": 0.00,
      "stop": 0.00,
      "target": 0.00,
      "stop_dist": 0.00,
      "risk_reward": "1:X",
      "order_type": "LIMIT",
      "units": 0.00,
      "window": "Session time Oslo",
      "skip_if": "Condition that kills the trade",
      "alerts": [
        {"label": "ENTRY", "condition": "Crossing Up/Down", "price": 0.00, "msg": "Alert 1/3 — ENTRY @ price"},
        {"label": "STOP LOSS", "condition": "Crossing Up/Down", "price": 0.00, "msg": "Alert 2/3 — STOP LOSS @ price"},
        {"label": "TAKE PROFIT", "condition": "Crossing Up/Down", "price": 0.00, "msg": "Alert 3/3 — TAKE PROFIT @ price"}
      ]
    }
  ]
}
```

---

## Step 7: Update Journal

Add each new Tier 2 trade to `journal.json` with result set to "PENDING". Do NOT add Tier 1 trades to the journal — they are not executed yet.

---

## Step 8: Set Alerts on TradingView

For each confirmed Tier 2 trade, use the MCP tools to:
1. `chart_set_symbol` — switch to the asset
2. `alert_create` — create ENTRY, STOP LOSS, and TAKE PROFIT alerts
3. Confirm all alerts are active with `alert_list`

Do NOT set alerts for Tier 1 trades — they are automation-only.

---

## Key Reminders

- **Never assume direction** — always check both Buy and Sell
- **Never skip an asset** — scan every single one in the watchlist
- **Always read watchlist.json and rules.json first** — before starting any briefing
- **Always check today.json first** — don't duplicate existing trades
- **Maximum 4 open Tier 2 trades** — if already at 4, don't add more
- **$100 position size** — calculate units from this
- **News blackout** — no trades 30 min before/after major releases
- **Weekend rule** — no forex/stock trades Sat-Sun (crypto only)
- **Stop loss is mandatory** — never enter without one
- **Think in R** — 1R = planned risk, present results in R multiples
- **Tier 1 = AUTOMATION ONLY** — never place manually, label clearly
- **Tier 2 = PLACE MANUALLY** — full trade cards, alerts, journal entries
