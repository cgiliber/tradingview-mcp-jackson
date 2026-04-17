# Order Placement Procedure v1.0
# This documents EXACTLY how orders are placed via TradingView Paper Trading
# Every step is traceable. If something fails, check which step broke.

## INPUTS (from v8.5 indicator):
- symbol: e.g. "ETHUSDT"
- side: "BUY" or "SELL" (from BUY_SIGNAL or SELL_SIGNAL)
- entry: indicator ENTRY price (for reference, we use market order)
- tp_price: indicator TP price
- sl_price: indicator STOP price
- trend: indicator TREND (1=UP, -1=DOWN)

## PRE-FLIGHT CHECKS:
1. Verify side matches trend: BUY only if TREND=1, SELL only if TREND=-1
2. Verify TP direction: BUY → TP > current price. SELL → TP < current price
3. Verify SL direction: BUY → SL < current price. SELL → SL > current price
4. Verify SL distance: |entry - sl_price| must be > $0.05 (skip if too tight)
5. Verify R:R ratio: |tp - entry| / |entry - sl| must be >= 2.5
6. Check if we already have a position in this symbol (skip if yes)

## EXECUTION STEPS:

### Step 1: Click order button
- BUY: click data-name="buy-order-button"
- SELL: click data-name="sell-order-button"
- VERIFY: button text should show current price + "Buy"/"Sell"

### Step 2: Enable TP toggle
- Click at coordinates (868, 377) — the TP toggle switch
- VERIFY: toggle should turn blue

### Step 3: Enable SL toggle
- Click at coordinates (868, 461) — the SL toggle switch
- VERIFY: toggle should turn blue

### Step 4: Set TP price
- Double-click TP input field at (680, 414)
- Cmd+A to select all
- Type the exact tp_price value
- Press Tab to confirm
- VERIFY: field shows correct value

### Step 5: Set SL price
- Double-click SL input field at (680, 498)
- Cmd+A to select all
- Type the exact sl_price value
- Press Tab to confirm
- VERIFY: field shows correct value

### Step 6: Place order
- Click data-name="place-and-modify-button"
- VERIFY: confirmation notifications appear (market order placed, TP order placed, SL order placed)

### Step 7: Close dialog
- Click aria-label="Close button"

### Step 8: Verify position
- Check positions count increased by 1
- Check TP and SL values match what we set

## POST-TRADE LOG:
Record to overnight-scan-log.json:
- timestamp
- symbol
- side
- fill_price
- tp_price
- sl_price
- signal_source (which timeframe, which indicator)

## KNOWN ISSUES:
- TP/SL toggles may already be ON from previous order — clicking again turns them OFF
- Coordinate-based clicks (868,377) may shift if window resizes
- Paper Trading only works on Binance crypto and US stocks during market hours
- Pre-market stock orders show confirmation but don't execute
