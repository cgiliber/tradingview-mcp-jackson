# Timed Briefing — 15-Minute Market Monitor

This runs every 15 minutes during active trading sessions. It is SEPARATE from the morning briefing (MORNING_BRIEF.md). Do NOT mix these two workflows.

---

## When to Run

- **London session**: 10:00-18:00 Oslo — every 15 min
- **NY session**: 15:30-22:00 Oslo — every 15 min
- **Crypto**: 24/7 — every 15 min during peak (20:00-00:00), every 30 min otherwise
- **Outside active sessions**: do not run

---

## What to Check (5 steps, keep it fast)

### Step 1: Check Open Positions
- Get quote for all open positions from today.json
- Check if any stop or target is about to be hit (within 0.5%)
- If a stop or target was hit since last check → update journal.json, flag to Maria

### Step 2: Check Standing Orders
- Check if any standing limit order has been filled
- If filled → update journal.json and today.json, notify Maria

### Step 3: Scan for Swing Alerts
- For each asset in watchlist.json, get current price
- Compare with price from last check (or today's open if first check)
- If any asset moved >1% since last check → flag as ⚡ SWING ALERT

### Step 4: Score Swing Alerts
- For each swing alert, calculate trade score (14-point system + swing bonuses)
- Check: is it at a defined support/resistance level?
- Check: is portfolio heat below 5%?

### Step 5: Auto-Execute or Alert

**IF score >= 11 AND all auto-execute conditions met:**
- Place the order automatically on TradingView paper trading
- Use 0.5% risk (half of normal)
- Must have ATR-based stop at defined S/R level
- Log to `auto-trades.json` with full score breakdown
- Update journal.json with tag "AUTO-EXECUTED"
- Notify Maria immediately

**IF score >= 6 but < 11:**
- Show the opportunity to Maria
- Do NOT auto-execute — wait for confirmation

**IF score < 6:**
- Log it but don't alert — not worth trading

---

## Output Format

Keep it brief — this is a quick check, not a full briefing.

```
## TIMED CHECK — [HH:MM Oslo]

### Positions
| Asset | Direction | Entry | Current | P&L | Dist to SL | Status |

### Alerts
⚡ [Asset] moved [%] — [details]

### Auto-Executed (if any)
🤖 AUTO-EXECUTED: [Asset] [Direction] @ [price] — Score [x/14] — [reason]

### No Action
[x] assets checked — no significant moves
```

---

## Auto-Execute Rules (from rules.json)

| Criteria | Value |
|----------|-------|
| Minimum score | 11/14 |
| Max risk | 0.5% of portfolio |
| Max auto-trades/day | 2 |
| Required | ATR stop + defined S/R level + portfolio heat <5% |
| Forbidden | News blackout, weekend non-crypto, score <11 |
| After execution | Notify Maria, log to auto-trades.json and journal.json |

---

## Files Used

| File | Read/Write | Purpose |
|------|-----------|---------|
| `watchlist.json` | Read | Asset list to scan |
| `today.json` | Read + Write | Open trades, filled orders |
| `journal.json` | Write | Log filled orders and auto-trades |
| `auto-trades.json` | Write | Dedicated log for auto-executed trades |
| `rules.json` | Read | Scoring system, S/R levels, auto-execute criteria |

---

## Important

- This is a LIGHTWEIGHT check — do NOT run full news searches or macro analysis
- Do NOT update today.json structure — only update statuses of existing trades
- Do NOT add new trade opportunities to today.json — that's the morning briefing's job
- Auto-trades go in `auto-trades.json` separately
- Always notify Maria after any auto-execution
