#!/usr/bin/env python3
"""
Download additional forex crosses and test if EURGBP-style edges generalize.
Uses identical features and K-Means setup as statistical_validation_v2.
"""
import sys, os, csv, json
sys.path.insert(0, '/Users/mariashchekanenko/claude-trading-tv/scripts')
import yfinance as yf
import numpy as np
from datetime import datetime
from scipy.stats import binomtest
import warnings
warnings.filterwarnings('ignore')

from statistical_validation_v2 import (
    load_csv, precompute_indicators, enhanced_features, kmeans,
    WINDOW, LOOKAHEAD, K, MIN_N
)

OHLCV_DIR = '/Users/mariashchekanenko/claude-trading-tv/data/ohlcv'
OUT = '/Users/mariashchekanenko/claude-trading-tv/data/forex-cross-validation.json'

# Forex crosses to test (Yahoo symbols)
NEW_CROSSES = {
    'EURJPY': 'EURJPY=X',
    'EURCHF': 'EURCHF=X',
    'AUDJPY': 'AUDJPY=X',
    'AUDUSD': 'AUDUSD=X',
    'USDCHF': 'USDCHF=X',
    'NZDUSD': 'NZDUSD=X',
    'EURAUD': 'EURAUD=X',
    'GBPCHF': 'GBPCHF=X',
}

def download(sym, y_sym):
    out = os.path.join(OHLCV_DIR, f'{sym}.csv')
    if os.path.exists(out):
        return None  # already have it
    try:
        data = yf.download(y_sym, period='2y', interval='1h',
                           progress=False, auto_adjust=False)
        if data is None or len(data) == 0:
            return None
        if hasattr(data.columns, 'nlevels') and data.columns.nlevels > 1:
            data.columns = data.columns.get_level_values(0)
        with open(out, 'w') as f:
            f.write('timestamp,open,high,low,close,volume\n')
            for idx, row in data.iterrows():
                ts = int(idx.timestamp())
                o = float(row['Open']) if row['Open'] == row['Open'] else 0
                h = float(row['High']) if row['High'] == row['High'] else 0
                l = float(row['Low']) if row['Low'] == row['Low'] else 0
                c = float(row['Close']) if row['Close'] == row['Close'] else 0
                v = int(float(row['Volume'])) if row['Volume'] == row['Volume'] else 0
                if o > 0 and c > 0:
                    f.write(f'{ts},{o},{h},{l},{c},{v}\n')
        return len(data)
    except Exception as e:
        return None

def analyze(sym):
    bars = load_csv(os.path.join(OHLCV_DIR, f'{sym}.csv'))
    if len(bars) < 200:
        return None

    ind = precompute_indicators(bars)
    feats, outs = [], []
    for i in range(len(bars) - WINDOW - LOOKAHEAD):
        v = enhanced_features(bars, ind, i)
        if v is None or any(np.isnan(v)) or any(np.isinf(v)):
            continue
        feats.append(v)
        entry = bars[i + WINDOW - 1]['close']
        exit_p = bars[i + WINDOW - 1 + LOOKAHEAD]['close']
        outs.append(1 if exit_p > entry else 0)

    X = np.array(feats)
    outs = np.array(outs)
    if len(X) < 50:
        return None
    baseline = outs.mean()

    Xs = (X - X.mean(0)) / (X.std(0) + 1e-8)
    labels = kmeans(Xs, K)
    if labels is None:
        return None

    clusters = []
    for cid in set(labels):
        m = labels == cid
        n = int(m.sum())
        if n < MIN_N:
            continue
        wins = int(outs[m].sum())
        wr = wins / n * 100
        edge = wr - baseline * 100

        # Cluster's avg indicator values for context
        cluster_X = X[m]
        rsi = cluster_X[:, 25].mean()
        e20 = cluster_X[:, 26].mean()
        atr_r = cluster_X[:, 28].mean()
        hour = cluster_X[:, 29].mean()

        clusters.append({
            'cid': int(cid), 'n': n, 'k_up': wins, 'wr': wr,
            'baseline': baseline * 100, 'edge': edge,
            'rsi_mean': float(rsi), 'ema20_dist': float(e20),
            'range_atr': float(atr_r), 'hour_mean': float(hour),
        })
    return {'symbol': sym, 'bars': len(bars), 'baseline_pct': baseline * 100,
            'clusters': clusters}

def main():
    # Step 1: Download missing forex crosses
    print('─── Downloading new forex crosses ───')
    for sym, ysym in NEW_CROSSES.items():
        n = download(sym, ysym)
        if n is None:
            existing = os.path.exists(os.path.join(OHLCV_DIR, f'{sym}.csv'))
            print(f'  {sym:8} {"already have" if existing else "FAILED"}')
        else:
            print(f'  {sym:8} {n} bars downloaded')

    # Step 2: Analyze EURGBP + new crosses
    all_symbols = ['EURGBP'] + list(NEW_CROSSES.keys())
    print(f'\n─── Analyzing {len(all_symbols)} forex crosses ───')

    all_results = {}
    all_patterns_for_bonferroni = []

    for sym in all_symbols:
        path = os.path.join(OHLCV_DIR, f'{sym}.csv')
        if not os.path.exists(path):
            continue
        r = analyze(sym)
        if r is None:
            print(f'  {sym:8} insufficient data')
            continue
        all_results[sym] = r
        # Pool patterns for one combined Bonferroni test
        for c in r['clusters']:
            all_patterns_for_bonferroni.append({
                'symbol': sym, 'cluster': c['cid'], 'n': c['n'],
                'k_up': c['k_up'], 'baseline_p': r['baseline_pct'] / 100,
                'wr': c['wr'], 'edge': c['edge'],
                'rsi': c['rsi_mean'], 'ema20': c['ema20_dist'],
                'atr_r': c['range_atr'], 'hour': c['hour_mean'],
            })

    # Combined Bonferroni
    total = len(all_patterns_for_bonferroni)
    threshold = 0.05 / total
    print(f'\nTotal patterns across all crosses: {total}')
    print(f'Bonferroni threshold: {threshold:.2e}')

    survivors = []
    for p in all_patterns_for_bonferroni:
        result = binomtest(p['k_up'], p['n'], p['baseline_p'], alternative='two-sided')
        p['p_value'] = float(result.pvalue)
        if result.pvalue < threshold:
            p['direction'] = 'LONG' if p['edge'] > 0 else 'SHORT'
            survivors.append(p)

    survivors.sort(key=lambda x: x['p_value'])

    print(f'Survivors: {len(survivors)}')
    if survivors:
        print(f'\n{"Symbol":>8} {"Clu":>4} {"N":>5} {"WR%":>5} {"Base%":>6} '
              f'{"Edge":>6} {"Dir":>5} {"RSI":>5} {"EMA20%":>7} {"R/ATR":>6} '
              f'{"Hour":>5} {"p-value":>10}')
        print('-' * 105)
        for p in survivors:
            print(f'{p["symbol"]:>8} {p["cluster"]:>4} {p["n"]:>5} '
                  f'{p["wr"]:>5.1f} {p["baseline_p"]*100:>6.1f} '
                  f'{p["edge"]:>+6.1f} {p["direction"]:>5} '
                  f'{p["rsi"]:>5.1f} {p["ema20"]:>+7.3f} '
                  f'{p["atr_r"]:>6.2f} {p["hour"]:>5.1f} {p["p_value"]:>10.2e}')

    # Per-symbol summary: best edge regardless of significance
    print(f'\n─── Per-symbol best clusters (any significance) ───')
    print(f'{"Symbol":>8} {"BestWR":>7} {"Edge":>6} {"N":>5} {"Hour":>5} {"RSI":>5}')
    print('-' * 50)
    for sym, r in all_results.items():
        if not r['clusters']:
            print(f'{sym:>8} no qualifying clusters')
            continue
        best = max(r['clusters'], key=lambda c: abs(c['edge']))
        print(f'{sym:>8} {best["wr"]:>6.1f}% {best["edge"]:>+6.1f} {best["n"]:>5} '
              f'{best["hour_mean"]:>5.1f} {best["rsi_mean"]:>5.1f}')

    out_data = {
        'analyzed_at': datetime.now().isoformat(),
        'crosses_tested': all_symbols,
        'total_patterns': total,
        'bonferroni_threshold': threshold,
        'survivors_count': len(survivors),
        'survivors': survivors,
        'per_symbol': all_results,
    }
    with open(OUT, 'w') as f:
        json.dump(out_data, f, indent=2, default=str)
    print(f'\nSaved to {OUT}')

if __name__ == '__main__':
    main()
