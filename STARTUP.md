# Startup — Run at the beginning of every Claude session

Say this to Claude at the start of every session:

```
Start auto-trading. Read PROJECT_CONTEXT.md, then set up all 4 trading crons:

1. NY POWER HOUR: /loop 5m (15:00-16:59 Mon-Fri) — node scanner/trader-scan.js --top 10, analyze charts, trade aggressively, $10 risk, $20 target
2. REGULAR SESSION: /loop 15m (17:00-21:59 Mon-Fri) — same workflow, close all stocks by 22:00
3. CRYPTO EVENING: /loop 15m (20:00-23:59 daily) — node scanner/trader-scan.js --crypto --top 10, same rules
4. OVERNIGHT CRYPTO: /loop 30m (00:00-06:59 daily) — crypto scan, same rules

Follow TRADER_WORKFLOW.md for every scan. Be aggressive. Default is TRADE.
```

Or shorter: **"Start auto-trading per STARTUP.md"**
