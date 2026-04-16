# Paper Trading Orders — Technical Reference for Claude

How to place and cancel orders on TradingView paper trading via CDP/JavaScript evaluation.

---

## Prerequisites

- TradingView Desktop running with CDP on port 9222
- Paper Trading account connected (bottom panel shows "Paper Trading")
- Chart must be on the correct symbol BEFORE opening the order ticket

---

## Placing an Order

### Step 1: Switch chart to the target symbol

Use `chart_set_symbol` to ensure the chart is on the correct asset.

```
chart_set_symbol → symbol: "COINBASE:BTCUSD"
```

### Step 2: Open the order ticket

Click the Buy or Sell button on the chart.

```javascript
// For a BUY order:
ui_click → by: "data-name", value: "buy-order-button"

// For a SELL order:
ui_click → by: "data-name", value: "sell-order-button"
```

This opens the order ticket panel on the right side of the screen.

### Step 3: Select order type (Market / Limit / Stop)

The order ticket opens on Market by default. To switch:

```javascript
ui_evaluate → expression:
(() => {
  const ticket = document.querySelector('[data-name="order-panel"]');
  if (!ticket) return "no ticket";
  const buttons = ticket.querySelectorAll('button');
  for (const b of buttons) {
    if (b.textContent.trim() === 'Limit') {  // or 'Market' or 'Stop'
      b.click();
      return "clicked Limit";
    }
  }
  return "button not found";
})()
```

### Step 4: Set the price (for Limit/Stop orders)

The price field has the ID `absolute-limit-price-field`.

```javascript
ui_evaluate → expression:
(() => {
  const priceInput = document.getElementById('absolute-limit-price-field');
  if (!priceInput) return "price input not found";
  priceInput.focus();
  priceInput.select();
  document.execCommand('insertText', false, '60000');  // ← your price here
  priceInput.dispatchEvent(new Event('input', { bubbles: true }));
  priceInput.dispatchEvent(new Event('change', { bubbles: true }));
  return "price set to: " + priceInput.value;
})()
```

### Step 5: Set quantity

The quantity field has the ID `quantity-field`.

```javascript
ui_evaluate → expression:
(() => {
  const qtyInput = document.getElementById('quantity-field');
  if (!qtyInput) return "qty input not found";
  qtyInput.focus();
  qtyInput.select();
  document.execCommand('insertText', false, '1');  // ← your quantity here
  qtyInput.dispatchEvent(new Event('input', { bubbles: true }));
  qtyInput.dispatchEvent(new Event('change', { bubbles: true }));
  return "qty set to: " + qtyInput.value;
})()
```

### Step 6: Set Take Profit and Stop Loss — MANDATORY, NEVER SKIP

**CRITICAL: Every order MUST have TP and SL set. An order without SL is a risk of losing the entire position. NEVER submit an order without completing this step.**

TP and SL are in the "Exits" section. They have checkboxes that must be ENABLED first, then values set. Inputs are: index 2 = TP checkbox, index 3 = TP value, index 4 = SL checkbox, index 5 = SL value.

```javascript
ui_evaluate → expression:
(() => {
  const panel = document.querySelector('[data-name="order-panel"]');
  if (!panel) return "ABORT: no panel";
  const inputs = panel.querySelectorAll('input');
  
  // Enable TP checkbox (index 2) if not checked
  if (!inputs[2].checked) inputs[2].click();
  
  // Set TP value (index 3)
  inputs[3].focus();
  inputs[3].select();
  document.execCommand('insertText', false, 'TP_PRICE_HERE');
  inputs[3].dispatchEvent(new Event('input', { bubbles: true }));
  
  // Enable SL checkbox (index 4) if not checked
  if (!inputs[4].checked) inputs[4].click();
  
  // Set SL value (index 5)
  inputs[5].focus();
  inputs[5].select();
  document.execCommand('insertText', false, 'SL_PRICE_HERE');
  inputs[5].dispatchEvent(new Event('input', { bubbles: true }));
  
  // VERIFY before returning
  return JSON.stringify({
    tp_enabled: inputs[2].checked,
    tp_value: inputs[3].value,
    sl_enabled: inputs[4].checked,
    sl_value: inputs[5].value
  });
})()
```

**After running this, VERIFY the output shows both `tp_enabled: true` and `sl_enabled: true` with correct values. If not, DO NOT submit the order.**

### Step 7: Verify the submit button text

Before submitting, always read the submit button to confirm the order details are correct.

```javascript
ui_evaluate → expression:
(() => {
  const panel = document.querySelector('[data-name="order-panel"]');
  if (!panel) return "no panel";
  const buttons = panel.querySelectorAll('button');
  let submitText = '';
  buttons.forEach(b => {
    const t = b.textContent.trim();
    if (t.includes('Buy') || t.includes('Sell')) {
      if (t.includes('LIMIT') || t.includes('MARKET') || t.includes('STOP')) {
        submitText = t;
      }
    }
  });
  return submitText;
})()
```

Expected format: `"Buy  1 BTCUSD @ 60,000.00 LIMIT"`

### Step 8: Submit the order

```javascript
ui_evaluate → expression:
(() => {
  const panel = document.querySelector('[data-name="order-panel"]');
  if (!panel) return "no panel";
  const buttons = panel.querySelectorAll('button');
  for (const b of buttons) {
    const t = b.textContent.trim();
    if ((t.includes('Buy') || t.includes('Sell')) && (t.includes('LIMIT') || t.includes('MARKET') || t.includes('STOP'))) {
      b.click();
      return "ORDER SUBMITTED: " + t;
    }
  }
  return "submit button not found";
})()
```

### Step 9: Verify the order appeared

Click the Orders tab and check the order count increased.

```javascript
ui_evaluate → expression:
(() => {
  // Click Orders tab
  const allBtns = document.querySelectorAll('button');
  for (const b of allBtns) {
    if (b.textContent.trim().startsWith('Orders')) {
      b.click();
      return "clicked: " + b.textContent.trim();
    }
  }
  return "Orders tab not found";
})()
```

Then verify the order row exists:

```javascript
ui_evaluate → expression:
(() => {
  const rows = document.querySelectorAll('tr');
  for (const row of rows) {
    const text = row.textContent || '';
    if (text.includes('BTCUSD') && text.includes('60,000')) {
      return JSON.stringify({ found: true, text: text.substring(0, 120) });
    }
  }
  return JSON.stringify({ found: false });
})()
```

---

## Cancelling an Order

### Step 1: Open the Orders tab

```javascript
ui_evaluate → expression:
(() => {
  const allBtns = document.querySelectorAll('button');
  for (const b of allBtns) {
    if (b.textContent.trim().startsWith('Orders')) {
      b.click();
      return "clicked Orders tab";
    }
  }
  return "not found";
})()
```

### Step 2: Find the order row and click Cancel

Each order row has two buttons: "Modify Order…" and "Cancel" (accessible via aria-label).

```javascript
ui_evaluate → expression:
(() => {
  const rows = document.querySelectorAll('tr');
  for (const row of rows) {
    const text = row.textContent || '';
    if (text.includes('BTCUSD') && text.includes('60,000')) {  // ← match your order
      const cancelBtn = row.querySelector('button[aria-label="Cancel"]');
      if (cancelBtn) {
        cancelBtn.click();
        return "clicked cancel on order";
      }
      return "cancel button not found in row";
    }
  }
  return "order row not found";
})()
```

### Step 3: Confirm the cancellation dialog

A confirmation dialog appears with "Keep order" and "Cancel order" buttons. Click "Cancel order".

```javascript
ui_evaluate → expression:
(() => {
  const buttons = document.querySelectorAll('button');
  for (const b of buttons) {
    if (b.textContent.trim() === 'Cancel order') {
      b.click();
      return "Confirmed cancellation";
    }
  }
  return "Cancel order button not found";
})()
```

---

## Reading All Current Orders

To read all open positions and pending orders:

```javascript
ui_evaluate → expression:
(() => {
  const tables = document.querySelectorAll('.bottom-widgetbar-content table');
  const results = [];
  tables.forEach(t => {
    const text = t.innerText;
    if (text.includes('Symbol') && text.includes('Side')) {
      results.push(text);
    }
  });
  return JSON.stringify(results);
})()
```

This returns:
- **Table 1**: Open positions (symbol, side, qty, avg fill, TP, SL, last price, P&L)
- **Table 2**: Pending/working orders (symbol, side, type, qty, limit price, stop price, status)

---

## MANDATORY Post-Order Verification — NEVER SKIP

After EVERY order submission, run this verification. If any order is missing TP or SL, ALERT Maria immediately and fix it.

```javascript
ui_evaluate → expression:
(() => {
  // Read all working orders and check for missing TP/SL
  const rows = document.querySelectorAll('tr');
  const issues = [];
  const orders = [];
  
  rows.forEach(row => {
    const text = row.textContent || '';
    if (text.includes('Limit') && text.includes('working')) {
      const cells = row.querySelectorAll('td');
      if (cells.length > 4) {
        const symbol = cells[0].textContent.trim();
        const price = cells[4].textContent.trim();
        
        // Check if this limit order has corresponding SL and TP orders
        let hasSL = false;
        let hasTP = false;
        rows.forEach(r2 => {
          const t2 = r2.textContent || '';
          if (t2.includes(symbol.split(':')[1] || symbol)) {
            if (t2.includes('Stop Loss') && t2.includes('working')) hasSL = true;
            if (t2.includes('Take Profit') && t2.includes('working')) hasTP = true;
          }
        });
        
        orders.push({ symbol, price, hasSL, hasTP });
        if (!hasSL) issues.push("MISSING SL: " + symbol + " @ " + price);
        if (!hasTP) issues.push("MISSING TP: " + symbol + " @ " + price);
      }
    }
  });
  
  return JSON.stringify({ orders, issues, allClear: issues.length === 0 });
})()
```

**If `allClear` is false:**
1. STOP all other work
2. ALERT Maria: "ORDER SAFETY CHECK FAILED — [issues]"
3. Fix the missing TP/SL immediately before doing anything else

**Rules:**
- NEVER place an order without TP and SL
- NEVER skip this verification after placing an order
- If TP/SL checkboxes fail to enable, cancel the order and retry
- This check must run after EVERY order placement, including auto-executed trades

---

## Key DOM Selectors Reference

| Element | Selector |
|---------|----------|
| Order panel | `[data-name="order-panel"]` |
| Buy button (chart) | `[data-name="buy-order-button"]` |
| Sell button (chart) | `[data-name="sell-order-button"]` |
| Price input (limit) | `#absolute-limit-price-field` |
| Quantity input | `#quantity-field` |
| Cancel button (per row) | `button[aria-label="Cancel"]` |
| Modify button (per row) | `button[aria-label="Modify Order…"]` |
| Cancel confirm button | Button with text "Cancel order" |
| Pine Editor button | `[data-name="pine-dialog-button"]` |

---

## Known Issues

1. **Pine Editor must be clicked into** — `ui_open_panel("pine-editor", "open")` opens the bottom bar but the Monaco editor doesn't load until you click `pine-dialog-button`.

2. **DOM re-renders after price change** — After setting the limit price, TradingView re-renders the order ticket. TP/SL input elements may disappear from the DOM. Re-query them after setting the price.

3. **Quote data bleeds across panes** — In multi-pane layouts, `quote_get` may return data from the active pane, not the requested symbol. Use `pane_focus` first, or switch to single chart mode.

4. **US stocks return stale data on weekends** — PLTR/TSM quotes on Sunday return Gold data because markets are closed and TradingView falls back to the active feed.

5. **CRITICAL: Selling shares does NOT close a long — it creates a NEW SHORT.** On paper trading, placing a sell order when you have a long position opens a separate short position instead of closing the long. ONLY use the "Close" button (X) on the position row to close. If that fails, ask Maria to close via GUI. NEVER place a sell market/limit order to close a long. Same applies in reverse: buying does not close a short.

6. **Pre-market orders are ALL rejected** — Paper trading rejects both market AND limit orders placed before market hours (before 15:30 Oslo for US stocks). The only solution is the sniper cron at 15:30:00 exact that places market orders the instant the bell rings.
