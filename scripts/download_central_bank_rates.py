#!/usr/bin/env python3
"""
Download central bank policy rates from FRED.
Stores daily rates used to build per-bar rate differential features.
"""
import os
import pandas as pd
import pandas_datareader.data as web
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

OUT_DIR = '/Users/mariashchekanenko/claude-trading-tv/data/rates'
os.makedirs(OUT_DIR, exist_ok=True)

# FRED series IDs
SERIES = {
    'ECB_MRO': 'ECBMRRFR',       # ECB Main Refinancing Operations Rate (EUR policy)
    'ECB_DFR': 'ECBDFR',         # ECB Deposit Facility Rate (EUR lower bound)
    'BOE_SONIA': 'IUDSOIA',      # SONIA — BOE proxy (GBP policy)
    'FED_FUNDS': 'DFF',          # Fed Effective Funds (USD policy)
    # JPY: BOJ is near zero, use 3M JPY interbank as proxy
    'JPY_3M_IB': 'IR3TIB01JPM156N',
    # CHF: SNB policy rate — use 3M CHF interbank
    'CHF_3M_IB': 'IR3TIB01CHM156N',
}

def main():
    start = datetime(2023, 1, 1)
    end = datetime(2026, 4, 30)
    for name, sid in SERIES.items():
        try:
            df = web.DataReader(sid, 'fred', start, end)
            df = df.dropna()
            if len(df) == 0:
                print(f'  {name:12} {sid:20} EMPTY')
                continue
            out = os.path.join(OUT_DIR, f'{name}.csv')
            df.to_csv(out, header=['rate'])
            print(f'  {name:12} {sid:20} {len(df):5} rows, latest {df.index[-1].strftime("%Y-%m-%d")} = {df.iloc[-1, 0]:.3f}%')
        except Exception as e:
            print(f'  {name:12} {sid:20} FAILED: {str(e)[:50]}')

if __name__ == '__main__':
    main()
