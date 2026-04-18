# Barclays (BCS) Mean-Reversion C2 v1.0

**Asset:** NYSE:BCS — Barclays PLC ADR (US-listed)
**⚠️ IMPORTANT:** This is the NYSE ADR, not the London LSE listing. ADR trades during US hours and IS supported by TradingView Paper Trading.

**Timeframe:** 1H
**Direction:** LONG only
**Trading venue:** TradingView Paper Trading
**Market hours:** 15:30–22:00 Oslo time (9:30 AM – 4:00 PM ET)

## Edge Discovery

K-Means cluster C2 on v2 feature set (OHLCV + RSI + EMAs + ATR + volume + hour + weekday).
Binomial p-value = **6.6e-6** (passes Bonferroni).
**Multi-split validation: 5/5 splits passed.**

## Entry Rule (all must be true at 1H bar close)

- `RSI(14) between 33 and 61`
- `Price -1.64% to +1.17% vs EMA20` (near the EMA)
- `Price vs EMA50 in normal range`
- `Range/ATR(14) normal (0.4 to 1.5)`
- `Hour during US session (15:30-22:00 Oslo)`

## Exit Rule

- **Time-based:** close position 5 bars (5 hours) after entry
- If held into US close, close at market close instead
- Trade cost: 0.05% round-trip (ADR spread + commissions on paper)

## Validation

| Test | Result |
|------|--------|
| In-sample (n=231) | 60% WR, Bonferroni p=6.6e-6 ✓ |
| Multi-split (5 tests) | 5/5 passed ✓ |
| Full-period simulation | 249 trades, 60% WR, **+$5,920** on $10K/trade over 2y |
| Monthly avg | **+$253/month** |

## Risk Controls

- $10 max risk per trade
- Position size: $10K default
- Skip if BCS earnings within 2 trading days (earnings gap risk)

## Deployment Checklist

1. TradingView chart: **NYSE:BCS**, 1H timeframe
2. Indicators: RSI(14), EMA(20), EMA(50), ATR(14)
3. Scan every hour during US market hours
4. Place market BUY when all conditions met
5. Set 5-bar exit timer, or force-close at 21:55 Oslo (before US close)

## Correlated Strategies

BCS, HSBC, DNBBY — all UK/EU bank ADRs. They move together during financial sector stress. Cap total exposure across these three at **$30K** to avoid doubling down on one sector.
