#!/usr/bin/env python3
"""
Performance Map — plot all clustering methods as points in (N, WinRate) space.
Shows which methods produce frequent AND reliable patterns.
"""

import csv
import os
import numpy as np
from datetime import datetime
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

CSV_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'nvda-1h-ohlcv.csv')
OUT = os.path.join(os.path.dirname(__file__), '..', 'charts', 'pattern-performance-map.png')
WINDOW, LOOKAHEAD = 5, 5

# ─── Load ───
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

# ─── Features ───
def full_features(window):
    base = window[0]['open']
    vec = []
    for b in window:
        vec.extend([(b['open']-base)/base*100, (b['high']-base)/base*100,
                    (b['low']-base)/base*100, (b['close']-base)/base*100])
    vols = [b['volume'] for b in window]
    avg = np.mean(vols) or 1
    vec.extend([v/avg for v in vols])
    return vec

def shape_features(window):
    vec = []
    for b in window:
        o, h, l, c = b['open'], b['high'], b['low'], b['close']
        total = (h-l) or 1
        body = c - o
        uw, lw = h - max(o, c), min(o, c) - l
        vec.extend([np.sign(body)*(abs(body)/total), uw/total, lw/total])
    closes = [b['close'] for b in window]
    for i in range(1, len(closes)):
        vec.append((closes[i]-closes[i-1])/closes[i-1]*100)
    return vec

def extract(bars, feat_fn):
    feats, outs = [], []
    for i in range(len(bars) - WINDOW - LOOKAHEAD):
        w = bars[i:i+WINDOW]
        f = bars[i+WINDOW:i+WINDOW+LOOKAHEAD]
        feats.append(feat_fn(w))
        entry = w[-1]['close']
        exit_p = f[-1]['close']
        outs.append({
            'change': (exit_p - entry) / entry * 100,
            'direction': 'UP' if exit_p > entry else 'DOWN',
        })
    return np.array(feats), outs

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

def cluster_stats(labels, outs, min_n=10):
    """Return cluster stats with 95% confidence intervals."""
    stats = []
    for j in set(labels):
        m = labels == j
        n = int(m.sum())
        if n < min_n:
            continue
        co = [outs[i] for i in range(len(outs)) if m[i]]
        wr_up = sum(1 for o in co if o['direction'] == 'UP') / n * 100
        avg = np.mean([o['change'] for o in co])
        best_edge = max(wr_up, 100 - wr_up)

        # 95% CI half-width for a proportion: 1.96 * sqrt(p*(1-p)/n)
        p = best_edge / 100
        ci_half = 1.96 * np.sqrt(p * (1 - p) / n) * 100

        # Significance: lower CI bound > 50% means edge is real at 95%
        lower_bound = best_edge - ci_half
        is_significant = lower_bound > 50

        stats.append({
            'n': n, 'wr_up': wr_up, 'best_edge': best_edge,
            'avg': avg, 'cid': j, 'ci_half': ci_half,
            'lower_bound': lower_bound, 'significant': is_significant,
        })
    return stats

def template_match(bars, template, threshold_list=[0.7, 0.8, 0.9]):
    t = np.array(template)
    t = (t - t.mean()) / (t.std() + 1e-8)
    results = {}
    for threshold in threshold_list:
        matches = []
        for i in range(len(bars) - WINDOW - LOOKAHEAD):
            window = bars[i:i+WINDOW]
            closes = np.array([b['close'] for b in window])
            c = (closes - closes.mean()) / (closes.std() + 1e-8)
            corr = np.dot(t, c) / WINDOW
            if corr > threshold:
                entry = window[-1]['close']
                future = bars[i+WINDOW:i+WINDOW+LOOKAHEAD]
                if len(future) >= LOOKAHEAD:
                    chg = (future[-1]['close'] - entry) / entry * 100
                    matches.append({'change': chg, 'direction': 'UP' if chg > 0 else 'DOWN'})
        if len(matches) >= 10:
            n = len(matches)
            wr_up = sum(1 for m in matches if m['direction'] == 'UP') / n * 100
            avg = np.mean([m['change'] for m in matches])
            best_edge = max(wr_up, 100 - wr_up)
            p = best_edge / 100
            ci_half = 1.96 * np.sqrt(p * (1 - p) / n) * 100
            lower = best_edge - ci_half
            results[threshold] = {
                'n': n, 'wr_up': wr_up, 'best_edge': best_edge, 'avg': avg,
                'ci_half': ci_half, 'lower_bound': lower,
                'significant': lower > 50, 'cid': 0,
            }
    return results

def main():
    bars = load_bars(CSV_PATH)
    print(f'Loaded {len(bars)} bars')

    X_full, outs = extract(bars, full_features)
    X_shape, _ = extract(bars, shape_features)
    X_full = (X_full - X_full.mean(0)) / (X_full.std(0) + 1e-8)
    X_shape = (X_shape - X_shape.mean(0)) / (X_shape.std(0) + 1e-8)

    methods = []

    # Method: K-Means FULL with different K values
    for K in [10, 15, 20, 25, 30, 40]:
        labels = kmeans(X_full, K)
        stats = cluster_stats(labels, outs)
        methods.append(('K-Means FULL', K, stats))

    # Method: K-Means SHAPE with different K values
    for K in [10, 15, 20, 25, 30, 40]:
        labels = kmeans(X_shape, K)
        stats = cluster_stats(labels, outs)
        methods.append(('K-Means SHAPE', K, stats))

    # Method: V-reversal template (should go UP after)
    v_template = [-2, -3, -4, -3, -1]
    v_results = template_match(bars, v_template, [0.6, 0.7, 0.8, 0.9])
    for thr, s in v_results.items():
        methods.append(('V-reversal template', thr, [s]))

    # Method: Inverted-V template (should go DOWN after)
    iv_template = [1, 2, 3, 2, 0]
    iv_results = template_match(bars, iv_template, [0.6, 0.7, 0.8, 0.9])
    for thr, s in iv_results.items():
        methods.append(('Inv-V template', thr, [s]))

    # Build plot
    fig, ax = plt.subplots(figsize=(16, 10))
    fig.patch.set_facecolor('#1e1e2e')
    ax.set_facecolor('#1e1e2e')

    # Color per method family
    color_map = {
        'K-Means FULL': '#89b4fa',
        'K-Means SHAPE': '#a6e3a1',
        'V-reversal template': '#f9e2af',
        'Inv-V template': '#cba6f7',
    }
    marker_map = {
        'K-Means FULL': 'o',
        'K-Means SHAPE': 's',
        'V-reversal template': '^',
        'Inv-V template': 'v',
    }

    # Group stats for scatter with error bars
    plotted_labels = set()
    all_significant = []
    for method, param, stats_list in methods:
        for s in stats_list:
            color = color_map[method]
            marker = marker_map[method]
            is_sig = s['significant']
            # Faded for non-significant, solid for significant
            alpha = 0.85 if is_sig else 0.25
            edge = '#f9e2af' if is_sig else '#585b70'

            # Error bar (95% CI on win rate)
            ax.errorbar(s['n'], s['best_edge'], yerr=s['ci_half'],
                       fmt='none', ecolor=edge, elinewidth=0.8,
                       capsize=3, alpha=alpha * 0.6)

            size = 40 + abs(s['avg']) * 80
            label = method if method not in plotted_labels else None
            plotted_labels.add(method)
            ax.scatter([s['n']], [s['best_edge']], s=size, c=color, marker=marker,
                       alpha=alpha, edgecolors=edge, linewidth=1.0, label=label)

            if is_sig:
                all_significant.append((method, param, s))

    # Annotate only STATISTICALLY SIGNIFICANT points
    # (lower CI bound > 50% — means edge is real at 95% confidence)
    all_significant.sort(key=lambda x: -x[2]['lower_bound'])
    for method, param, s in all_significant[:10]:
        method_short = {'K-Means FULL': 'F', 'K-Means SHAPE': 'S',
                        'V-reversal template': 'V', 'Inv-V template': 'IV'}[method]
        label = f'{method_short}{param} C{s["cid"]}: {s["best_edge"]:.0f}±{s["ci_half"]:.0f}%'
        ax.annotate(label, (s['n'], s['best_edge']),
                    xytext=(8, 8), textcoords='offset points',
                    fontsize=9, color='#f9e2af', alpha=0.95, fontweight='bold')

    # Reference lines
    ax.axhline(y=50, color='#585b70', linestyle='--', alpha=0.5, linewidth=0.8)
    ax.axhline(y=60, color='#f9e2af', linestyle='--', alpha=0.4, linewidth=0.8)
    ax.axhline(y=70, color='#a6e3a1', linestyle='--', alpha=0.4, linewidth=0.8)
    ax.text(ax.get_xlim()[1] if ax.get_xlim()[1] > 0 else 100, 50, ' coin flip (50%)',
            color='#585b70', fontsize=9, va='center')
    ax.text(ax.get_xlim()[1] if ax.get_xlim()[1] > 0 else 100, 60, ' decent edge (60%)',
            color='#f9e2af', fontsize=9, va='center')
    ax.text(ax.get_xlim()[1] if ax.get_xlim()[1] > 0 else 100, 70, ' strong edge (70%)',
            color='#a6e3a1', fontsize=9, va='center')

    ax.text(0.5, 0.02,
            'SOLID dots = statistically significant (95% CI lower bound > 50%)\n'
            'FADED dots = too few samples — win rate could be random luck',
            transform=ax.transAxes, color='#a6e3a1', fontsize=10,
            ha='center', fontweight='bold')

    ax.set_xlabel('Frequency (N = times pattern occurred)', color='#cdd6f4', fontsize=12)
    ax.set_ylabel('Best Edge (%) — max of WR_long or WR_short', color='#cdd6f4', fontsize=12)
    ax.set_title('Pattern Performance Map — Frequency vs Win Rate\n'
                 'dot size ∝ avg absolute move | top-right = ideal',
                 color='#cdd6f4', fontsize=14, fontweight='bold', pad=15)
    ax.tick_params(colors='#cdd6f4', labelsize=10)
    for s in ax.spines.values():
        s.set_color('#585b70')
    ax.grid(True, alpha=0.15, color='#585b70')
    ax.legend(loc='upper right', facecolor='#1e1e2e', edgecolor='#585b70',
              labelcolor='#cdd6f4', fontsize=10)

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    fig.savefig(OUT, dpi=140, bbox_inches='tight', facecolor='#1e1e2e')
    plt.close(fig)
    print(f'Saved {OUT}')
    print(f'Total clusters plotted: {sum(len(s) for _, _, s in methods)}')
    print(f'Statistically significant (95% CI lower bound > 50%): {len(all_significant)}')

if __name__ == '__main__':
    main()
