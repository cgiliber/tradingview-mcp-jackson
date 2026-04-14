# Morning Briefing — Workflow for Claude

When Maria says "morning briefing" or "morning brief", execute this workflow exactly.

---

## Step 1: Read Files & Calculate Risk

Before doing anything else:
1. Read `watchlist.json` — full asset list by session
2. Read `rules.json` — trading rules, scoring system, tier definitions, ATR stops
3. Read `today.json` — existing open trades and their status
4. Read `journal.json` — recent trade history, check last 3-5 trades for performance-based sizing
5. Note the current portfolio value from TradingView paper trading account
6. Calculate total % currently at risk across all open trades

---

## Step 2: Macro Overview

Search the web for news affecting the watchlist. Searches to perform:

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

Then present ONE PARAGRAPH covering:
- Key geopolitical events affecting markets today
- Major economic data releases today (PPI, CPI, NFP, Fed decisions, earnings)
- Overall market sentiment (Fear & Greed index direction)
- Dollar direction (DXY) — affects all USD pairs and Gold
- Any asset from the watchlist that moved >2% overnight or has a major catalyst

---

## Step 3: Open Trades Status

For each open trade in today.json show:

```
## OPEN TRADES STATUS

| Asset | Direction | Entry | Current | P&L | Dist to SL | Dist to TP | Score | Recommendation |
```

- **Dist to SL**: how far price is from stop loss (in $ and %)
- **Dist to TP**: how far price is from take profit (in $ and %)
- **Score**: trade score out of 14 (from rules.json scoring system)
- **Recommendation**: one word — Hold / Watch / Consider closing
- Add one line of context per trade explaining the recommendation

---

## Step 4: Swing Alerts

**NEVER skip this section — catching swings is a priority.**

For EVERY asset in `watchlist.json`, scan the overnight price action and flag any that moved >1%.

For each flagged asset show:

```
## SWING ALERTS

### ⚡ SWING ALERT — [Asset Name]
- Overnight move: from [low] to [high] = [%] move
- Current price: [price]
- Next swing opportunity: [Buy/Sell] at [level]
- Entry: [price] | Stop Loss: [price] | Take Profit: [price]
- Risk/Reward: [ratio]
- Score: [x/14] (including swing bonus points)
- Better than open trade? [Yes/No — which one to replace]
```

Gold-specific levels to always check:
- Strong support: $4,644 and $4,700 — Buy on touch
- Strong resistance: $4,750, $4,800, $4,858 — Buy on breakout above

---

## Step 5: London Session Opportunities (10:00 Oslo)

Scan ALL `london_session` assets from watchlist.json:
EURUSD, GBPUSD, USDJPY, EURGBP, GBPJPY, XAUUSD, XAGUSD, USOIL, UKOUSD, NATGAS, COPPUSD

Apply: FX-1, FX-2, FX-3 strategies for forex; CMD-1, CMD-2, CMD-3 for commodities.
Check for BOTH Buy AND Sell on every asset. Check for BOTH Tier 1 and Tier 2 setups.

For each asset show one line: **price, % change, signal (Buy/Sell/Neutral)**

Show full TIER 2 trade card only for assets with clear setups and score 6+ out of 14:

```
### RANK #[n] — TIER 2 — PLACE MANUALLY — [ASSET NAME] ([SYMBOL])
Direction: LONG / SHORT
Timeframe: [1H / 4H / Daily]
Session: London 10:00 Oslo
Strategy: [Which strategy from rules.json]
Why: [1-2 sentence catalyst/reason]

Entry: [price]
Stop Loss: [price] — [placement: below support / above resistance / 1.5x ATR]
Take Profit: [price]
Risk/Reward: [ratio]
Position Size: (portfolio × risk%) ÷ stop distance
Units: [calculated]

Order Type: LIMIT / MARKET
Skip If: [condition that invalidates the trade]

Alerts to Set:
  ENTRY — [condition] @ [price]
  STOP LOSS — [condition] @ [price]
  TAKE PROFIT — [condition] @ [price]
```

---

## Step 6: NY Session Opportunities (15:30 Oslo)

Scan ALL `ny_session` assets from watchlist.json:
- Layer 1 Chips: NVDA, AMD, TSM, AVGO, INTC, ARM
- Layer 2 Hyperscalers: MSFT, GOOGL, AMZN, META
- Layer 3 AI Software: PLTR, ORCL, NOW
- Layer 4 Data Centers: DELL, SMCI, CRWV
- Layer 5 Nuclear: CEG, VST, NRG, CCJ
- Layer 6 Materials: FCX, MP, UUUU, ALB
- Layer 7 Networking: ANET, CSCO, MRVL
- High News: TSLA, AAPL, NFLX, COIN, MSTR, CRWD, HOOD, RKLB, BABA, BIDU, IONQ

Apply: IDX-1, IDX-2 for indices; STK-1, STK-2, STK-3 for US stocks.
Check: Earnings calendar — any watchlist stock reporting this week?

For each asset show one line: **price, % change, signal (Buy/Sell/Neutral)**
Show full trade card only for assets with clear setups and score 6+ out of 14.

---

## Step 7: Crypto Session Opportunities (20:00 Oslo)

Scan ALL `crypto_session` assets from watchlist.json:
- Majors: BTCUSD, ETHUSD, SOLUSD, XRPUSD, BNBUSD, ADAUSD, AVAXUSD, LINKUSD
- AI tokens: FETUSD, RENDERUSD, TAOUSD, ARUSD, OCEANPUSD, AGIXUSD, VIRTUALSUSD, WLDUSD

Apply: BTC-1, BTC-2 for Bitcoin; ALT-1 for altcoins.
Check: BTC dominance — rising = avoid altcoins, falling = altcoins outperform.
- Crypto Tier 1: BTC, ETH only (1m-15m charts) — automation only
- Crypto Tier 2: BTC, ETH, SOL, FET, RENDER, TAO (4H-Daily charts) — place manually

For each asset show one line: **price, % change, signal (Buy/Sell/Neutral)**
Show full trade card only for clear setups.

---

## Step 8: All Day Macro Check

Check these macro indicators and flag any significant moves affecting other trades:

| Indicator | What to check |
|-----------|--------------|
| SPY | S&P 500 direction — overall risk sentiment |
| QQQ | Nasdaq 100 — tech/AI sector health |
| DXY | Dollar strength — affects Gold and all USD pairs |
| USOIL | Oil — geopolitical risk gauge (Strait of Hormuz) |
| COPPUSD | Copper — AI/EV demand bellwether, global growth |
| XAGUSD | Silver — AI solar and industrial demand |
| NATGAS | Natural Gas — AI data center energy cost |

---

## Step 9: Trade Recommendations Ranked

Show ALL new opportunities (from Steps 4-7) ranked by score — highest first.

For each clearly state:
- Score out of 14 (including swing bonus points if applicable)
- Is this better than any existing open trade? **Yes or No**
- If Yes — which open trade to cancel and why
- Portfolio % risk this trade would add

```
## RANKED RECOMMENDATIONS

| Rank | Asset | Direction | Entry | R:R | Score /14 | Better than open? | Action |
```

---

## Step 10: Portfolio Risk Summary

```
## PORTFOLIO RISK SUMMARY
- Total portfolio value: [from TradingView account]
- Total % currently at risk: [calculated across all open trades]
- Remaining risk capacity: [5% max - current risk]
- Performance-based sizing tier: [1% / 0.75% / 0.5% / 0.25% based on last 3-5 trades]
- Recommendation: Add more trades / Hold current / Reduce exposure
```

---

## Step 11: Update today.json

After Maria confirms the Tier 2 trades, update `today.json`. Only include Tier 2 trades (Tier 1 are not placed manually).

```json
{
  "date": "Day DD Month YYYY",
  "portfolio_value": 0,
  "max_risk_per_trade_pct": 1,
  "max_total_risk_pct": 5,
  "total_risk_currently_pct": 0,
  "remaining_risk_capacity_pct": 0,
  "open_trades": [],
  "new_opportunities": [],
  "recommendation": ""
}
```

---

## Step 12: Update Journal

Add each new Tier 2 trade to `journal.json` with result set to "PENDING". Do NOT add Tier 1 trades to the journal — they are not executed yet.

---

## Step 13: Place Orders on TradingView

For each confirmed Tier 2 trade, place the order on TradingView paper trading:
1. `chart_set_symbol` — switch to the asset
2. Open order ticket, set Limit price, quantity, TP, SL
3. Submit order (see PAPER_TRADING_ORDERS.md for detailed steps)
4. Verify order appears in Orders tab

Do NOT place orders for Tier 1 trades — they are automation-only.

---

## Key Reminders

- **Never assume direction** — always check both Buy and Sell
- **Never skip an asset** — scan every single one in the watchlist
- **Never skip Swing Alerts** — this is where the biggest wins are
- **Always read watchlist.json, rules.json, today.json first** — before starting any briefing
- **Always rank new opportunities against existing open trades** — swap if better
- **Portfolio % risk management** — no fixed trade count, use 5% max total risk
- **Performance-based sizing** — check last 3-5 trades to determine risk tier (1% / 0.75% / 0.5% / 0.25%)
- **ATR-based stops** — stop distance = 1.5x ATR(14) minimum, reduce position size for wider stops
- **News blackout** — no trades 30 min before/after major releases
- **Weekend rule** — no forex/stock trades Sat-Sun (crypto only)
- **Stop loss is mandatory** — never enter without one, never exit manually before stop is hit
- **Think in R** — 1R = planned risk, present results in R multiples
- **Tier 1 = AUTOMATION ONLY** — never place manually, label clearly
- **Tier 2 = PLACE MANUALLY** — full trade cards, orders, journal entries
