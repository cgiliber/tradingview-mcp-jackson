# DNB Bank (DNBBY) Mean-Reversion C2 v1.0

**Asset:** OTC:DNBBY — DNB Bank ADR (Norwegian bank)
**⚠️ OTC pink sheets — LOW LIQUIDITY warning**

**Timeframe:** 1H
**Direction:** LONG only
**Trading venue:** TradingView Paper Trading (may fail — test first)
**Market hours:** 15:30–22:00 Oslo time

## Edge Discovery

K-Means cluster C2 on v2 feature set.
Binomial p-value = 1.1e-4 (passes within-round Bonferroni).
**Multi-split validation: 5/5 splits passed.**

## Entry Rule (all must be true at 1H bar close)

- `RSI(14) between 28 and 47` (oversold bias)
- `Price -2.67% to -0.36% vs EMA20` (clearly below EMA20)
- `Price in normal EMA50 range`
- `Range/ATR normal`

## Exit Rule

- **Time-based:** close 5 bars after entry
- If fill delay on OTC, use next available price

## Validation

| Test | Result |
|------|--------|
| In-sample (n=243) | 62.6% WR ✓ |
| Multi-split (5 tests) | 5/5 passed ✓ |
| Full-period simulation | 94 trades, 61% WR, **+$1,966** over 2y |
| Monthly avg | **+$86/month** |

**⚠️ Equity curve is LUMPY** — returns cluster around specific periods rather than steady.

## Risk Controls

- $10 max risk per trade
- **REDUCED position: $5K** (not the standard $10K, due to OTC liquidity)
- Skip if volume drops below 100K shares/day (illiquid fills likely)
- Skip if spread > 1% of price (typical: 0.2-0.5%)

## Deployment Checklist — TEST FIRST

1. **Before live paper trading, place ONE $100 test order** to verify OTC acceptance
2. If test order fills normally, proceed with standard setup
3. If rejected, skip this strategy — not tradable on your paper account
4. Chart: **OTC:DNBBY**, 1H
5. Indicators: RSI(14), EMA(20), EMA(50), ATR(14)

## Deployment Risk

This is the weakest of the 4 stock strategies. OTC stocks can have:
- Wide bid/ask spreads (eats profit)
- Delayed fills (slippage)
- Occasional halts
- Quote staleness

**If DNBBY turns out untradable, drop this strategy from portfolio.**
