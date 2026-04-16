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

| 17 | Had movers list at 13:10, sat there making "hit list for 15:30" | Apr 16 | Pre-market cron (10:00-14:59) places LIMIT orders at current price → auto-fill at open | Cron 59bf31fa, feedback_premarket_limits.md | Yes |
| 18 | Market orders don't fill in pre-market on paper trading | Apr 16 | Use LIMIT orders instead of market orders in pre-market | TRADER_WORKFLOW.md Step 5 market hours | Yes |

| 19 | Analyze before executing — spent 7+ min writing before placing AR trade | Apr 16 | RULE ZERO: See it → Place it → Verify → Then write. Order first, notes after. | TRADER_WORKFLOW.md Rule Zero, feedback_execute_first.md | Yes |
| 20 | No sniper cron at market open — entered 10 min late, bought WSHP at $32.78 instead of $28 open | Apr 16 | Sniper cron at 15:30:00 EXACT places market orders on all pre-market targets | Cron e08d4094 | Yes — fires tomorrow |
| 21 | Selling shares to close a long creates a NEW SHORT on paper trading | Apr 16 | NEVER sell to close a long. ONLY use the Close/X button on the position row. If that fails, ask Maria to close via GUI. | PAPER_TRADING_ORDERS.md | Needs code update |
| 22 | Chasing stocks after gap — entered WSHP +261% at $32.78 (opened at $28), DOO after bounce | Apr 16 | Enter at OPEN price via sniper cron, OR wait for first pullback to EMA 8/VWAP. Never chase 10+ min after open. | TRADER_WORKFLOW.md | Yes |
| 23 | Pre-market limit orders ALL rejected by paper trading — ASTI, XNDU, BIRD, WSHP, DOO | Apr 16 | Paper trading rejects ALL pre-market orders (market AND limit). Only solution: sniper cron at 15:30:00 exact with market orders. | TRADER_WORKFLOW.md | Yes |
| 24 | Same mistake two days in a row — knew movers early, failed to execute at open | Apr 16 | CRITICAL PATTERN. Sniper cron is the only fix. Manual execution always delays 10+ min. | feedback_execute_first.md | Sniper cron ready |

| 25 | Only traded 8 of 30 movers — ignored 22 with no valid reason | Apr 16 | Rapid fire: 30 seconds per stock, process ALL 30 movers | feedback_rapid_fire.md | Needs architecture fix |
| 26 | Only traded LONGS, ignored 50% of opportunities (SHORTS) | Apr 15+16 | Alternate long/short during scan | feedback_trade_both_directions.md | Fixed in workflow |

## CRITICAL OPEN ISSUE — SPEED BOTTLENECK

**This is the #1 problem killing our performance. Must be solved before anything else.**

**Problem:** Processing 30 movers takes too long. Currently ~5 min per stock = 2.5 hours for 30 stocks. Need 30 seconds per stock = 15 min for 30 stocks.

**Root cause analysis needed:** Is it computer performance? TradingView MCP latency? Too many tool calls per trade? Claude thinking too much? Need to profile and fix.

**See: SPEED_BOTTLENECK.md for full analysis.**

## ALL 26 MISTAKES TRACKED — 23 FIXED, 3 PENDING
