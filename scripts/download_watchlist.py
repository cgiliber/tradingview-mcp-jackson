#!/usr/bin/env python3
"""
Download 1y 1H OHLCV data for all assets in watchlist.json.
Uses yfinance (free). Saves to data/ohlcv/<symbol>.csv.
"""
import json
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
import yfinance as yf
import warnings
warnings.filterwarnings('ignore')

WATCHLIST = '/Users/mariashchekanenko/claude-trading-tv/watchlist.json'
OUT_DIR = '/Users/mariashchekanenko/claude-trading-tv/data/ohlcv'
os.makedirs(OUT_DIR, exist_ok=True)

# Yahoo symbol mapping — some tickers need suffixes
def yahoo_symbol(sym, asset_type):
    # Crypto: BTCUSD -> BTC-USD
    if asset_type in ('crypto', 'crypto-major', 'crypto-alt'):
        base = sym.replace('USD', '').replace('USDT', '')
        return f'{base}-USD'
    # Forex: EURUSD -> EURUSD=X
    if asset_type == 'forex':
        return f'{sym}=X'
    # EU stocks — UK uses .L, German uses .DE, etc.
    # For simplicity, try base symbol first
    return sym

def extract_symbols(watchlist):
    """Extract (symbol, name, type, asset_class) from watchlist."""
    symbols = []
    classes = {
        'london_session': 'forex',
        'ny_session': 'us_stocks',
        'crypto_session': 'crypto',
        'all_day': 'etf_macro',
        'eu_session': 'eu_stocks',
    }
    for session, cls in classes.items():
        if session not in watchlist:
            continue
        assets = watchlist[session].get('assets', [])
        for a in assets:
            sym = a.get('symbol', '')
            if not sym:
                continue
            symbols.append({
                'symbol': sym,
                'name': a.get('name', sym),
                'type': a.get('type', cls),
                'asset_class': cls,
            })
    return symbols

def download_one(info):
    """Download 1y 1H for a single symbol."""
    sym = info['symbol']
    asset_type = info.get('type', '')
    y_sym = yahoo_symbol(sym, asset_type)

    out_path = os.path.join(OUT_DIR, f'{sym}.csv')
    try:
        data = yf.download(y_sym, period='2y', interval='1h',
                           progress=False, auto_adjust=False)
        if data is None or len(data) == 0:
            return {'symbol': sym, 'status': 'empty', 'bars': 0}

        # Flatten multi-index columns (yfinance returns nested columns)
        if hasattr(data.columns, 'nlevels') and data.columns.nlevels > 1:
            data.columns = data.columns.get_level_values(0)

        # Build clean CSV
        with open(out_path, 'w') as f:
            f.write('timestamp,open,high,low,close,volume\n')
            for idx, row in data.iterrows():
                ts = int(idx.timestamp())
                o = float(row['Open']) if not pd_isna(row['Open']) else 0
                h = float(row['High']) if not pd_isna(row['High']) else 0
                l = float(row['Low']) if not pd_isna(row['Low']) else 0
                c = float(row['Close']) if not pd_isna(row['Close']) else 0
                v = int(float(row['Volume'])) if not pd_isna(row['Volume']) else 0
                if o == 0 or c == 0:
                    continue
                f.write(f'{ts},{o},{h},{l},{c},{v}\n')

        return {'symbol': sym, 'yahoo': y_sym, 'status': 'ok', 'bars': len(data),
                'asset_class': info['asset_class']}
    except Exception as e:
        return {'symbol': sym, 'yahoo': y_sym, 'status': 'error',
                'error': str(e)[:80], 'asset_class': info['asset_class']}

def pd_isna(x):
    """Simple NaN check without pandas import in hot loop."""
    return x != x

def main():
    watchlist = json.load(open(WATCHLIST))
    symbols = extract_symbols(watchlist)
    print(f'Found {len(symbols)} symbols in watchlist')

    # Serial download — yfinance has thread-safety issues
    results = []
    for i, s in enumerate(symbols):
        r = download_one(s)
        results.append(r)
        status_mark = '✓' if r['status'] == 'ok' else '✗'
        print(f'  [{i+1}/{len(symbols)}] {status_mark} {r["symbol"]:10} '
              f'{r.get("asset_class", ""):12} '
              f'{r.get("bars", 0)} bars'
              + (f' ERR: {r.get("error", "")[:50]}' if r['status'] != 'ok' else ''))

    # Summary
    by_class = {}
    for r in results:
        cls = r.get('asset_class', 'unknown')
        by_class.setdefault(cls, {'ok': 0, 'fail': 0, 'total_bars': 0})
        if r['status'] == 'ok':
            by_class[cls]['ok'] += 1
            by_class[cls]['total_bars'] += r.get('bars', 0)
        else:
            by_class[cls]['fail'] += 1

    print('\n─── SUMMARY ───')
    for cls, s in by_class.items():
        print(f'  {cls:14} {s["ok"]:2}/{s["ok"]+s["fail"]:2} OK, {s["total_bars"]} total bars')

    # Save manifest
    manifest = {
        'downloaded_at': time.strftime('%Y-%m-%d %H:%M:%S'),
        'summary': by_class,
        'results': results,
    }
    with open(os.path.join(OUT_DIR, '_manifest.json'), 'w') as f:
        json.dump(manifest, f, indent=2, default=str)
    print(f'\nManifest saved to {OUT_DIR}/_manifest.json')

if __name__ == '__main__':
    main()
