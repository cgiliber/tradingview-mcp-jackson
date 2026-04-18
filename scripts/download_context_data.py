#!/usr/bin/env python3
"""
Download context/macro data needed for stock and crypto feature engineering.
All free sources.

Stocks: VIX, SPY, QQQ, XLK, XLE, XLF, XLY, XLV
Crypto: Binance funding rates for BTC/ETH/SOL perpetuals
"""
import os
import urllib.request
import json
import yfinance as yf
import warnings
warnings.filterwarnings('ignore')

OHLCV_DIR = '/Users/mariashchekanenko/claude-trading-tv/data/ohlcv'
FUNDING_DIR = '/Users/mariashchekanenko/claude-trading-tv/data/funding'
os.makedirs(FUNDING_DIR, exist_ok=True)

# yfinance symbols for market context
CONTEXT_SYMBOLS = {
    '^VIX': 'VIX',        # volatility index
    'XLK': 'XLK',         # Tech
    'XLE': 'XLE',         # Energy
    'XLF': 'XLF',         # Financials
    'XLV': 'XLV',         # Healthcare
    'XLY': 'XLY',         # Consumer discretionary
    'XLC': 'XLC',         # Communication services
}

def download_yahoo(ysym, name):
    out = os.path.join(OHLCV_DIR, f'{name}.csv')
    if os.path.exists(out):
        return 'exists'
    try:
        d = yf.download(ysym, period='2y', interval='1h',
                        progress=False, auto_adjust=False)
        if d is None or len(d) == 0:
            return 'empty'
        if hasattr(d.columns, 'nlevels') and d.columns.nlevels > 1:
            d.columns = d.columns.get_level_values(0)
        with open(out, 'w') as f:
            f.write('timestamp,open,high,low,close,volume\n')
            for idx, row in d.iterrows():
                ts = int(idx.timestamp())
                o = float(row['Open']) if row['Open'] == row['Open'] else 0
                h = float(row['High']) if row['High'] == row['High'] else 0
                l = float(row['Low']) if row['Low'] == row['Low'] else 0
                c = float(row['Close']) if row['Close'] == row['Close'] else 0
                v = int(float(row['Volume'])) if row['Volume'] == row['Volume'] else 0
                if o > 0 and c > 0:
                    f.write(f'{ts},{o},{h},{l},{c},{v}\n')
        return f'{len(d)} bars'
    except Exception as e:
        return f'error: {str(e)[:40]}'

def download_binance_funding(symbol):
    """Binance funding rate history for a perpetual symbol (e.g. BTCUSDT)."""
    # Binance returns max 1000 records per call (8-hour intervals → ~333 days)
    # Need pagination for 2 years of data
    out = os.path.join(FUNDING_DIR, f'{symbol}.csv')
    all_records = []
    # Binance funding interval is 8 hours → 3 per day → 2190 for 2 years
    # Fetch in chunks of 1000, going backwards
    end_time = None
    for _ in range(5):  # 5 pages × 1000 = 5000 records max (more than enough)
        url = f'https://fapi.binance.com/fapi/v1/fundingRate?symbol={symbol}&limit=1000'
        if end_time:
            url += f'&endTime={end_time}'
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            resp = urllib.request.urlopen(req, timeout=15)
            data = json.loads(resp.read().decode())
            if not data:
                break
            all_records = data + all_records
            # Oldest timestamp in this batch - 1 for next query
            oldest_ts = data[0]['fundingTime']
            if end_time and oldest_ts >= end_time:
                break
            end_time = oldest_ts - 1
            if len(data) < 1000:
                break
        except Exception as e:
            return f'error: {str(e)[:40]}'

    # Dedupe by fundingTime
    seen = set()
    unique = []
    for r in all_records:
        if r['fundingTime'] not in seen:
            seen.add(r['fundingTime'])
            unique.append(r)
    unique.sort(key=lambda r: r['fundingTime'])

    with open(out, 'w') as f:
        f.write('funding_time,funding_rate,mark_price\n')
        for r in unique:
            f.write(f'{r["fundingTime"]},{r["fundingRate"]},{r.get("markPrice", 0)}\n')
    return f'{len(unique)} funding records'

def main():
    print('─── Market context (Yahoo) ───')
    for ysym, name in CONTEXT_SYMBOLS.items():
        status = download_yahoo(ysym, name)
        print(f'  {name:6} {ysym:6} {status}')

    print('\n─── Binance funding rates ───')
    for sym in ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'XRPUSDT', 'ADAUSDT']:
        status = download_binance_funding(sym)
        print(f'  {sym:10} {status}')

if __name__ == '__main__':
    main()
