#!/usr/bin/env python3
"""
Pattern + Aftermath using tighter clustering (K=30, SHAPE features).
Shows 4 real examples per top cluster with the "after" candles dimmed.
"""

import csv
import os
import numpy as np
from datetime import datetime
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

CSV_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'nvda-1h-ohlcv.csv')
OUT = os.path.join(os.path.dirname(__file__), '..', 'charts', 'pattern-v2-aftermath.png')
WINDOW, LOOKAHEAD = 5, 5

def load_bars(path):
    bars = []
    with open(path) as f:
        for r in csv.DictReader(f):
            bars.append({
                'time': datetime.utcfromtimestamp(int(r['timestamp'])),
                'open': float(r['open']), 'high': float(r['high']),
                'low': float(r['low']), 'close': float(r['close']),
                'volume': int(float(r['volume'])),
            })
    return bars

def full_features(window):
    base = window[0]['open']
    vec = []
    for b in window:
        vec.extend([
            (b['open'] - base) / base * 100,
            (b['high'] - base) / base * 100,
            (b['low'] - base) / base * 100,
            (b['close'] - base) / base * 100,
        ])
    vols = [b['volume'] for b in window]
    avg_v = np.mean(vols) or 1
    vec.extend([v / avg_v for v in vols])
    return vec

def shape_features(window):
    vec = []
    for b in window:
        o, h, l, c = b['open'], b['high'], b['low'], b['close']
        total = (h - l) or 1
        body = c - o
        uw = h - max(o, c)
        lw = min(o, c) - l
        vec.extend([np.sign(body) * (abs(body) / total), uw / total, lw / total])
    closes = [b['close'] for b in window]
    for i in range(1, len(closes)):
        vec.append((closes[i] - closes[i-1]) / closes[i-1] * 100)
    return vec

def extract(bars, feat_fn):
    feats, outs, meta = [], [], []
    for i in range(len(bars) - WINDOW - LOOKAHEAD):
        window = bars[i:i+WINDOW]
        future = bars[i+WINDOW:i+WINDOW+LOOKAHEAD]
        feats.append(feat_fn(window))
        entry = window[-1]['close']
        exit_p = future[-1]['close']
        outs.append({
            'change': (exit_p - entry) / entry * 100,
            'direction': 'UP' if exit_p > entry else 'DOWN',
        })
        meta.append({'index': i})
    return np.array(feats), outs, meta

def kmeans(X, k, max_iter=100, seed=42):
    rng = np.random.RandomState(seed)
    n = X.shape[0]
    cent = np.empty((k, X.shape[1]))
    cent[0] = X[rng.randint(n)]
    for j in range(1, k):
        d = np.min([np.sum((X - cent[c])**2, axis=1) for c in range(j)], axis=0)
        cent[j] = X[rng.choice(n, p=d/d.sum())]
    labels = np.zeros(n, dtype=int)
    for _ in range(max_iter):
        d = np.array([np.sum((X - c)**2, axis=1) for c in cent])
        new = np.argmin(d, axis=0)
        if np.array_equal(new, labels):
            break
        labels = new
        for j in range(k):
            m = labels == j
            if m.sum() > 0:
                cent[j] = X[m].mean(axis=0)
    return labels

def pick_top(labels, outs, k, min_n=6, n_top=2, direction='UP'):
    stats = []
    for j in range(k):
        m = labels == j
        n = int(m.sum())
        if n < min_n:
            continue
        co = [outs[i] for i in range(len(outs)) if m[i]]
        wins = sum(1 for o in co if o['direction'] == direction)
        wr = wins / n * 100
        avg = np.mean([o['change'] for o in co])
        stats.append({'cid': j, 'n': n, 'wr': wr, 'avg': avg})
    stats.sort(key=lambda s: (-s['wr'], -s['n']))
    return stats[:n_top]

def draw_row(axes_row, bars, label_left, stats_row, labels_arr, method_name):
    cid = stats_row['cid']
    idxs = [i for i in range(len(labels_arr)) if labels_arr[i] == cid][:4]
    GREEN, RED = '#26a69a', '#ef5350'
    W = 0.7

    for col, idx in enumerate(idxs):
        ax = axes_row[col]
        pattern = bars[idx:idx+WINDOW]
        after = bars[idx+WINDOW:idx+WINDOW+LOOKAHEAD]
        if len(after) < LOOKAHEAD:
            ax.set_visible(False)
            continue
        all_b = pattern + after

        for i, b in enumerate(all_b):
            o, h, l, c = b['open'], b['high'], b['low'], b['close']
            col_c = GREEN if c >= o else RED
            alpha = 1.0 if i < WINDOW else 0.45
            ax.plot([i, i], [l, h], color=col_c, linewidth=1.3, alpha=alpha)
            blo = min(o, c)
            bh = abs(c - o) or 0.01
            ax.add_patch(Rectangle((i - W/2, blo), W, bh,
                                   facecolor=col_c, edgecolor='none', alpha=alpha))

        ax.axvline(x=WINDOW - 0.5, color='#f9e2af', linestyle='--', linewidth=1.2, alpha=0.8)
        entry = pattern[-1]['close']
        exit_p = after[-1]['close']
        outcome = (exit_p - entry) / entry * 100
        ax.axhline(y=entry, color='#89b4fa', linestyle=':', linewidth=0.8, alpha=0.6)
        ymin = min(b['low'] for b in all_b)
        ymax = max(b['high'] for b in all_b)
        ax.axvspan(WINDOW - 0.5, len(all_b) - 0.5, color='#585b70', alpha=0.15)

        arrow_col = GREEN if outcome > 0 else RED
        ax.annotate('', xy=(len(all_b) - 1, exit_p),
                    xytext=(WINDOW - 1, entry),
                    arrowprops=dict(arrowstyle='->', color=arrow_col, lw=1.8, alpha=0.9))

        ax.autoscale_view()
        ax.set_xlim(-0.5, len(all_b) - 0.5)
        ax.set_facecolor('#1e1e2e')
        ax.tick_params(colors='#585b70', labelsize=8)
        for s in ax.spines.values():
            s.set_color('#585b70')
        ax.grid(True, alpha=0.1, color='#585b70')

        t_col = GREEN if outcome > 0 else RED
        date_str = pattern[0]['time'].strftime('%b %d %H:%M')
        ax.set_title(f'{method_name} C{cid} | {date_str}\n${entry:.2f} → ${exit_p:.2f} ({outcome:+.2f}%)',
                     color=t_col, fontsize=10, fontweight='bold')
        ax.text(WINDOW/2 - 0.5, ymax, 'PATTERN', ha='center', va='top',
                color='#89b4fa', fontsize=9, fontweight='bold')
        ax.text(WINDOW + LOOKAHEAD/2 - 0.5, ymax, 'AFTER →', ha='center', va='top',
                color='#f9e2af', fontsize=9, fontweight='bold')

    axes_row[0].text(-0.25, 0.5, label_left,
                     transform=axes_row[0].transAxes, ha='right', va='center',
                     color='#cdd6f4', fontsize=12, fontweight='bold')

def main():
    bars = load_bars(CSV_PATH)
    print(f'Loaded {len(bars)} bars')

    X_full, outs, _ = extract(bars, full_features)
    X_shape, _, _ = extract(bars, shape_features)
    X_full = (X_full - X_full.mean(0)) / (X_full.std(0) + 1e-8)
    X_shape = (X_shape - X_shape.mean(0)) / (X_shape.std(0) + 1e-8)

    K = 30
    lab_full = kmeans(X_full, K)
    lab_shape = kmeans(X_shape, K)

    top_bull_full = pick_top(lab_full, outs, K, min_n=6, n_top=2, direction='UP')
    top_bull_shape = pick_top(lab_shape, outs, K, min_n=6, n_top=2, direction='UP')
    top_bear_full = pick_top(lab_full, outs, K, min_n=6, n_top=1, direction='DOWN')
    top_bear_shape = pick_top(lab_shape, outs, K, min_n=6, n_top=1, direction='DOWN')

    rows_info = [
        (top_bull_full[0], lab_full, 'FULL', 'BULLISH'),
        (top_bull_shape[0], lab_shape, 'SHAPE', 'BULLISH'),
        (top_bear_full[0], lab_full, 'FULL', 'BEARISH'),
        (top_bear_shape[0], lab_shape, 'SHAPE', 'BEARISH'),
    ]

    fig, axes = plt.subplots(len(rows_info), 4, figsize=(26, 4.2 * len(rows_info)))
    fig.patch.set_facecolor('#1e1e2e')

    for row_idx, (stats, labels_arr, method, bias) in enumerate(rows_info):
        cid, n, wr, avg = stats['cid'], stats['n'], stats['wr'], stats['avg']
        label = f'{method}\nC{cid}\n{bias}\nWR {wr:.0f}%\nn={n}\navg {avg:+.2f}%'
        draw_row(axes[row_idx], bars, label, stats, labels_arr, method)

    fig.suptitle('K=30 Tighter Clusters — Pattern + Aftermath\n(bright = pattern | dimmed = 5 candles after | arrow = outcome)',
                 color='#cdd6f4', fontsize=17, fontweight='bold', y=0.998)
    plt.subplots_adjust(left=0.08, hspace=0.55, wspace=0.22, top=0.95)

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    fig.savefig(OUT, dpi=120, bbox_inches='tight', facecolor='#1e1e2e')
    plt.close(fig)
    print(f'Saved {OUT}')

if __name__ == '__main__':
    main()
