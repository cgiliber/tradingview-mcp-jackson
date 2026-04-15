# Trader Workflow v2 — Be Aggressive, Play Small

**Philosophy: Many small wins. Tiny stops. NEVER sit on the sidelines when momentum is right there.**

$10 risk per trade. Win $20. Do it 5-8 times a day. That's $100-$160/day = $3,000/month.

## Scan Frequency

| Window (Oslo) | Interval | Why |
|---------------|----------|-----|
| **15:30-17:00** | **Every 5 min** | NY open power hour — gaps spike, biggest moves happen here |
| **17:00-22:00** | Every 15 min | Regular session — monitor and catch late runners |
| **22:00** | CLOSE ALL | End of day — no overnight holds |

## Step 1: Find Movers

```
node scanner/trader-scan.js
```

Finviz scans the ENTIRE US market for free. Top 10 movers by % change. Start from #1 going down.

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
- Above BB upper WITH rising volume (momentum breakout, NOT exhaustion)

### SKIP ONLY if:
- Volume dead (<500 shares per candle)
- Price under $1 (too thin)
- Making lower highs AND lower lows (downtrend)
- Already in this position

### THESE ARE NOT VALID SKIP REASONS:
- "Above BB upper" — momentum stocks live above BB. That's the signal.
- "Extended from EMA" — gap stocks ARE extended. That's normal.
- "Late in the day" — if there's 1+ hour left, trade it.
- "Already have positions open" — with $10 risk each, 5 positions = $50 total risk. That's fine.
- "Might reverse" — everything might reverse. That's what the stop loss is for.
- "Too volatile" — volatile = opportunity. Tight stop + small size = controlled risk.

## Step 3: Size and Execute

1. **Stop**: Below last candle low OR below EMA 8. Whichever is TIGHTER.
2. **Units**: FLOOR($10 / stop_distance)
3. **TP**: Entry + (2 × stop_distance) = target +$20
4. **Place**: Market order with TP and SL
5. **At +$10**: Move SL to breakeven. IMMEDIATELY. No waiting.
6. **At +$20**: CLOSE. Take the $20. Find next trade.

## Step 4: Log to journal.json

Every trade and every skip with reason. Update after each trade.

## Step 5: Check Open Positions

1. Quote each position
2. At +$10 unrealized → move SL to breakeven
3. At +$20 unrealized → CLOSE position
4. Close ALL by 22:00 Oslo

## Mindset Rules

- **Default is TRADE, not SKIP.** You need a reason NOT to trade, not a reason to trade.
- **5 trades per day minimum target.** If you've done 0 trades by 17:00 Oslo, you're too scared.
- **$10 risk is nothing.** That's 0.01% of portfolio. Stop treating it like $1,000.
- **Speed matters.** Scan → chart → 10 seconds → decide → place. Don't overthink.
- **ASTI lesson:** Staircase up, volume surging, skipped because "above BB." Missed +$23.50. Never again.
