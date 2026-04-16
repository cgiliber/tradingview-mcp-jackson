# Mistakes Audit — All Issues and Fix Status

## FIXED

| # | Mistake | When | Fix | Where | Verified |
|---|---------|------|-----|-------|----------|
| 1 | Fixed watchlist missed biggest movers | Apr 15 | Finviz scanner (free, entire market) | scanner/trader-scan.js | Yes — found BIRD +700%, MNTS +43% |
| 2 | $25 max loss (AVGO -$27.80) | Apr 15 | $10 max loss | strategies/goal-based-rules.json line 11 | Yes |
| 3 | Only scanning gainers | Apr 15 | Added losers (SHORT candidates) | scanner/trader-scan.js fetchFinvizMovers('losers') | Yes |
| 4 | Not checking charts before decisions | Apr 15 | TRADER_WORKFLOW.md Step 2 — mandatory chart check | TRADER_WORKFLOW.md | Yes |
| 5 | Being too scared to trade (ASTI missed) | Apr 15 | "Default is TRADE" rule, not valid skip reasons list | TRADER_WORKFLOW.md, feedback_be_aggressive.md | Yes |
| 6 | Twelve Data credits/rate limits | Apr 15 | Replaced with Finviz + CoinGecko (all free) | scanner/trader-scan.js, config.json | Yes |
| 7 | No overnight crypto scanning | Apr 15 | CoinGecko scanner + cron every 30 min | Cron 6d84bf37 | Yes |
| 8 | Didn't verify ORDI TP/SL hit | Apr 16 | TRADER_WORKFLOW.md Step 4 — mandatory verification | TRADER_WORKFLOW.md Step 4a-4d | Yes |
| 9 | STLA close failed silently | Apr 16 | TRADER_WORKFLOW.md Step 4b — verify position gone after close | TRADER_WORKFLOW.md Step 4b | Yes |
| 10 | Tried closing stock outside market hours | Apr 16 | Market hours check added — Step 5 | TRADER_WORKFLOW.md Step 5 | Yes |
| 11 | Close at 22:00 too late (order may not execute) | Apr 16 | Changed to 21:55 Oslo (5 min before close) | TRADER_WORKFLOW.md Step 6 | Yes |
| 12 | Asking permission constantly | Apr 16 | Full autonomy granted | feedback_full_autonomy.md | Yes |
| 13 | Gold obsession (80+ credits on one asset) | Apr 15 | Finviz movers-first replaces fixed list monitoring | feedback_gold_obsession.md | Yes |
| 14 | Hardcoded strategy in scan loop | Apr 15 | trader-scan.js dynamic movers | feedback_strategy_rotation.md | Yes |
| 15 | No strategy comparison | Apr 16 | A/B test framework (v8.0 vs v8.1) | AB_TEST.md, journal-v80.json, journal-v81.json | Yes |
| 16 | Old zombie orders left open | Apr 16 | All cancelled (TSM, ETH, Gold, AMD, META) | Verified on TradingView | Yes |

## ALL 16 MISTAKES FIXED
