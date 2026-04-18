#!/usr/bin/env python3
"""Extract trigger conditions from the 4 v5 crypto Bonferroni survivors."""
import sys, os
sys.path.insert(0, '/Users/mariashchekanenko/claude-trading-tv/scripts')
import numpy as np
from statistical_validation_v2 import load_csv, kmeans
from statistical_validation_v5_crypto import extract_v5, K

# Target survivors
TARGETS = [
    ('XRPUSD', 1, 'LONG'),
    ('ADAUSD', 9, 'LONG'),
    ('XRPUSD', 10, 'SHORT'),
    ('XRPUSD', 0, 'LONG'),
]

# Feature indices (v5 crypto layout):
# 0-19: OHLC %, 20-24: vol ratios, 25-32: indicators (RSI, EMA20dist, EMA50dist, range/ATR, hour, weekday, weekend, EMA20-50),
# 33-36: funding (current%, 3d avg%, extremity, 1d change)
LABELS = {
    25: 'RSI(14)', 26: 'EMA20_dist%', 27: 'EMA50_dist%', 28: 'Range/ATR',
    29: 'Hour', 30: 'Weekday', 31: 'Weekend',
    33: 'Funding_now%', 34: 'Funding_3d_avg%', 35: 'Funding_extremity%',
    36: 'Funding_change_1d%',
}

for sym, cid, direction in TARGETS:
    bars = load_csv(f'/Users/mariashchekanenko/claude-trading-tv/data/ohlcv/{sym}.csv')
    X, outs = extract_v5(bars, sym)
    Xs = (X - X.mean(0)) / (X.std(0) + 1e-8)
    labels = kmeans(Xs, K)
    m = labels == cid
    n = m.sum()
    wr = outs[m].mean() * 100
    baseline = outs.mean() * 100
    cluster_X = X[m]

    print(f'\n══════ {sym} C{cid} {direction} ══════')
    print(f'N={n}, WR={wr:.1f}%, baseline={baseline:.1f}%, edge={wr-baseline:+.1f}%')
    print(f'\n{"Feature":>22} {"Mean":>12} {"P25":>12} {"P75":>12} {"Global":>12}')
    print('-' * 75)
    for idx, name in LABELS.items():
        vals = cluster_X[:, idx]
        print(f'{name:>22} {vals.mean():>12.4f} {np.percentile(vals, 25):>12.4f} '
              f'{np.percentile(vals, 75):>12.4f} {X[:, idx].mean():>12.4f}')
