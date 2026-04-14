# Session Briefing — Multi-Strategy System

Triggered by the word **"briefing"** at ANY time of day. Claude auto-detects Oslo time and runs relevant strategies.

---

## Trigger Words

| Command | Action |
|---------|--------|
| `"briefing"` | Auto-detect Oslo time → run relevant strategies for current session |
| `"full briefing"` | Run ALL 6 strategies regardless of time |
| `"run GAP-AND-GO"` | Read `/strategies/gap-and-go/` rules and watchlist only |
| `"run SWING-TRADE"` | Read `/strategies/swing-trade/` rules and watchlist only |
| `"run OVERNIGHT-SWING"` | Read `/strategies/overnight-swing/` rules and watchlist only |
| `"run CRYPTO-MOMENTUM"` | Read `/strategies/crypto-momentum/` rules and watchlist only |
| `"run RESOURCE-COMMODITY"` | Read `/strategies/resource-commodity/` rules and watchlist only |
| `"run PENNY-STOCK-MOMENTUM"` | Scan Finviz + Warrior Trading (Apify) → return top 3-5 candidates with scores |
| `"penny scan"` | Shortcut → run PENNY-STOCK-MOMENTUM scanner immediately |
| `"gap scan"` | Shortcut → run GAP-AND-GO scanner immediately |
| `"crypto scan"` | Shortcut → run CRYPTO-MOMENTUM scanner immediately |
| `"resource scan"` | Shortcut → run RESOURCE-COMMODITY scanner immediately |
| `"swing scan"` | Shortcut → run SWING-TRADE scanner immediately |
| `"overnight scan"` | Shortcut → run OVERNIGHT-SWING scanner immediately |

---

## Session Detection (Oslo Time)

### BEFORE LONDON (before 10:00 Oslo)
- **GAP-AND-GO** — check pre-market gappers >4% preparing for NY open later
- **RESOURCE-COMMODITY** — check Gold, Silver, Oil overnight moves and swing alerts
- **OVERNIGHT-SWING** — check if any overnight positions need managing at London open

### LONDON SESSION (10:00–15:30 Oslo)
- **SWING-TRADE** — scan London assets: EURUSD, GBPUSD, USDJPY, XAUUSD, Silver, Oil
- **RESOURCE-COMMODITY** — Gold and Oil setups
- **GAP-AND-GO** — flag candidates building pre-market for NY open at 15:30

### NY SESSION (15:30–22:00 Oslo)
- **GAP-AND-GO** — execute if pre-market gapper found with catalyst
- **PENNY-STOCK-MOMENTUM** — scan Finviz screener + Warrior Trading page (Apify) for penny stocks gapping >4% with catalyst. Show top 3-5 with scores out of 9. Only trade if score 5+.
- **SWING-TRADE** — scan all NY assets: full AI ecosystem watchlist
- **RESOURCE-COMMODITY** — Oil and Copper

### CRYPTO SESSION (20:00–00:00 Oslo)
- **CRYPTO-MOMENTUM** — scan all crypto assets

---

## ALWAYS Include in Every Briefing (regardless of time)

1. Read `today.json` — check all open trades, one line status each
2. Read TradingView broker panel — verify positions match
3. Calculate total portfolio % currently at risk and remaining capacity
4. **SWING ALERTS** — scan ALL watchlist assets for overnight or intraday moves >1%, flag immediately
5. If a new opportunity scores higher than an open trade — recommend which to cancel and why

---

## Briefing Output Format

Every briefing MUST follow this structure:

### 1. MACRO OVERVIEW
- Geopolitical events affecting markets today
- Economic data releases today (PPI, CPI, NFP, Fed, ECB, BOJ, earnings)
- Fear & Greed index direction
- DXY (Dollar) direction — affects Gold and all USD pairs

### 2. OPEN TRADES STATUS
```
| Asset | Dir | Entry | Current | P&L | Dist to SL | Dist to TP | Score /5 | Recommendation |
```
One line per trade. Recommendation: Hold / Watch / Consider closing.

### 3. SWING ALERTS
For any asset that moved >1% overnight or intraday:
```
⚡ SWING ALERT — [Asset Name]
- Move: from [low] to [high] = [%]
- Current: [price]
- Next opportunity: [Buy/Sell] at [level]
- Entry / SL / TP / R:R
- Better than open trade? [Yes/No]
```

### 4. SESSION OPPORTUNITIES
Ranked trade cards by score — highest first:
```
RANK #[n] — [STRATEGY LABEL] — [TIER LABEL]
Symbol: [symbol]
Direction: Buy or Sell
Entry: [price]
Stop Loss: [price]
Take Profit: [price]
Risk/Reward: [ratio]
Units: [calculated for 1% risk with proper sizing]
Score: [x/5]
Catalyst: [reason]
Strategy: GAP-AND-GO / SWING-TRADE / OVERNIGHT-SWING / CRYPTO-MOMENTUM / RESOURCE-COMMODITY
Tier: TIER 1 AUTOMATION ONLY or TIER 2 PLACE MANUALLY
Better than open trade? Yes/No — if yes, which one to replace
```

### 5. PORTFOLIO RISK SUMMARY
```
- Total portfolio value: [from TradingView]
- Total % at risk: [calculated]
- Remaining capacity: [5% max - current]
- Market regime: BULL / BEAR / NEUTRAL
- Recommendation: Add trades / Hold / Reduce exposure
```

---

## Strategy Files Location

| Strategy | Rules | Watchlist |
|----------|-------|-----------|
| GAP-AND-GO | `/strategies/gap-and-go/rules.json` | `/strategies/gap-and-go/watchlist.json` |
| SWING-TRADE | `/strategies/swing-trade/rules.json` | `/strategies/swing-trade/watchlist.json` (refs root) |
| OVERNIGHT-SWING | `/strategies/overnight-swing/rules.json` | `/strategies/overnight-swing/watchlist.json` |
| CRYPTO-MOMENTUM | `/strategies/crypto-momentum/rules.json` | `/strategies/crypto-momentum/watchlist.json` |
| RESOURCE-COMMODITY | `/strategies/resource-commodity/rules.json` | `/strategies/resource-commodity/watchlist.json` |
| PENNY-STOCK-MOMENTUM | `/strategies/penny-stock-momentum/rules.json` | `/strategies/penny-stock-momentum/watchlist.json` (dynamic) |

Root `rules.json` and `watchlist.json` remain the master reference. Strategy files are used when a specific strategy is called.

---

## Critical Rules

- **Scan watchlist.json directly** — never limit to today.json
- **Every order MUST have TP and SL** — verify after placement
- **Proper position sizing** — use v6.0 formula: Units = (Portfolio × Risk%) ÷ Stop Distance
- **Market regime detection** — check SPY/QQQ/DXY/BTC vs 20 EMA before setting limit distances
- **Bull regime**: limits 1-2% below, market orders for breakouts
- **Bear regime**: limits at support, no market orders
- **Never trade against the higher timeframe trend**
