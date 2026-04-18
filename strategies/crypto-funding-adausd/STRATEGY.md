# ADAUSD Funding Squeeze v1.0

**Asset:** ADAUSD (Cardano) — Binance perpetual and spot
**Timeframe:** 1H
**Direction:** LONG only
**Trading venue:** Binance (via TradingView Paper Trading)
**Market hours:** 24/7

## Edge Discovery

K-Means cluster C9 on v5 feature set (adds Binance perpetual funding rate).
Binomial p-value = **5.5e-5** (passes Bonferroni).

**This is the only strategy that USES funding rate data.**

## Entry Rule (all must be true at 1H bar close)

- `RSI(14) between 31 and 57` (neutral-to-oversold)
- `Price -1.87% to +1.09% vs EMA20` (near EMA, not extended)
- `Price vs EMA50 within normal range`
- `Binance funding rate ≤ -0.01%` per 8h (shorts crowded, paying longs)
- `Funding change over last day ≤ -0.01%` (shorts getting MORE crowded)

**Economic rationale:** When funding rate is deeply negative AND falling, perpetual shorts are aggressively positioned. This creates a short squeeze setup — any price uptick forces cascading short covers → upward move.

## Exit Rule

- **Time-based:** close position exactly 5 bars (5 hours) after entry
- No traditional stop loss
- Trade cost assumed: 0.15% round-trip

## Data Requirements

- Free Binance futures API: `https://fapi.binance.com/fapi/v1/fundingRate?symbol=ADAUSDT`
- Historical data: download via `scripts/download_funding_rates.py`
- Real-time: query once per hour at bar close

## Validation

| Test | Result |
|------|--------|
| In-sample (n=903) | 55.6% WR, Bonferroni p=5.5e-5 ✓ |
| Out-of-sample 70/30 | 36 trades, 55.6% WR, **+7.7% return** ✓ |

This was the strongest OOS performance of all strategies.

## Risk Controls

- $10 max risk per trade
- Position size: $10K default
- Skip trade if ADAUSD 24h volume drops >50% from 7d avg (liquidity risk)

## Deployment Checklist

1. Chart: BINANCE:ADAUSDT, 1H
2. Ensure funding rate lookup endpoint is accessible
3. Check signal at each 1H bar close
4. Place market BUY, set 5-bar exit timer
