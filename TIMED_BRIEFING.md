# Timed Briefing — 15-Minute Market Monitor

This runs every 15 minutes during active trading sessions. It is SEPARATE from the morning briefing (MORNING_BRIEF.md). Do NOT mix these two workflows.

---

## When to Run

- **London session**: 10:00-18:00 Oslo — every 15 min
- **NY session**: 15:30-22:00 Oslo — every 15 min
- **Crypto**: 24/7 — every 15 min during peak (20:00-00:00), every 30 min otherwise
- **Outside active sessions**: do not run

---

## What to Check (7 steps)

### Step 1: Check Open Positions (from TradingView broker, NOT today.json)
- Get quote for all open positions directly from TradingView paper trading
- Check if any stop or target is about to be hit (within 0.5%)
- If a stop or target was hit since last check → update journal.json, flag to Maria

### Step 2: Check Standing/Pending Orders
- Check if any limit order has been filled
- If filled → update journal.json, notify Maria
- VERIFY all orders have TP and SL set — if missing, ALERT and fix immediately

### Step 3: Scan WATCHLIST for Swing Alerts
- **Scan watchlist.json directly — NOT today.json**
- For the correct session (London/NY/Crypto), get current price for EACH asset
- Compare with previous day close or last known price
- If any asset moved >1% since last check → flag as ⚡ SWING ALERT
- If any asset moved >2% today → flag as ⚡⚡ MAJOR SWING ALERT

### Step 4: Scan for BREAKOUTS (catches moves like META +20%)
- For each asset in the active session's watchlist:
  - Check if price broke above previous day high with above-average volume → **BREAKOUT BUY signal**
  - Check if price broke below previous day low with above-average volume → **BREAKOUT SELL signal**
  - Check if price gapped >2% from previous close → **GAP ALERT**
- A breakout on a watchlist asset is a trade opportunity even if it wasn't in today.json
- Apply Ross Cameron's STK-1 Bull Flag strategy for breakout entries

### Step 5: Score Opportunities
- For each swing alert AND breakout signal, calculate trade score (14-point system + bonuses)
- Swing bonus: +2 for S/R bounce, +2 for >1% move, +1 for volume confirmation
- Breakout bonus: +2 for gap >2%, +2 for volume >2x average, +1 for above all EMAs
- Check: is portfolio heat below 5%?
- Rank all opportunities — highest score first

### Step 6: Auto-Execute or Alert

**IF all auto-execute conditions met:**
- Place the order automatically on TradingView paper trading
- Use 0.5% risk (half of normal)
- Must have ATR-based stop
- Set TP and SL BEFORE submitting (MANDATORY — never skip)
- Run post-order verification (MANDATORY — never skip)
- Log to `auto-trades.json` with full score breakdown
- Update journal.json with tag "AUTO-EXECUTED"
- Notify Maria immediately

**IF conditions not fully met:**
- Show the opportunity to Maria but do NOT auto-execute
- Wait for confirmation

### Step 7: Tier 1 vs Tier 2 Conflict Check
- If a Tier 1 signal conflicts with a Tier 2 trade on the same asset:
  - Check 1H and Daily trend
  - Higher TF agrees with Tier 2 → Tier 1 is noise, ignore
  - Higher TF agrees with Tier 1 → flag Tier 2 for review

---

## Output Format

Keep it brief — this is a quick check, not a full briefing.

```
## TIMED CHECK — [HH:MM Oslo]

### Positions (from TradingView broker)
| Asset | Direction | Entry | Current | P&L | Dist to SL | Status |

### Watchlist Movers (>1% moves)
| Asset | Previous | Current | Move % | Signal |

### Breakouts (prev day high/low breaks)
⚡ BREAKOUT: [Asset] broke above [prev high] @ [price] — volume [x]

### Swing Alerts
⚡ [Asset] moved [%] — [details]

### Auto-Executed (if any)
🤖 AUTO-EXECUTED: [Asset] [Direction] @ [price] — Score [x/14] — [reason]

### No Action
[x] assets checked — no significant moves
```

---

## Priority Scanning Order

During each session, scan assets in this priority:
1. **Open positions** — always first (risk management)
2. **Pending orders** — check if any filled
3. **Priority assets** — Gold, Oil, BTC, major forex (every check)
4. **Session-specific assets** — London assets during London, NY during NY, Crypto during crypto
5. **Full watchlist scan** — every 4th check (once per hour) scan ALL assets

---

## Auto-Execute Rules (from rules.json)

| Criteria | Value |
|----------|-------|
| Minimum score | None — no threshold, use ranking to prioritize |
| Max risk | 0.5% of portfolio |
| Max auto-trades/day | 2 |
| Required | ATR stop + TP and SL set + portfolio heat <5% |
| Forbidden | News blackout, weekend non-crypto |
| After execution | Notify Maria, log to auto-trades.json and journal.json |
| Post-order check | MANDATORY — verify TP and SL are set after every order |

---

## Files Used

| File | Read/Write | Purpose |
|------|-----------|---------|
| `watchlist.json` | **Read — PRIMARY source for asset scanning** |
| `rules.json` | Read | Scoring system, S/R levels, strategies, auto-execute criteria |
| `journal.json` | Write | Log filled orders and auto-trades |
| `auto-trades.json` | Write | Dedicated log for auto-executed trades |
| `today.json` | Read only | Morning snapshot reference — NOT the limiter for scanning |

---

## Critical Rules

- **Scan watchlist.json directly** — NEVER limit scanning to only today.json
- **Check for breakouts** — price above prev day high with volume = opportunity
- **Check for gaps** — >2% gap from prev close = major alert
- **Every order MUST have TP and SL** — verify after every placement
- **Do NOT skip any asset** — META +20% was missed because we only checked today.json
- Auto-trades go in `auto-trades.json` separately
- Always notify Maria after any auto-execution
