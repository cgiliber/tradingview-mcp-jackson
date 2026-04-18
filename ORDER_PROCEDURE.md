# Order Placement Procedure v2.0

**Purpose:** Standardize order placement to prevent the mistakes we hit before switching to pattern R&D.

## Previous Mistakes (must not repeat)

| # | Mistake | Fix |
|---|---------|-----|
| 1 | Missing TP/SL on orders | ALWAYS verify TP and SL fields are filled before submit |
| 2 | Wrong direction TP/SL (TP below entry on a short) | Verify: LONG → TP > entry > SL; SHORT → SL > entry > TP |
| 3 | Pre-market rejection | Only place stock orders 15:30-21:55 Oslo |
| 4 | European stocks silently rejected | Only trade: Binance crypto 24/7, US stocks & US-listed ADRs (NYSE/NASDAQ) during US hours |
| 5 | Stop loss only 1 tick from entry | Require minimum stop distance: $0.05 for stocks, 0.3% for crypto, 0.03% for forex |
| 6 | Assumed fill without verification | After every order: screenshot + check positions panel to confirm |
| 7 | Overnight holds on stocks | Close ALL stock positions by 21:55 Oslo |

## Standard Procedure (every order)

1. **Pre-check**
   - Confirm asset is supported on paper account (see strategies/REGISTRY.json)
   - Confirm market hours for the asset
   - Confirm no pending earnings/news event for that asset

2. **Sizing**
   - Default: $10,000 position per trade
   - Crypto: $5,000 (higher vol)
   - OTC stocks (DNBBY): $5,000 (liquidity risk)

3. **Entry order (place via TradingView MCP)**
   - Use MARKET order for signals that require immediate entry
   - Use LIMIT order at pattern close price +/- 0.01% for non-urgent entries

4. **Take Profit (mandatory)**
   - For strategies with **time-based exit** (all 7 current strategies): set TP far away (e.g., +2 ATR) — TP shouldn't trigger before timer
   - For rules-based TP: explicit price from strategy config

5. **Stop Loss (mandatory)**
   - For time-based exit strategies: set SL at -2 ATR — emergency brake only
   - For rules-based SL: explicit price from strategy config
   - NEVER submit order without SL

6. **Direction verification — READ BACK the order**
   - LONG: entry < TP AND entry > SL
   - SHORT: entry > TP AND entry < SL
   - If inverted, CANCEL order

7. **Post-submit verification**
   - Wait 2 seconds
   - `chart_get_state` → confirm position shows in positions panel
   - `capture_screenshot` → save visual record
   - If not filled after 10 seconds, investigate before retrying

8. **Exit — time-based strategies**
   - Schedule close at entry_time + 5 hours
   - Set calendar reminder OR use broker OCO/timer feature
   - If 5-hour exit happens after market close, close at market close instead

9. **Exit — force conditions**
   - Stock positions: close by 21:55 Oslo regardless of strategy rule
   - Before major news event: close all positions in affected asset
   - Broker disconnection: flag for manual intervention

## Asset-Specific Rules

### Binance crypto (24/7)
- Use BINANCE:<SYM>USDT on TradingView
- Paper trading fills are realistic
- No overnight risk (always open)
- Assumed cost: 0.15% round-trip

### US stocks / US-listed ADRs (15:30-22:00 Oslo)
- NYSE and NASDAQ symbols fill normally on paper
- Watch for pre-market (before 15:30) → orders WILL BE REJECTED
- Earnings after close can gap the stock → close by 21:55

### OTC stocks (DNBBY)
- Pink sheet fills are SLOW and uncertain
- Test with small order before committing to strategy
- May need to skip if paper account rejects

### Forex (EURGBP)
- TradingView Paper Trading usually defaults to stocks, not forex
- Check if OANDA or Saxo broker is connected to account
- If not, EURGBP strategy cannot run in paper mode — use real broker or skip

## Auto-Scanner Integration

The scanner reads `strategies/REGISTRY.json` to know:
- Which assets to scan
- What trigger rules to evaluate
- What market hours apply
- Where to place orders

**Every scan cycle:**
1. Check time against each strategy's market hours
2. For active strategies only, fetch latest 1H bar
3. Compute indicators (RSI, EMAs, ATR, range, volume, hour)
4. For crypto: also fetch latest funding rate
5. Check each strategy's entry rule
6. On match: follow procedure above

## Emergency Protocol

If an order misbehaves:
1. **STOP** — do not retry
2. Screenshot the state
3. Check positions panel for accidental fills
4. If accidental position opened, close manually at market
5. Log incident in `INCIDENT_LOG.md`
6. Identify root cause before next trade

## Verification Checklist (use every trade)

```
[ ] Asset is supported by paper account
[ ] Market is open for that asset
[ ] Position size matches strategy config
[ ] TP field filled
[ ] SL field filled
[ ] Direction verified (TP/SL on correct side)
[ ] Order submitted
[ ] Position confirmed in panel
[ ] Screenshot saved
[ ] Exit timer set (for time-based strategies)
```

If ANY box unchecked → do not proceed.
