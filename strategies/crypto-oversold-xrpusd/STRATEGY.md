# XRPUSD Deep Oversold Bounce v1.0

**Asset:** XRPUSD (Ripple) — Binance perpetual and spot
**Timeframe:** 1H
**Direction:** LONG only
**Trading venue:** Binance (via TradingView Paper Trading)
**Market hours:** 24/7

## Edge Discovery

K-Means cluster C1 on v5 feature set (OHLCV + RSI + EMAs + ATR + volume + funding rate).
Binomial p-value = **8.9e-7** (passes strict Bonferroni correction).

## Entry Rule (all must be true at 1H bar close)

- `RSI(14) between 16 and 46` (deeply oversold)
- `Price -11% to -1.7% below EMA20` (extended down)
- `Price -11% to -3% below EMA50`
- `Range/ATR(14) between 0.2 and 2.1`

**Economic rationale:** After a sharp XRP drop, oversold conditions near major EMAs create a mean-reversion bounce opportunity. The 73% training win rate reflects crowd over-selling.

## Exit Rule

- **Time-based:** close position exactly 5 bars (5 hours) after entry
- No traditional stop loss
- Trade cost assumed: 0.15% round-trip (Binance spot 0.1% × 2)

## Validation

| Test | Result |
|------|--------|
| In-sample cluster (n=111) | 73% WR, Bonferroni p=8.9e-7 ✓ |
| Out-of-sample 70/30 | 54 trades, 59.3% WR, +2.47% return ✓ |

## Risk Controls

- $10 max risk per trade (per v7 rules)
- Position size: $10K default
- Skip trade if XRPUSD daily range > 10% (too volatile, regime change)

## Known Limitations

- Only 111 training samples — variance per trade is real
- XRPUSD can have sudden regulatory news (SEC cases) that break the pattern
- Signal rare (~5 per month) — not a high-frequency edge

## Deployment Checklist

1. TradingView chart: set to BINANCE:XRPUSDT, 1H timeframe
2. Add indicators: RSI(14), EMA(20), EMA(50), ATR(14)
3. Monitor for signal match each hour at :00 close
4. On signal, place market BUY order
5. Set 5-bar timer or calendar reminder to close at entry_time + 5 hours
