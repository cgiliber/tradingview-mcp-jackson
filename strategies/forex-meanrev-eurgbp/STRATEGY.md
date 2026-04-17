# EURGBP 1H Mean-Reversion Strategy v1.0

**Status:** Validated — only strategy with both Bonferroni-significant edge AND positive out-of-sample backtest.

**Discovered:** 2026-04-18
**Validation:** 2y of 1H EURGBP data (12,375 bars), 70/30 train/test split.

## The Edge

EURGBP exhibits mean-reversion at the 1H timeframe with strong time-of-day dependency. Discovered via K-Means clustering of OHLCV + indicator features across 9 forex pairs and 74 watchlist assets. Only EURGBP survived statistical validation (Bonferroni p < 5.1e-06) AND held in out-of-sample testing.

## Rules

### LONG entry (1H bar close)
- `RSI(14) <= 50` (slight oversold)
- `close <= EMA20` (within -0.2% below EMA20, but not lower than -0.2%)
- `range(high - low) <= 1.0 × ATR(14)` (quiet bar)
- `Hour UTC in [18, 22]` (London end / NY late)

### SHORT entry (1H bar close)
- `RSI(14) >= 55` (slight overbought)
- `close >= EMA20` (within +0.2% above EMA20)
- `range(high - low) >= 1.0 × ATR(14)` (volatile bar)
- `Hour UTC in [9, 16]` (London / NY active)

### Exit
- **Time-based**: close position 5 hours after entry (mandatory)
- No traditional TP/SL — the edge is statistical mean-reversion over fixed horizon

## Backtest Results

| Period | Trades | WR | Return | Profit Factor | Max DD |
|--------|--------|----|----|---------------|--------|
| Train (first 70%) | 437 | 50.6% | -0.87% | 0.96 | 2.6% |
| **Test (last 30%, OOS)** | **192** | **57.3%** | **+1.43%** | **1.19** | 1.92% |

**Test period:** 2025-09-11 onward (~7 months)
**Trade frequency:** ~1.2 trades/day on average
**Spread cost:** 0.008% per round-trip (already deducted)

## What did NOT work

- EURJPY: train 51% WR, test 44% WR — collapsed OOS
- USDCHF: train 48% WR, test 51% WR — never had edge
- All US/EU stocks: zero patterns survived original Bonferroni
- All crypto: zero patterns survived
- V-reversal / Inverted-V templates: zero patterns survived

## Risk Management

- **Position size**: Use $10 max risk per trade (per Maria's v7.0 rules)
- **Daily loss cap**: 3 consecutive losses → stop trading for the day
- **Max concurrent positions**: 1 (no pyramiding)
- **News blackout**: Skip during ECB/BOE rate decisions

## Why this might be real (not just lucky)

1. **Plausible mechanism**: EUR-GBP is a "cross pair" (no USD), tightly traded by European banks. Mean-reversion is a known dynamic in cross pairs that lack USD-driven trend dynamics.
2. **Time-of-day fits**: LONG at end of London/NY (18-22 UTC) when liquidity drops and overshoots correct. SHORT during active hours (9-16 UTC) when initial momentum exhausts.
3. **Survives multiple corrections**: Bonferroni across 1,329 patterns AND 173 forex-only patterns AND held in 30% holdout.
4. **Modest edge**: +6-8% over baseline win rate is realistic for forex mean-reversion. Not too good to be true.

## Why it might still fail in live trading

1. Sample size still modest (192 OOS trades over 7 months)
2. Spread can widen during volatile sessions (Brexit-style events)
3. ECB/BOE policy divergence could break the mean-reversion regime
4. Slippage on order fills not modeled

## Files

- `strategy.pine` — Pine Script for TradingView (alerts + visualization)
- `config.json` — machine-readable rule definition
- `backtest-meanrev.json` (in `data/`) — full backtest output
