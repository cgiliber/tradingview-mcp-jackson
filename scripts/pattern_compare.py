#!/usr/bin/env python3
"""
Compare clustering approaches:
1. K=40 (tighter clusters, more visual similarity within each)
2. Shape-only features (direction + body size, no price magnitudes)
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

# Features method 1: full OHLC (original, 25 dims)
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

# Features method 2: shape only (direction + body ratio + wick ratio per candle)
def shape_features(window):
    vec = []
    for b in window:
        o, h, l, c = b['open'], b['high'], b['low'], b['close']
        total_range = (h - l) or 1
        body = (c - o)  # signed
        upper_wick = h - max(o, c)
        lower_wick = min(o, c) - l
        vec.extend([
            np.sign(body) * (abs(body) / total_range),  # body size signed
            upper_wick / total_range,
            lower_wick / total_range,
        ])
    # Consecutive close changes (momentum)
    closes = [b['close'] for b in window]
    for i in range(1, len(closes)):
        chg = (closes[i] - closes[i-1]) / closes[i-1] * 100
        vec.append(chg)
    return vec

def extract(bars, feat_fn, win=5, lookahead=5):
    feats, outcomes, meta = [], [], []
    for i in range(len(bars) - win - lookahead):
        window = bars[i:i+win]
        future = bars[i+win:i+win+lookahead]
        feats.append(feat_fn(window))
        entry = window[-1]['close']
        exit_p = future[-1]['close']
        outcomes.append({
            'change': (exit_p - entry) / entry * 100,
            'direction': 'UP' if exit_p > entry else 'DOWN',
        })
        meta.append({'index': i, 'entry': entry})
    return np.array(feats), outcomes, meta

def kmeans(X, k=30, max_iter=100, seed=42):
    rng = np.random.RandomState(seed)
    n = X.shape[0]
    centroids = np.empty((k, X.shape[1]))
    centroids[0] = X[rng.randint(n)]
    for j in range(1, k):
        dists = np.min([np.sum((X - centroids[c])**2, axis=1) for c in range(j)], axis=0)
        p = dists / dists.sum()
        centroids[j] = X[rng.choice(n, p=p)]
    labels = np.zeros(n, dtype=int)
    for _ in range(max_iter):
        d = np.array([np.sum((X - c)**2, axis=1) for c in centroids])
        new = np.argmin(d, axis=0)
        if np.array_equal(new, labels):
            break
        labels = new
        for j in range(k):
            m = labels == j
            if m.sum() > 0:
                centroids[j] = X[m].mean(axis=0)
    return labels, centroids

def draw_pattern(ax, bars_w, title, alpha=1.0):
    GREEN, RED = '#26a69a', '#ef5350'
    W = 0.7
    for i, b in enumerate(bars_w):
        o, h, l, c = b['open'], b['high'], b['low'], b['close']
        col = GREEN if c >= o else RED
        ax.plot([i, i], [l, h], color=col, linewidth=1.2, alpha=alpha)
        blo = min(o, c)
        bh = abs(c - o) or 0.01
        ax.add_patch(Rectangle((i - W/2, blo), W, bh,
                                facecolor=col, edgecolor='none', alpha=alpha))
    ax.autoscale_view()
    ax.set_xlim(-0.5, len(bars_w) - 0.5)
    ax.set_facecolor('#1e1e2e')
    ax.tick_params(colors='#585b70', labelsize=7)
    for s in ax.spines.values():
        s.set_color('#585b70')
    ax.set_title(title, color='#cdd6f4', fontsize=9, fontweight='bold')

def pick_top_bullish(X, labels, outcomes, k, min_n=5, max_clusters=3):
    stats = []
    for j in range(k):
        m = labels == j
        n = m.sum()
        if n < min_n:
            continue
        co = [outcomes[i] for i in range(len(outcomes)) if m[i]]
        wr = sum(1 for o in co if o['direction'] == 'UP') / n * 100
        avg = np.mean([o['change'] for o in co])
        stats.append((j, n, wr, avg))
    stats.sort(key=lambda x: (-x[2], -x[1]))
    return stats[:max_clusters]

def main():
    bars = load_bars(CSV_PATH)

    # Run both methods
    X_full, outs, meta = extract(bars, full_features)
    X_shape, _, _ = extract(bars, shape_features)

    # Standardize
    X_full = (X_full - X_full.mean(0)) / (X_full.std(0) + 1e-8)
    X_shape = (X_shape - X_shape.mean(0)) / (X_shape.std(0) + 1e-8)

    K = 30
    labels_full, _ = kmeans(X_full, k=K)
    labels_shape, _ = kmeans(X_shape, k=K)

    # For each method, pick top bullish cluster and show 4 examples
    top_full = pick_top_bullish(X_full, labels_full, outs, K, min_n=5, max_clusters=2)
    top_shape = pick_top_bullish(X_shape, labels_shape, outs, K, min_n=5, max_clusters=2)

    # Plot: 2 rows per method, 4 cols
    fig, axes = plt.subplots(4, 4, figsize=(22, 14))
    fig.patch.set_facecolor('#1e1e2e')

    def plot_cluster_row(row_idx, stats_row, labels, method_label):
        cid, n, wr, avg = stats_row
        # Find first 4 indices in cluster
        idxs = [i for i in range(len(labels)) if labels[i] == cid][:4]
        for col, idx in enumerate(idxs):
            ax = axes[row_idx][col]
            pattern = bars[idx:idx+5]
            title = f'{method_label} C{cid} ex{col+1}'
            draw_pattern(ax, pattern, title)
        # Label row
        axes[row_idx][0].text(-0.3, 0.5,
            f'{method_label}\nC{cid}\nWR {wr:.0f}%\nn={n}',
            transform=axes[row_idx][0].transAxes,
            ha='right', va='center', color='#cdd6f4', fontsize=11, fontweight='bold')

    # Row 0-1: FULL features top 2 clusters
    for i, s in enumerate(top_full[:2]):
        plot_cluster_row(i, s, labels_full, 'FULL')
    # Row 2-3: SHAPE features top 2 clusters
    for i, s in enumerate(top_shape[:2]):
        plot_cluster_row(i + 2, s, labels_shape, 'SHAPE')

    fig.suptitle('Clustering Comparison: FULL OHLC vs SHAPE-only (K=30)\n'
                 'Are patterns within a cluster VISUALLY similar?',
                 color='#cdd6f4', fontsize=16, fontweight='bold', y=0.995)
    plt.subplots_adjust(left=0.08, hspace=0.45, wspace=0.2, top=0.93)

    out = os.path.join(os.path.dirname(__file__), '..', 'charts', 'pattern-compare.png')
    fig.savefig(out, dpi=130, bbox_inches='tight', facecolor='#1e1e2e')
    plt.close(fig)
    print(f'Saved {out}')

if __name__ == '__main__':
    main()
