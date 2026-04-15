# Remote Commands — Trigger from Claude App

Create these as Routines at https://claude.ai/code/routines
Each one can be triggered from the Claude app on your phone.

## 1. SCAN — Run auto scanner immediately

**Name:** scan
**Prompt:**
```
Run node scanner/index.js auto immediately. Evaluate results. If any asset qualifies per goal-based-rules.json ($25 max loss, 1:2 R:R), auto-execute the trade. Report results briefly.
```

## 2. STATUS — Check positions and P&L

**Name:** status
**Prompt:**
```
Check current status: 1) Run date for Oslo time, 2) Get all open positions from TradingView broker panel, 3) Get current quotes for each position, 4) Calculate P&L for each, 5) Check if any profit-lock tiers triggered, 6) Show credit usage from scanner/credit-log.json. Brief table output.
```

## 3. CLOSE-ALL — Emergency close everything

**Name:** close-all
**Prompt:**
```
URGENT: Close ALL open positions on TradingView paper trading immediately. Use TradingView MCP tools to find and close every position. Log closures to journal.json. Report what was closed and final P&L.
```

## 4. CLOSE — Close a specific position

**Name:** close
**Prompt:**
```
Close the position specified in the trigger input on TradingView paper trading. Get the current price first, calculate final P&L, close the position, verify it is closed, log to journal.json. Report what was closed and the P&L.
```
**Usage from app:** Fire with text like "UUUU" or "Gold"

## 5. TRADE — Place a trade

**Name:** trade
**Prompt:**
```
Place a paper trade on TradingView. Use the trigger input to determine: symbol, direction (buy/sell), entry price. Apply v7.0 rules: calculate units = FLOOR($25 / stop_distance), set ATR-based SL, set TP at minimum 1:2 R:R. Enable TP and SL checkboxes. Verify after placement. Log to journal.json.
```
**Usage from app:** Fire with text like "buy UUUU at 21.00" or "sell Gold at 4810"

## 6. LOCK-PROFIT — Apply profit-lock tiers

**Name:** lock-profit
**Prompt:**
```
Run profit-lock check on ALL open positions: 1) Get current prices via TradingView quote_get, 2) Calculate P&L for each, 3) Check against profit-lock-rules.json tiers (+$25 breakeven, +$50 sell half, +$75 lock $50, +$100 close all), 4) If triggered, modify SL immediately, 5) Verify SL saved, 6) Log to journal.json.
```

## How to set up

1. Go to https://claude.ai/code/routines
2. Create each routine with the name and prompt above
3. Add an "API trigger" to each one
4. From the Claude app, you can fire any routine by name
5. Each routine runs in this project directory with full TradingView MCP access
