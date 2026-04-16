# A/B Strategy Test — v8.0 vs v8.1

## How It Works

Every scan analyzes each mover through BOTH strategies. If either qualifies → place the trade tagged to that strategy. Both can trade the same stock if both have valid setups.

## Strategy A: v8.0 Baseline
- **Entry:** EMA 8 position, staircase, BB breakout
- **Stop:** Below last candle low or EMA 8
- **Journal:** journal-v80.json
- **Rules:** strategies/v8.0-baseline/rules.json

## Strategy B: v8.1 Rayner
- **Entry:** Buildup at resistance, retest, ascending triangle, 20 EMA proximity
- **Stop:** 1 ATR below pattern swing low
- **Journal:** journal-v81.json
- **Rules:** strategies/v8.1-rayner/rules.json

## Both Share
- $10 max risk per trade
- $20 target (1:2 R:R)
- Breakeven at +$10
- Close at +$20
- Max 5 positions per strategy (10 total)
- Finviz + CoinGecko scanner
- Mandatory verification after every action

## Per-Scan Workflow

For each top 10 mover:
1. Open chart, read indicators
2. **v8.0 check:** EMA 8 above? Staircase? BB breakout? → TRADE or SKIP
3. **v8.1 check:** Buildup? Retest? Near EMA 21? Higher lows? → TRADE or SKIP
4. If TRADE: tag which strategy, log to correct journal
5. Both strategies can enter the same stock with different sizing/stops

## Scoring After 20 Days

| Metric | v8.0 | v8.1 |
|--------|------|------|
| Total trades | | |
| Win rate | | |
| Avg profit per win | | |
| Avg loss per loss | | |
| Total P&L | | |
| Best trade | | |
| Worst trade | | |
| Max drawdown | | |

## Strategy C: v8.2 Cowen (CRYPTO ONLY)
- **Framework:** Benjamin Cowen — market cycles, 21-week EMA bull/bear divider, BTC dominance
- **Entry:** Only trade crypto when BTC is above 21w EMA (bull). Below = counter-trend, smaller size.
- **BTC dominance rising:** Only trade BTC, skip altcoins
- **RSI divergence:** Don't enter if price higher highs but RSI lower highs
- **Journal:** journal-v82.json
- **Rules:** strategies/v8.2-cowen/rules.json

**Current Cowen assessment (Apr 16):**
- BTC at $74,713 — BELOW 21w EMA ($78,506) = **BEAR MARKET**
- BTC dominance 59.76% — **RISING** = altcoins underperform
- v8.2 says: reduce crypto exposure, only BTC if anything, tighter stops

## Strategy D: v8.3 Wysetrade (FOREX focused)
- **Framework:** Wysetrade — liquidity sweeps, smart money concepts, trend lines, MA strategy
- **Entry:** Liquidity grabs above/below key levels, trend line bounces, MA crossovers
- **Best time:** London-NY overlap (15:30-17:30 Oslo) — highest forex liquidity
- **Pairs:** EUR/USD, GBP/USD, USD/JPY, GBP/JPY, EUR/GBP
- **Journal:** journal-v83.json
- **Rules:** strategies/v8.3-wysetrade/rules.json
- **Note:** 10% portfolio limit suspended during paper trading — trade freely to test

## Strategy E: v8.4 Range Breakout
- **Framework:** 15-min opening range breakout. Wait for first candle, mark range, enter on 5-min breakout + pullback.
- **Key difference:** Does NOT enter at market open. Waits 15 min. Avoids spike-and-crash.
- **Crons:** 15:45 mark ranges, 15:50-16:15 check breakouts every 5 min
- **Journal:** journal-v84.json
- **Rules:** strategies/v8.4-range-breakout/rules.json

## Strategy F: v8.5 TradingLab — Supply & Demand (PRIORITY: HIGH)
- **Framework:** 3-step: valid market structure + supply/demand zones + R:R > 2.5:1
- **No indicators.** Pure price action. Valid highs/lows only.
- **Demand zone:** consolidation before sharp up move, enter on retest
- **Supply zone:** consolidation before sharp down move, enter on retest
- **Key rule:** A low is ONLY valid if it broke the previous high
- **Journal:** journal-v85.json

## Scoring After 20 Days

| Metric | v8.0 | v8.1 | v8.2 | v8.3 | v8.4 | v8.5 |
|--------|------|------|------|
| Total trades | | | | | | |
| Win rate | | | | | | |
| Avg profit per win | | | | | | |
| Avg loss per loss | | | | | | |
| Total P&L | | | | | | |
| Best trade | | | | | | |
| Worst trade | | | | | | |
| Max drawdown | | | | | | |

Winner becomes the permanent strategy.
