#!/usr/bin/env python3
"""
Pattern Aftermath Visualizer — show the pattern PLUS what happened next.
For each top cluster, plot 4 real examples: 5 pattern candles + 5 aftermath candles.
"""

import csv
import os
import json
import numpy as np
from datetime import datetime
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

CSV_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'nvda-1h-ohlcv.csv')
RESULTS_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'pattern-results.json')
CHART_PATH = os.path.join(os.path.dirname(__file__), '..', 'charts', 'pattern-aftermath.png')

WINDOW = 5
LOOKAHEAD = 5

# ─── Load data ───

def load_bars(path):
    bars = []
    with open(path) as f:
        for r in csv.DictReader(f):
            bars.append({
                'time': datetime.utcfromtimestamp(int(r['timestamp'])),
                'open': float(r['open']),
                'high': float(r['high']),
                'low': float(r['low']),
                'close': float(r['close']),
                'volume': int(float(r['volume'])),
            })
    return bars

# ─── Draw a single pattern + aftermath ───

def draw_pattern(ax, bars_pattern, bars_aftermath, title, win_rate, outcome_pct):
    """Draw 5 pattern candles + 5 aftermath candles with divider."""
    GREEN = '#26a69a'
    RED = '#ef5350'
    W = 0.7

    all_bars = bars_pattern + bars_aftermath

    for i, bar in enumerate(all_bars):
        o, h, l, c = bar['open'], bar['high'], bar['low'], bar['close']
        color = GREEN if c >= o else RED
        # Aftermath dimmed to differentiate
        alpha = 1.0 if i < WINDOW else 0.55

        # Wick
        ax.plot([i, i], [l, h], color=color, linewidth=1.2, alpha=alpha,
                solid_capstyle='butt')
        # Body
        body_lo = min(o, c)
        body_h = abs(c - o) or 0.01
        rect = Rectangle((i - W / 2, body_lo), W, body_h,
                         facecolor=color, edgecolor='none', alpha=alpha)
        ax.add_patch(rect)

    # Divider between pattern and aftermath
    ax.axvline(x=WINDOW - 0.5, color='#f9e2af', linestyle='--',
               linewidth=1.2, alpha=0.8)

    # Entry price line (close of last pattern candle)
    entry = bars_pattern[-1]['close']
    ax.axhline(y=entry, color='#89b4fa', linestyle=':', linewidth=0.8, alpha=0.6)

    # Shade aftermath area
    ymin = min(b['low'] for b in all_bars)
    ymax = max(b['high'] for b in all_bars)
    ax.axvspan(WINDOW - 0.5, len(all_bars) - 0.5,
               color='#585b70', alpha=0.15)

    # Outcome arrow & label
    exit_price = bars_aftermath[-1]['close']
    outcome_color = GREEN if outcome_pct > 0 else RED
    ax.annotate('', xy=(len(all_bars) - 1, exit_price),
                xytext=(WINDOW - 1, entry),
                arrowprops=dict(arrowstyle='->', color=outcome_color,
                                lw=1.5, alpha=0.8))

    ax.autoscale_view()
    ax.set_xlim(-0.5, len(all_bars) - 0.5)

    # Styling
    ax.set_facecolor('#1e1e2e')
    ax.tick_params(colors='#585b70', labelsize=9)
    for spine in ax.spines.values():
        spine.set_color('#585b70')
    ax.grid(True, alpha=0.1, color='#585b70')

    # Title
    title_color = GREEN if outcome_pct > 0 else RED
    ax.set_title(f'{title}\noutcome: {outcome_pct:+.2f}%',
                 color=title_color, fontsize=11, fontweight='bold')

    # Pattern / After labels
    ax.text(WINDOW / 2 - 0.5, ymax, 'PATTERN', ha='center', va='top',
            color='#89b4fa', fontsize=10, fontweight='bold')
    ax.text(WINDOW + LOOKAHEAD / 2 - 0.5, ymax, 'AFTER →', ha='center', va='top',
            color='#f9e2af', fontsize=10, fontweight='bold')


def main():
    bars = load_bars(CSV_PATH)
    print(f'Loaded {len(bars)} bars')

    # Load cluster results
    results = json.load(open(RESULTS_PATH))
    clusters = results['clusters']

    # Pick top clusters to show (most interesting mix)
    # C6 (biggest), C14 (best bull), C7 (best bear), C11 (rally stall),
    # C3 (uptrend), C2 (downtrend)
    to_show = [6, 14, 7, 11, 3, 2]

    # For each cluster, grab 4 real examples from the JSON data
    # (the examples list has time + index info)

    # Re-scan to get indices for each cluster
    # We need to match by entry_price / time
    rows = []
    for cid in to_show:
        cluster = next((c for c in clusters if c['cluster'] == cid), None)
        if not cluster:
            continue

        examples = cluster.get('examples', [])[:4]
        # Find bar indices by matching time
        example_indices = []
        for ex in examples:
            ex_time = ex['time']
            for i, b in enumerate(bars):
                if b['time'].strftime('%Y-%m-%d %H:%M') == ex_time:
                    example_indices.append(i)
                    break

        rows.append({
            'cluster_id': cid,
            'win_rate': cluster['win_rate'],
            'n': cluster['n'],
            'avg_change': cluster['avg_change_pct'],
            'bias': cluster['bias'],
            'indices': example_indices,
        })

    # Plot grid: rows = clusters, cols = 4 examples each
    n_rows = len(rows)
    n_cols = 4
    fig, axes = plt.subplots(n_rows, n_cols, figsize=(28, 4.5 * n_rows))
    fig.patch.set_facecolor('#1e1e2e')

    for row_idx, row in enumerate(rows):
        # Row header (cluster info)
        for col_idx in range(n_cols):
            ax = axes[row_idx][col_idx] if n_rows > 1 else axes[col_idx]

            if col_idx >= len(row['indices']):
                ax.set_visible(False)
                continue

            idx = row['indices'][col_idx]
            if idx + WINDOW + LOOKAHEAD > len(bars):
                ax.set_visible(False)
                continue

            pattern_bars = bars[idx:idx + WINDOW]
            after_bars = bars[idx + WINDOW:idx + WINDOW + LOOKAHEAD]

            entry = pattern_bars[-1]['close']
            exit_p = after_bars[-1]['close']
            outcome_pct = (exit_p - entry) / entry * 100

            date_str = pattern_bars[0]['time'].strftime('%b %d %H:%M')
            title = f"C{row['cluster_id']} | {date_str} | ${entry:.2f}"

            draw_pattern(ax, pattern_bars, after_bars, title,
                         row['win_rate'], outcome_pct)

        # Add row label on the leftmost subplot
        leftmost = axes[row_idx][0] if n_rows > 1 else axes[0]
        bias_color = '#26a69a' if row['bias'] == 'LONG' else '#ef5350' if row['bias'] == 'SHORT' else '#f9e2af'
        leftmost.text(-0.22, 0.5, f"C{row['cluster_id']}\n{row['bias']}\n"
                     f"WR {row['win_rate']}%\nn={row['n']}\navg {row['avg_change']:+.2f}%",
                     transform=leftmost.transAxes, ha='right', va='center',
                     color=bias_color, fontsize=14, fontweight='bold')

    fig.suptitle('Pattern + Aftermath — 5 candles pattern (bright) | 5 candles after (dimmed)',
                 color='#cdd6f4', fontsize=18, fontweight='bold', y=0.997)
    plt.subplots_adjust(left=0.08, hspace=0.55, wspace=0.2, top=0.96)

    os.makedirs(os.path.dirname(CHART_PATH), exist_ok=True)
    fig.savefig(CHART_PATH, dpi=120, bbox_inches='tight', facecolor='#1e1e2e')
    plt.close(fig)
    print(f'Saved {CHART_PATH}')


if __name__ == '__main__':
    main()
