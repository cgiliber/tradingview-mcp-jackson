#!/usr/bin/env python3
"""
Visualize the 4 multi-split robust patterns from v7:
BCS C2, HSBC C11, DNBBY C2, BCS C4 — all LONG.

Shows 6 real examples per pattern with pattern (bright) + aftermath (dimmed).
"""
import sys, os
sys.path.insert(0, '/Users/mariashchekanenko/claude-trading-tv/scripts')
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from statistical_validation_v2 import load_csv, kmeans, WINDOW, LOOKAHEAD
from multi_split_validation import v2_feat, extract_with_idx, K

WINNERS = [
    {'sym': 'BCS',   'cid': 2,  'label': 'BCS C2\nLONG\nBarclays\n5/5 splits'},
    {'sym': 'HSBC',  'cid': 11, 'label': 'HSBC C11\nLONG\n5/5 splits'},
    {'sym': 'DNBBY', 'cid': 2,  'label': 'DNBBY C2\nLONG\nDNB Bank\n5/5 splits'},
    {'sym': 'BCS',   'cid': 4,  'label': 'BCS C4\nLONG\nBarclays\n5/5 splits'},
]

def draw(ax, pattern_bars, after_bars, title, outcome_pct):
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
        ax.add_patch(Rectangle((i - W/2, blo), W, bh, facecolor=col,
                               edgecolor='none', alpha=alpha))
    ax.axvline(x=WINDOW - 0.5, color='#f9e2af', linestyle='--', linewidth=1.2, alpha=0.8)
    entry = pattern_bars[-1]['close']
    exit_p = after_bars[-1]['close']
    ax.axhline(y=entry, color='#89b4fa', linestyle=':', linewidth=0.8, alpha=0.6)
    ymax = max(b['high'] for b in all_b)
    ax.axvspan(WINDOW - 0.5, len(all_b) - 0.5, color='#585b70', alpha=0.15)
    arrow_col = GREEN if outcome_pct > 0 else RED
    ax.annotate('', xy=(len(all_b) - 1, exit_p), xytext=(WINDOW - 1, entry),
                arrowprops=dict(arrowstyle='->', color=arrow_col, lw=1.8, alpha=0.9))
    ax.autoscale_view()
    ax.set_xlim(-0.5, len(all_b) - 0.5)
    ax.set_facecolor('#1e1e2e')
    ax.tick_params(colors='#585b70', labelsize=7)
    for s in ax.spines.values():
        s.set_color('#585b70')
    ax.grid(True, alpha=0.1, color='#585b70')
    t_col = GREEN if outcome_pct > 0 else RED
    ax.set_title(title + f'\n{outcome_pct:+.2f}%', color=t_col, fontsize=9, fontweight='bold')
    ax.text(WINDOW/2 - 0.5, ymax, 'PATTERN', ha='center', va='top',
            color='#89b4fa', fontsize=8, fontweight='bold')
    ax.text(WINDOW + LOOKAHEAD/2 - 0.5, ymax, 'AFTER →', ha='center', va='top',
            color='#f9e2af', fontsize=8, fontweight='bold')

def main():
    fig, axes = plt.subplots(4, 6, figsize=(26, 16))
    fig.patch.set_facecolor('#1e1e2e')

    for row_idx, w in enumerate(WINNERS):
        sym = w['sym']
        cid = w['cid']
        print(f'Processing {sym} C{cid}...')
        bars = load_csv(f'/Users/mariashchekanenko/claude-trading-tv/data/ohlcv/{sym}.csv')
        X, outs_pct, idxs, _ = extract_with_idx(bars)
        Xs = (X - X.mean(0)) / (X.std(0) + 1e-8)
        labels = kmeans(Xs, K)
        cluster_idxs = [idxs[i] for i in range(len(labels)) if labels[i] == cid]
        print(f'  Found {len(cluster_idxs)} members')

        if len(cluster_idxs) >= 6:
            step = len(cluster_idxs) // 6
            examples = [cluster_idxs[i * step] for i in range(6)]
        else:
            examples = cluster_idxs

        for col, idx in enumerate(examples):
            ax = axes[row_idx][col]
            pattern = bars[idx:idx + WINDOW]
            after = bars[idx + WINDOW:idx + WINDOW + LOOKAHEAD]
            if len(after) < LOOKAHEAD:
                ax.set_visible(False); continue
            entry = pattern[-1]['close']
            exit_p = after[-1]['close']
            outcome = (exit_p - entry) / entry * 100
            date_str = pattern[0]['time'].strftime('%Y-%m-%d %H:%M')
            title = f'{date_str}\n${entry:.2f} → ${exit_p:.2f}'
            draw(ax, pattern, after, title, outcome)

        axes[row_idx][0].text(-0.25, 0.5, w['label'],
                              transform=axes[row_idx][0].transAxes,
                              ha='right', va='center', color='#a6e3a1',
                              fontsize=13, fontweight='bold')

    fig.suptitle('Multi-Split ROBUST Patterns (passed all 5 time splits)\n'
                 'UK/EU bank stocks — long-biased small edges',
                 color='#cdd6f4', fontsize=16, fontweight='bold', y=0.998)
    plt.subplots_adjust(left=0.08, hspace=0.55, wspace=0.25, top=0.95)
    out = '/Users/mariashchekanenko/claude-trading-tv/charts/robust-v7-winners.png'
    fig.savefig(out, dpi=120, bbox_inches='tight', facecolor='#1e1e2e')
    plt.close(fig)
    print(f'Saved {out}')

if __name__ == '__main__':
    main()
