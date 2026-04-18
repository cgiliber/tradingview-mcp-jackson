# HSBC Mean-Reversion C11 v1.0

**Asset:** NYSE:HSBC — HSBC Holdings ADR (US-listed)
**Timeframe:** 1H
**Direction:** LONG only
**Trading venue:** TradingView Paper Trading
**Market hours:** 15:30–22:00 Oslo time

## Edge Discovery

K-Means cluster C11 on v2 feature set.
Binomial p-value = **1.1e-14** (passes Bonferroni by huge margin — strongest signal in dataset).
**Multi-split validation: 5/5 splits passed.**

## Entry Rule (all must be true at 1H bar close)

- `RSI(14) between 33 and 55`
- `Price -1.23% to +0.27% vs EMA20` (price sitting AT or slightly below EMA20)
- `Price in normal EMA50 range`
- `Range/ATR normal`
- `US session hour`

## Exit Rule

- **Time-based:** close 5 bars after entry
- Force-close by 21:55 Oslo if held into US close

## Validation

| Test | Result |
|------|--------|
| In-sample (n=471) | 67.7% WR, p=1.1e-14 ✓ |
| Multi-split (5 tests) | 5/5 passed ✓ |
| Full-period simulation | 149 trades, 66% WR, **+$3,595** over 2y |
| Monthly avg | **+$159/month** |

## Risk Controls

- $10 max risk per trade
- Position size: $10K
- Skip if HSBC earnings within 2 days
- Skip during major Asian market crisis (HSBC has heavy Asia exposure)

## Deployment Checklist

1. Chart: **NYSE:HSBC**, 1H
2. Indicators: RSI(14), EMA(20), EMA(50), ATR(14)
3. Hourly scan during US session
4. BUY → 5-bar exit
