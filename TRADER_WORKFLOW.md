# Trader Workflow v3 — Be Aggressive, Verify Everything

**Philosophy: Many small wins. Tiny stops. NEVER assume — always VERIFY.**

$10 risk per trade. Win $20. Do it 5-8 times a day. That's $100-$160/day = $3,000/month.

## Scan Frequency

| Window (Oslo) | Interval | Why |
|---------------|----------|-----|
| **15:30-17:00** | **Every 5 min** | NY open power hour — gaps spike, biggest moves happen here |
| **17:00-22:00** | Every 15 min | Regular session — monitor and catch late runners |
| **20:00-07:00** | Every 15-30 min | Crypto — CoinGecko scanner |
| **22:00** | CLOSE ALL stocks | No overnight stock holds |

## Step 1: Find Movers

```
node scanner/trader-scan.js          # Stocks: Finviz gainers + losers
node scanner/trader-scan.js --crypto # Crypto: CoinGecko
node scanner/trader-scan.js --all    # Both
```

Start from #1 going down. Both LONG (gainers) and SHORT (losers).

## Step 2: Analyze Charts (Top 10, starting from #1)

For EACH mover, open the chart:
```
chart_set_symbol → symbol, chart_set_timeframe → "15"
quote_get + data_get_study_values + data_get_ohlcv summary:true
```

### Quick check (10 seconds per stock):
1. **Price above EMA 8?** → momentum is alive
2. **Staircase pattern?** (higher lows, higher highs) → GO signal
3. **Volume above average?** → real buyers, not fake
4. **Price $1+ and volume 1K+?** → tradeable

### ENTER if ANY of these are true:
- Staircase up on volume (each candle makes higher low)
- Pullback to EMA 8 and bouncing
- Breaking above a consolidation range
- Above BB upper WITH rising volume (momentum breakout)

### SKIP ONLY if:
- Volume dead (<500 shares per candle)
- Price under $1 (too thin)
- Making lower highs AND lower lows (downtrend)
- Already in this position

### NOT valid skip reasons:
- "Above BB upper" — momentum stocks live there
- "Extended from EMA" — gap stocks ARE extended
- "Late in the day" — if 1+ hour left, trade it
- "Already have positions" — 5 × $10 = $50 risk, fine
- "Too volatile" — that's the opportunity

## Step 3: Size and Execute

1. **Stop**: Below last candle low OR below EMA 8. Whichever is TIGHTER.
2. **Units**: FLOOR($10 / stop_distance)
3. **TP**: Entry + (2 × stop_distance) = target +$20
4. **Place**: Market order with TP and SL

## Step 4: MANDATORY VERIFICATION — NEVER SKIP

**After EVERY order action (place, close, modify SL), do ALL of these:**

### 4a. After placing a trade:
```
1. capture_screenshot → verify order panel shows "Order sent" or "Filled"
2. Read positions table → confirm new position appears with correct qty, TP, SL
3. If TP or SL missing → ALERT and fix immediately
4. Only THEN report "trade placed"
```

### 4b. After closing a position:
```
1. capture_screenshot → verify position is GONE from positions table
2. Count positions → confirm count decreased by 1
3. If position still there → click Close again and re-verify
4. Only THEN report "position closed"
```

### 4c. After modifying SL (breakeven lock):
```
1. Re-read the position → confirm SL value actually changed
2. If old SL still showing → modify again and re-verify
3. Only THEN report "SL moved to breakeven"
```

### 4d. After TP/SL should have triggered:
```
1. NEVER assume TP/SL hit based on price movement alone
2. Check positions table → is the position still there or gone?
3. Check order history → find the specific fill: "Take Profit filled" or "Stop Loss filled"
4. Only THEN report the result
```

### CRITICAL RULE: Never say "TP hit" or "SL triggered" without checking order history on TradingView. Price going past TP doesn't mean the order filled — verify it.

## Step 5: Market Hours Check — BEFORE Any Stock Action

**NEVER try to place, close, or modify a US stock order outside market hours.**

| Market | Open (Oslo) | Close (Oslo) | Days |
|--------|-------------|--------------|------|
| US stocks (NYSE/NASDAQ) | 15:30 | 22:00 | Mon-Fri |
| EU stocks (ADR) | 15:30 | 22:00 | Mon-Fri |
| Crypto | 24/7 | 24/7 | Every day |
| Forex | 24/7 (Sun 23:00 - Fri 23:00) | — | Sun-Fri |

**Before ANY stock order action:**
1. Check Oslo time with `date`
2. If before 15:30 or after 22:00 → **DON'T TRY.** Paper trading won't execute.
3. If stock needs closing and market is closed → **set a reminder for 15:30, not now**
4. Crypto and forex can trade anytime

**STLA lesson:** Tried to close NYSE stock at 21:50 and 07:00 Oslo. Both failed silently. Wasted time. The order just doesn't execute outside hours.

## Step 6: Profit Management

1. **At +$10 unrealized** → move SL to breakeven → VERIFY per 4c
2. **At +$20 unrealized** → CLOSE position → VERIFY per 4b (only during market hours for stocks)
3. Close ALL stocks by **21:55 Oslo** (5 min before close, not AT close) → VERIFY each one closed

## Step 6: Log to journal.json

Every trade with VERIFIED entry price, exit price, and P&L. Not assumed — verified.

## Mindset Rules

- **Default is TRADE, not SKIP.**
- **VERIFY everything.** Never assume an action worked.
- **$10 risk is nothing.** 0.01% of portfolio.
- **Speed matters.** But verification matters more.
- **ORDI lesson:** Assumed TP hit because price went above target. Actually SL hit first during a dip. Never assume — check order history.
- **STLA lesson:** Clicked "Close position" but it didn't execute. Never assume — verify position is gone.
