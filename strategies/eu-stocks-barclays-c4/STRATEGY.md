# Barclays (BCS) Alternative Pattern C4 v1.0

**Asset:** NYSE:BCS — Barclays ADR
**Timeframe:** 1H
**Direction:** LONG only
**⚠️ MARGINAL STRATEGY — trust cautiously, track performance closely**

## Edge Discovery

K-Means cluster C4 on v2 features (separate pattern from C2).
Multi-split validation: 5/5 splits passed, but **equity curve was flat for 1 year then spiked in 2026-04**. Recent outperformance may be partly luck.

## Entry Rule

- `RSI(14) between 36 and 59`
- `Price -1.43% to +0.59% vs EMA20`
- Similar to BCS C2 but broader RSI range

## Exit Rule

- Close 5 bars after entry

## Validation

| Test | Result |
|------|--------|
| Multi-split | 5/5 passed |
| Full-period | 163 trades, 56% WR, +$1,264 over 2y |
| Monthly avg | **+$54/month** |

## Warning

**Avg per trade is only +$7.76** — very thin edge, barely covers slippage in live trading. Paper results may NOT transfer to live.

## Risk Controls

- $10 max risk per trade
- Position size: $10K
- **After 30 days of paper trading, review:** if real results underperform backtest by >30%, deactivate

## Coordination with BCS C2

**Do not run both BCS C2 and BCS C4 simultaneously** on the same BCS ticker. The triggers overlap partially; running both doubles exposure without doubling edge. **Pick ONE** — BCS C2 has the stronger edge.

Recommendation: **deactivate BCS C4, keep only BCS C2**.
