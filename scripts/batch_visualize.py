#!/usr/bin/env python3
"""
Visualize batch pattern analysis across 74 assets.
Three views:
1. Method success rate per asset class
2. Top symbols across all classes
3. Edge distribution
"""
import json
import os
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

RESULTS = '/Users/mariashchekanenko/claude-trading-tv/data/batch-results.json'
OUT = '/Users/mariashchekanenko/claude-trading-tv/charts/batch-summary.png'

def main():
    data = json.load(open(RESULTS))
    results = data['results']

    # Group by class
    by_class = {}
    for sym, r in results.items():
        cls = r['asset_class']
        by_class.setdefault(cls, []).append((sym, r))

    methods = ['kmeans_full', 'kmeans_shape', 'v_reversal', 'inverted_v']
    method_labels = ['K-Means\nFULL', 'K-Means\nSHAPE', 'V-reversal\ntemplate', 'Inv-V\ntemplate']
    method_colors = ['#89b4fa', '#a6e3a1', '#f9e2af', '#cba6f7']

    fig = plt.figure(figsize=(20, 14))
    fig.patch.set_facecolor('#1e1e2e')

    # ─── Panel 1: Success rate per method per class ───
    ax1 = plt.subplot(2, 2, 1)
    ax1.set_facecolor('#1e1e2e')
    classes = list(by_class.keys())
    x = np.arange(len(classes))
    width = 0.2

    for i, m in enumerate(methods):
        rates = []
        for cls in classes:
            items = by_class[cls]
            count = 0
            for sym, r in items:
                if m in ('kmeans_full', 'kmeans_shape'):
                    if r.get(m) and r[m]['top']:
                        count += 1
                else:
                    if r.get(m):
                        count += 1
            rates.append(count / len(items) * 100)
        ax1.bar(x + i * width, rates, width, label=method_labels[i].replace('\n', ' '),
                color=method_colors[i], edgecolor='#cdd6f4', linewidth=0.5)

    ax1.set_xticks(x + width * 1.5)
    ax1.set_xticklabels([c.upper() for c in classes], color='#cdd6f4')
    ax1.set_ylabel('% of symbols with significant edge', color='#cdd6f4', fontsize=11)
    ax1.set_title('Method Reliability per Asset Class\n(% of symbols where method finds a 95%-significant edge)',
                  color='#cdd6f4', fontsize=12, fontweight='bold')
    ax1.tick_params(colors='#cdd6f4', labelsize=9)
    ax1.legend(facecolor='#1e1e2e', edgecolor='#585b70', labelcolor='#cdd6f4', fontsize=9)
    ax1.grid(True, alpha=0.15, color='#585b70', axis='y')
    for s in ax1.spines.values():
        s.set_color('#585b70')

    # ─── Panel 2: Avg edge size per method per class ───
    ax2 = plt.subplot(2, 2, 2)
    ax2.set_facecolor('#1e1e2e')
    for i, m in enumerate(methods):
        avgs = []
        for cls in classes:
            items = by_class[cls]
            edges = []
            for sym, r in items:
                if m in ('kmeans_full', 'kmeans_shape'):
                    if r.get(m) and r[m]['top']:
                        edges.append(r[m]['top'][0]['best_edge'])
                else:
                    if r.get(m):
                        edges.append(r[m]['best_edge'])
            avgs.append(np.mean(edges) if edges else 0)
        ax2.bar(x + i * width, avgs, width, label=method_labels[i].replace('\n', ' '),
                color=method_colors[i], edgecolor='#cdd6f4', linewidth=0.5)

    ax2.set_xticks(x + width * 1.5)
    ax2.set_xticklabels([c.upper() for c in classes], color='#cdd6f4')
    ax2.set_ylabel('Avg best edge (%) — only significant ones', color='#cdd6f4', fontsize=11)
    ax2.set_title('Average Edge Strength per Method per Class\n(higher = stronger profitable signal)',
                  color='#cdd6f4', fontsize=12, fontweight='bold')
    ax2.axhline(y=50, color='#585b70', linestyle='--', alpha=0.5)
    ax2.tick_params(colors='#cdd6f4', labelsize=9)
    ax2.legend(facecolor='#1e1e2e', edgecolor='#585b70', labelcolor='#cdd6f4', fontsize=9)
    ax2.grid(True, alpha=0.15, color='#585b70', axis='y')
    ax2.set_ylim(40, 80)
    for s in ax2.spines.values():
        s.set_color('#585b70')

    # ─── Panel 3: Top 25 symbols by best edge (any method) ───
    ax3 = plt.subplot(2, 2, 3)
    ax3.set_facecolor('#1e1e2e')
    ranked = []
    for sym, r in results.items():
        best = 0
        best_method = ''
        best_dir = ''
        best_n = 0
        for m in methods:
            if m in ('kmeans_full', 'kmeans_shape'):
                if r.get(m) and r[m]['top']:
                    s = r[m]['top'][0]
                    if s['best_edge'] > best:
                        best = s['best_edge']
                        best_method = m.replace('kmeans_', 'K')
                        best_dir = s['direction']
                        best_n = s['n']
            else:
                if r.get(m) and r[m]['best_edge'] > best:
                    best = r[m]['best_edge']
                    best_method = 'V' if m == 'v_reversal' else 'IV'
                    best_dir = r[m]['direction']
                    best_n = r[m]['n']
        if best > 0:
            ranked.append({
                'sym': sym, 'edge': best, 'method': best_method,
                'dir': best_dir, 'n': best_n,
                'class': r['asset_class'],
            })
    ranked.sort(key=lambda x: -x['edge'])
    top25 = ranked[:25]

    syms = [r['sym'] for r in top25]
    edges = [r['edge'] for r in top25]
    class_color_map = {
        'us_stocks': '#89b4fa', 'eu_stocks': '#a6e3a1',
        'crypto': '#f9e2af', 'forex': '#cba6f7', 'etf_macro': '#fab387',
    }
    colors = [class_color_map.get(r['class'], '#cdd6f4') for r in top25]

    y_pos = np.arange(len(top25))
    bars = ax3.barh(y_pos, edges, color=colors, edgecolor='#cdd6f4', linewidth=0.4)
    ax3.set_yticks(y_pos)
    labels = [f'{r["sym"]:8} {r["dir"]:5} {r["method"]:3} n={r["n"]:3}' for r in top25]
    ax3.set_yticklabels(labels, color='#cdd6f4', fontsize=8, family='monospace')
    ax3.invert_yaxis()
    ax3.set_xlabel('Best edge (%)', color='#cdd6f4', fontsize=11)
    ax3.set_title('Top 25 Symbols Across All Methods\n(color = asset class)',
                  color='#cdd6f4', fontsize=12, fontweight='bold')
    ax3.tick_params(colors='#cdd6f4', labelsize=8)
    ax3.grid(True, alpha=0.15, color='#585b70', axis='x')
    ax3.set_xlim(50, 100)
    for s in ax3.spines.values():
        s.set_color('#585b70')

    # Add edge values at end of bars
    for i, (bar, r) in enumerate(zip(bars, top25)):
        ax3.text(bar.get_width() + 0.5, bar.get_y() + bar.get_height()/2,
                 f'{r["edge"]:.1f}%', va='center', color='#cdd6f4',
                 fontsize=8, fontweight='bold')

    # Class color legend on this panel
    legend_handles = []
    for cls, col in class_color_map.items():
        legend_handles.append(plt.Rectangle((0,0), 1, 1, color=col))
    ax3.legend(legend_handles, list(class_color_map.keys()),
               facecolor='#1e1e2e', edgecolor='#585b70',
               labelcolor='#cdd6f4', fontsize=8, loc='lower right')

    # ─── Panel 4: Edge distribution histogram ───
    ax4 = plt.subplot(2, 2, 4)
    ax4.set_facecolor('#1e1e2e')

    for cls in classes:
        all_edges = []
        for sym, r in by_class[cls]:
            for m in methods:
                if m in ('kmeans_full', 'kmeans_shape'):
                    if r.get(m) and r[m]['top']:
                        all_edges.append(r[m]['top'][0]['best_edge'])
                else:
                    if r.get(m):
                        all_edges.append(r[m]['best_edge'])
        if all_edges:
            color = class_color_map.get(cls, '#cdd6f4')
            ax4.hist(all_edges, bins=15, alpha=0.5, label=cls.upper(),
                     color=color, edgecolor='#cdd6f4', linewidth=0.5)

    ax4.axvline(x=50, color='#585b70', linestyle='--', alpha=0.5, label='coin flip')
    ax4.axvline(x=70, color='#a6e3a1', linestyle='--', alpha=0.5, label='strong edge')
    ax4.set_xlabel('Best edge (%) — all significant clusters across all methods',
                   color='#cdd6f4', fontsize=11)
    ax4.set_ylabel('Count of edges', color='#cdd6f4', fontsize=11)
    ax4.set_title('Distribution of Significant Edges per Asset Class',
                  color='#cdd6f4', fontsize=12, fontweight='bold')
    ax4.tick_params(colors='#cdd6f4', labelsize=9)
    ax4.legend(facecolor='#1e1e2e', edgecolor='#585b70', labelcolor='#cdd6f4', fontsize=9)
    ax4.grid(True, alpha=0.15, color='#585b70', axis='y')
    for s in ax4.spines.values():
        s.set_color('#585b70')

    fig.suptitle('Pattern Detection — Batch Analysis of 74 Assets (1y 1H data)\n'
                 '4 methods × 5 asset classes | only 95%-significant edges shown',
                 color='#cdd6f4', fontsize=15, fontweight='bold', y=0.998)
    plt.tight_layout(rect=[0, 0, 1, 0.97])

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    fig.savefig(OUT, dpi=130, bbox_inches='tight', facecolor='#1e1e2e')
    plt.close(fig)
    print(f'Saved {OUT}')

if __name__ == '__main__':
    main()
