#!/usr/bin/env python3
"""
Characterize EURGBP C0 (LONG) and C8 (SHORT) — what features define them?
Outputs the centroid + ranges so we know exactly when to trigger the trade.
"""
import sys, os, csv
sys.path.insert(0, '/Users/mariashchekanenko/claude-trading-tv/scripts')
import numpy as np
from datetime import datetime
from statistical_validation_v2 import (
    load_csv, precompute_indicators, enhanced_features, kmeans,
    WINDOW, LOOKAHEAD, K
)

# Feature index labels (matches enhanced_features layout)
# 20 OHLC % features (5 bars × O/H/L/C)
# 5 volume ratios (one per bar)
# 7 indicator features at end of window:
#   25: RSI(14)
#   26: EMA20 distance %
#   27: EMA50 distance %
#   28: ATR-normalized range
#   29: Hour (0-23)
#   30: Weekday (0-6)
#   31: EMA stack (EMA20 - EMA50)/EMA50 %
INDICATOR_LABELS = [
    'RSI(14)', 'EMA20 dist %', 'EMA50 dist %',
    'Range/ATR', 'Hour', 'Weekday', 'EMA20-EMA50 %'
]
INDICATOR_START = 25  # index where indicators begin

def main():
    bars = load_csv('/Users/mariashchekanenko/claude-trading-tv/data/ohlcv/EURGBP.csv')
    print(f'Loaded {len(bars)} EURGBP bars')

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

    Xs = (X - X.mean(0)) / (X.std(0) + 1e-8)
    labels = kmeans(Xs, K)

    print(f'\n{"="*70}')
    print('CLUSTER TRIGGER CARDS — what conditions activate each pattern?')
    print(f'{"="*70}')

    for cid, name, direction in [(0, 'C0', 'LONG'), (8, 'C8', 'SHORT')]:
        m = labels == cid
        n = m.sum()
        wins = outs[m].sum()
        wr = wins / n * 100

        print(f'\n──── {name} {direction} (n={n}, WR={wr:.1f}%) ────')
        print(f'\n{"Indicator":>20} {"Mean":>10} {"Std":>10} {"P25":>10} {"P75":>10}')
        print('-' * 65)

        cluster_X = X[m]  # Original (un-standardized) values
        for j, label in enumerate(INDICATOR_LABELS):
            col = INDICATOR_START + j
            vals = cluster_X[:, col]
            print(f'{label:>20} {np.mean(vals):>10.3f} {np.std(vals):>10.3f} '
                  f'{np.percentile(vals, 25):>10.3f} {np.percentile(vals, 75):>10.3f}')

        # Pattern shape — show last candle's body direction tendency
        # Last candle is bars 16-19 of the window vector (open, high, low, close at bar 4)
        last_open_idx = 16
        last_close_idx = 19
        body_signs = np.sign(cluster_X[:, last_close_idx] - cluster_X[:, last_open_idx])
        green_pct = (body_signs > 0).mean() * 100
        print(f'\n  Last candle direction:  {green_pct:.0f}% GREEN, {100-green_pct:.0f}% RED')

        # Compare to global baseline
        print(f'  Global baseline RSI mean: {X[:, INDICATOR_START].mean():.1f}')
        print(f'  Global baseline EMA20 dist mean: {X[:, INDICATOR_START+1].mean():+.3f}%')

if __name__ == '__main__':
    main()
