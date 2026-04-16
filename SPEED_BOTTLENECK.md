# SPEED BOTTLENECK — #1 Problem to Solve

## The Problem

Processing 30 movers should take 15 minutes. Currently takes 2+ hours. We miss 70% of opportunities.

## Where the Time Goes (per stock)

| Step | Current Time | Target Time | Bottleneck? |
|------|-------------|-------------|:-----------:|
| 1. chart_set_symbol | ~2 sec | 2 sec | No |
| 2. quote_get | ~1 sec | 1 sec | No |
| 3. data_get_study_values | ~1 sec | 1 sec | No |
| 4. **Claude writes analysis paragraph** | **30-60 sec** | **0 sec** | **YES — #1** |
| 5. **Claude evaluates 4 strategies in text** | **30-60 sec** | **5 sec** | **YES — #2** |
| 6. ui_click buy/sell button | ~1 sec | 1 sec | No |
| 7. ui_evaluate set qty/tp/sl | ~2 sec | 2 sec | No |
| 8. ui_evaluate submit | ~1 sec | 1 sec | No |
| 9. **Claude writes notes/tables after** | **30-60 sec** | **0 sec** | **YES — #3** |
| 10. Repeat for v8.1 (second trade) | ~10 sec | 5 sec | Minor |
| **TOTAL per stock** | **~3-5 min** | **~30 sec** | |

## Root Cause

**It's NOT the computer. It's NOT TradingView MCP.** The tool calls are fast (1-2 sec each).

**The bottleneck is Claude generating text between tool calls.** Every trade, I write:
- Analysis paragraph (30 sec)
- 4-strategy evaluation table (30 sec)  
- Position update table (30 sec)
- Notes about what happened (30 sec)

That's 2 minutes of WRITING per stock that adds zero value during execution. All of that should happen AFTER all 30 stocks are processed.

## Proposed Fix

### Option A: Batch mode script
Build a Node.js script that rapidly places orders on a list of symbols without Claude's text generation in between. Claude provides the list, script executes all 30.

### Option B: Minimal text mode
Claude processes all 30 with ZERO text output between trades. Just tool calls back to back. Write the full summary only after all 30 are done.

### Option C: Parallel execution
Use multiple TradingView tabs/panes to place orders on multiple stocks simultaneously.

## Action Items

- [ ] Profile actual time per step with timestamps
- [ ] Decide on Option A, B, or C
- [ ] Implement the fix
- [ ] Test: can we process 30 stocks in 15 minutes?

## Priority: HIGHEST — This blocks everything else.
