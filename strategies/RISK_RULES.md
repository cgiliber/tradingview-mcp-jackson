# Risk Management Rules (Universal) v7.0

**Applies to ALL strategies.** These are separate from entry patterns — they govern how much money we risk and when we force-exit.

## Per-trade rules

| Rule | Value |
|------|-------|
| **Position size** | $1,000 (standard across all strategies) |
| **Hard stop loss** | -$10 max loss per trade |
| **Take profit** | +$20 target |
| **Breakeven trigger** | Move stop to entry price when profit hits +$10 |
| **Time exit** | Close at market after 5 bars if neither TP nor SL hit |
| **Session end** | Close ALL stock positions by 21:55 Oslo |

## Portfolio-level rules

| Rule | Value |
|------|-------|
| **Max simultaneous open positions** | 10-20% of paper money |
| **On $100K paper account** | $10K-$20K total exposure = 10-20 open trades max |
| **Per-strategy cap** | Max 3 open positions on same strategy |
| **Correlated-asset cap** | BCS + HSBC + DNBBY combined ≤ $5K (they move together) |

## Order placement — mandatory fields

Every order MUST have:
- Entry price (market or limit)
- **Take Profit** (at least $20 away)
- **Stop Loss** (at most $10 away)

If TP and SL aren't both set, DO NOT submit the order. Refer to `ORDER_PROCEDURE.md`.

## Stop loss translated into % by asset

Since position is $1,000, -$10 loss = -1% from entry. So stop loss = **entry price × 0.99** for LONG, **entry × 1.01** for SHORT.

Take profit +$20 = +2% from entry. So TP = entry × 1.02 (LONG) or 0.98 (SHORT).

## Example — BCS at $10/share

| Action | Price | Reasoning |
|--------|-------|-----------|
| Entry (BUY) | $10.00 | Pattern triggered |
| Shares | 100 | $1000 / $10 = 100 shares |
| Stop loss | $9.90 | Entry × 0.99 = -$10 loss |
| Take profit | $10.20 | Entry × 1.02 = +$20 gain |
| Breakeven move | at $10.10 | Profit = +$10 → move stop to $10.00 |
| Time exit | +5 hours | If neither TP nor SL hit, close at market |

## Example — XRPUSD at $2.50

| Action | Price | Reasoning |
|--------|-------|-----------|
| Entry (BUY) | $2.500 | Pattern triggered |
| Units | 400 | $1000 / $2.50 = 400 XRP |
| Stop loss | $2.475 | Entry × 0.99 |
| Take profit | $2.550 | Entry × 1.02 |
| Time exit | +5 hours | Same as above |

## Why this works across all 7 strategies

The pattern tells us **WHEN** to enter. The risk overlay limits **LOSS** per trade and **CAPS** upside at +2%. Since our patterns' average moves are 0.5-1% over 5 bars, most trades will:
- Hit breakeven at +$10 → stop moves, rest of trade is risk-free
- Expire at time exit after 5 bars if no further move

A few big winners will hit +$20 target for full profit. A few big losers will hit -$10 stop for capped loss.

## What is NOT covered by risk rules

- Pattern selection (that's the entry strategy)
- Signal frequency (pattern-dependent)
- Direction (pattern specifies LONG or SHORT)
- Asset selection (pattern + registry specifies)
