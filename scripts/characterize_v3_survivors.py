#!/usr/bin/env python3
"""Characterize the 3 Bonferroni survivors from v3 (GBPCHF C18, EURUSD C11, GBPJPY C6)."""
import sys, os, json
sys.path.insert(0, '/Users/mariashchekanenko/claude-trading-tv/scripts')
import numpy as np
from statistical_validation_v3 import extract_v3, load_csv, kmeans, K

TARGETS = [
    ('GBPCHF', 18, 'SHORT'),
    ('EURUSD', 11, 'LONG'),
    ('GBPJPY', 6, 'LONG'),
]
# Feature index map (32 base + 4 rate = 36 dims)
# 0-19: OHLC %; 20-24: vol ratios; 25-31: indicators; 32-35: rates
INDICATORS = {
    25: 'RSI(14)', 26: 'EMA20_dist%', 27: 'EMA50_dist%',
    28: 'Range/ATR', 29: 'Hour', 30: 'Weekday', 31: 'EMA20-EMA50%',
    32: 'Rate_diff%', 33: 'Rate_change_30d', 34: 'Days_since_base_rate_change',
    35: 'Days_since_quote_rate_change',
}

for sym, target_cid, direction in TARGETS:
    bars = load_csv(f'/Users/mariashchekanenko/claude-trading-tv/data/ohlcv/{sym}.csv')
    X, outs = extract_v3(bars, sym)
    Xs = (X - X.mean(0)) / (X.std(0) + 1e-8)
    labels = kmeans(Xs, K)

    m = labels == target_cid
    n = m.sum()
    wr = outs[m].mean() * 100
    baseline = outs.mean() * 100

    print(f'\n══════ {sym} C{target_cid} {direction} ══════')
    print(f'N={n}, WR={wr:.1f}%, baseline={baseline:.1f}%, edge={wr-baseline:+.1f}%')
    print(f'\n{"Feature":>32} {"Cluster mean":>15} {"Global mean":>15}')
    print('-' * 65)
    cluster_X = X[m]
    for idx, name in INDICATORS.items():
        cm = cluster_X[:, idx].mean()
        gm = X[:, idx].mean()
        marker = '  ←' if abs(cm - gm) > X[:, idx].std() else ''
        print(f'{name:>32} {cm:>15.3f} {gm:>15.3f}{marker}')
