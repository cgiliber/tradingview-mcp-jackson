#!/usr/bin/env python3
"""
Download Binance perpetual funding rate history for crypto majors.
Full 2y history via pagination. FREE, no auth required.

Funding rate interpretation:
- Positive = longs pay shorts (bullish crowd = often contrarian signal)
- Negative = shorts pay longs (bearish crowd = often contrarian signal)
- Extreme values (>0.05% per 8h) mark sentiment extremes
"""
import urllib.request
import json
import os
import time

OUT_DIR = '/Users/mariashchekanenko/claude-trading-tv/data/funding'
os.makedirs(OUT_DIR, exist_ok=True)

SYMBOLS = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'XRPUSDT', 'ADAUSDT',
           'BNBUSDT', 'AVAXUSDT', 'LINKUSDT']

def fetch_funding(symbol, start_date='2024-01-01'):
    """Paginate forward from start_date to present."""
    start_ts = int(time.mktime(time.strptime(start_date, '%Y-%m-%d')) * 1000)
    end_ts = int(time.time() * 1000)

    all_records = []
    cursor = start_ts

    while cursor < end_ts:
        url = (f'https://fapi.binance.com/fapi/v1/fundingRate'
               f'?symbol={symbol}&startTime={cursor}&limit=1000')
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            data = json.loads(urllib.request.urlopen(req, timeout=20).read().decode())
            if not data:
                break
            all_records.extend(data)
            # Move cursor past the last record's time
            new_cursor = data[-1]['fundingTime'] + 1
            if new_cursor == cursor:
                break
            cursor = new_cursor
            if len(data) < 1000:
                break
            time.sleep(0.1)  # rate limit courtesy
        except Exception as e:
            print(f'  {symbol} error: {e}')
            break

    # Dedupe
    seen = set()
    unique = []
    for r in all_records:
        t = r['fundingTime']
        if t not in seen:
            seen.add(t)
            unique.append(r)
    unique.sort(key=lambda x: x['fundingTime'])
    return unique

def main():
    for sym in SYMBOLS:
        print(f'Fetching {sym}...')
        records = fetch_funding(sym)
        if not records:
            print(f'  EMPTY')
            continue

        out = os.path.join(OUT_DIR, f'{sym}.csv')
        with open(out, 'w') as f:
            f.write('funding_time,funding_rate,mark_price\n')
            for r in records:
                f.write(f'{r["fundingTime"]},{r["fundingRate"]},{r.get("markPrice","0")}\n')

        # Date range
        t0 = records[0]['fundingTime'] / 1000
        tN = records[-1]['fundingTime'] / 1000
        import datetime
        print(f'  {sym}: {len(records)} records | '
              f'{datetime.datetime.fromtimestamp(t0).strftime("%Y-%m-%d")} to '
              f'{datetime.datetime.fromtimestamp(tN).strftime("%Y-%m-%d")}')

if __name__ == '__main__':
    main()
