#!/usr/bin/env python3
"""
Visualize the 2 Bonferroni-surviving EURGBP patterns:
- C0: LONG (n=1297, WR 56.1%)
- C8: SHORT (n=770, WR 42.1%)

Shows 6 real examples per cluster with pattern + aftermath.
Uses the SAME features as statistical_validation_v2.py (must produce same clusters).
"""
import sys
sys.path.insert(0, '/Users/mariashchekanenko/claude-trading-tv/scripts')
import os
import csv
import numpy as np
from datetime import datetime
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

# Reuse functions from validation script
from statistical_validation_v2 import (
    load_csv, precompute_indicators, enhanced_features, kmeans,
    WINDOW, LOOKAHEAD, K
)

OHLCV = '/Users/mariashchekanenko/claude-trading-tv/data/ohlcv/EURGBP.csv'
OUT = '/Users/mariashchekanenko/claude-trading-tv/charts/eurgbp-survivors.png'

# Re-run extraction but keep indices
def extract_with_indices(bars):
    ind = precompute_indicators(bars)
    feats, outs, idxs = [], [], []
    for i in range(len(bars) - WINDOW - LOOKAHEAD):
        v = enhanced_features(bars, ind, i)
        if v is None or any(np.isnan(v)) or any(np.isinf(v)):
            continue
        feats.append(v)
        entry = bars[i + WINDOW - 1]['close']
        exit_p = bars[i + WINDOW - 1 + LOOKAHEAD]['close']
        outs.append(1 if exit_p > entry else 0)
        idxs.append(i)
    return np.array(feats), np.array(outs), idxs

def draw(ax, pattern_bars, after_bars, title_prefix, outcome_pct):
    GREEN, RED = '#26a69a', '#ef5350'
    W = 0.7
    all_b = pattern_bars + after_bars

    for i, b in enumerate(all_b):
        o, h, l, c = b['open'], b['high'], b['low'], b['close']
        col = GREEN if c >= o else RED
        alpha = 1.0 if i < WINDOW else 0.45
        ax.plot([i, i], [l, h], color=col, linewidth=1.3, alpha=alpha)
        blo = min(o, c)
        bh = abs(c - o) or (h - l) * 0.001
        ax.add_patch(Rectangle((i - W/2, blo), W, bh,
                               facecolor=col, edgecolor='none', alpha=alpha))

    # Divider + entry line + arrow
    ax.axvline(x=WINDOW - 0.5, color='#f9e2af', linestyle='--', linewidth=1.2, alpha=0.8)
    entry = pattern_bars[-1]['close']
    exit_p = after_bars[-1]['close']
    ax.axhline(y=entry, color='#89b4fa', linestyle=':', linewidth=0.8, alpha=0.6)
    ymin = min(b['low'] for b in all_b)
    ymax = max(b['high'] for b in all_b)
    ax.axvspan(WINDOW - 0.5, len(all_b) - 0.5, color='#585b70', alpha=0.15)

    arrow_col = GREEN if outcome_pct > 0 else RED
    ax.annotate('', xy=(len(all_b) - 1, exit_p), xytext=(WINDOW - 1, entry),
                arrowprops=dict(arrowstyle='->', color=arrow_col, lw=1.8, alpha=0.9))

    ax.autoscale_view()
    ax.set_xlim(-0.5, len(all_b) - 0.5)
    ax.set_facecolor('#1e1e2e')
    ax.tick_params(colors='#585b70', labelsize=8)
    for s in ax.spines.values():
        s.set_color('#585b70')
    ax.grid(True, alpha=0.1, color='#585b70')

    t_col = GREEN if outcome_pct > 0 else RED
    ax.set_title(f'{title_prefix}\n{entry:.5f} → {exit_p:.5f} ({outcome_pct:+.3f}%)',
                 color=t_col, fontsize=10, fontweight='bold')
    ax.text(WINDOW/2 - 0.5, ymax, 'PATTERN', ha='center', va='top',
            color='#89b4fa', fontsize=9, fontweight='bold')
    ax.text(WINDOW + LOOKAHEAD/2 - 0.5, ymax, 'AFTER →', ha='center', va='top',
            color='#f9e2af', fontsize=9, fontweight='bold')

def main():
    bars = load_csv(OHLCV)
    print(f'Loaded {len(bars)} EURGBP bars')

    X, outs, idxs = extract_with_indices(bars)
    print(f'Extracted {len(X)} windows')

    Xs = (X - X.mean(0)) / (X.std(0) + 1e-8)
    labels = kmeans(Xs, K)
    print(f'K-Means K={K} done')

    # Verify cluster stats match the validation
    for cid in [0, 8]:
        m = labels == cid
        n = int(m.sum())
        wins = int(outs[m].sum())
        wr = wins / n * 100
        print(f'  C{cid}: n={n}, wins={wins}, WR={wr:.1f}%')

    # Sample 6 examples (evenly spaced in time) from each cluster
    cluster_examples = {}
    for cid in [0, 8]:
        cluster_indices = [idxs[i] for i in range(len(labels)) if labels[i] == cid]
        # Take 6 evenly distributed
        if len(cluster_indices) <= 6:
            chosen = cluster_indices
        else:
            step = len(cluster_indices) // 6
            chosen = [cluster_indices[i * step] for i in range(6)]
        cluster_examples[cid] = chosen

    # Plot 2 rows × 6 columns
    fig, axes = plt.subplots(2, 6, figsize=(28, 10))
    fig.patch.set_facecolor('#1e1e2e')

    cluster_meta = {
        0: {'label': 'EURGBP C0\nLONG\n+6.4% edge\nn=1297\nWR 56.1%\np=5.1e-6', 'color': '#a6e3a1'},
        8: {'label': 'EURGBP C8\nSHORT\n-7.7% edge\nn=770\nWR 42.1%\np=2.1e-5', 'color': '#f38ba8'},
    }

    for row_idx, cid in enumerate([0, 8]):
        for col, idx in enumerate(cluster_examples[cid]):
            ax = axes[row_idx][col]
            pattern = bars[idx:idx + WINDOW]
            after = bars[idx + WINDOW:idx + WINDOW + LOOKAHEAD]
            entry = pattern[-1]['close']
            exit_p = after[-1]['close']
            outcome = (exit_p - entry) / entry * 100
            date_str = pattern[0]['time'].strftime('%Y-%m-%d %H:%M')
            draw(ax, pattern, after, f'C{cid} | {date_str}', outcome)

        # Row label
        meta = cluster_meta[cid]
        axes[row_idx][0].text(-0.28, 0.5, meta['label'],
                              transform=axes[row_idx][0].transAxes,
                              ha='right', va='center', color=meta['color'],
                              fontsize=13, fontweight='bold')

    fig.suptitle('EURGBP — The 2 Bonferroni-Surviving Patterns (real edges)\n'
                 'PATTERN (bright) + AFTERMATH (dimmed) | green arrow = price went UP after | red arrow = DOWN',
                 color='#cdd6f4', fontsize=15, fontweight='bold', y=0.998)
    plt.subplots_adjust(left=0.07, hspace=0.5, wspace=0.25, top=0.93)

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    fig.savefig(OUT, dpi=120, bbox_inches='tight', facecolor='#1e1e2e')
    plt.close(fig)
    print(f'Saved {OUT}')

if __name__ == '__main__':
    main()
