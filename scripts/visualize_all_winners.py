#!/usr/bin/env python3
"""
Show pattern + aftermath for all 4 Bonferroni-validated edges:
  Row 1: EURGBP C0 LONG
  Row 2: EURGBP C8 SHORT
  Row 3: XRPUSD C1 LONG
  Row 4: ADAUSD C9 LONG

6 real examples per pattern, evenly spaced in time.
"""
import sys, os
sys.path.insert(0, '/Users/mariashchekanenko/claude-trading-tv/scripts')
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from datetime import datetime

from statistical_validation_v2 import load_csv, kmeans, WINDOW, LOOKAHEAD

# ─── Reuse extraction functions ───
def extract_v2_with_indices(bars):
    """v2 feature extraction with original indices kept."""
    from statistical_validation_v2 import enhanced_features, precompute_indicators
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

def extract_v5_with_indices(bars, asset):
    """v5 crypto feature extraction."""
    from statistical_validation_v5_crypto import extract_v5
    # Reconstruct to get indices
    from statistical_validation_v2 import precompute_indicators
    from statistical_validation_v5_crypto import load_funding, funding_at, ASSET_FUNDING
    funding_key = ASSET_FUNDING.get(asset)
    funding = load_funding(funding_key)
    ind = precompute_indicators(bars)
    feats, outs, idxs = [], [], []
    for i in range(len(bars) - WINDOW - LOOKAHEAD):
        window = bars[i:i + WINDOW]
        base_p = window[0]['open']
        if base_p == 0:
            continue
        vec = []
        for b in window:
            vec.extend([(b['open']-base_p)/base_p*100, (b['high']-base_p)/base_p*100,
                        (b['low']-base_p)/base_p*100, (b['close']-base_p)/base_p*100])
        for j in range(WINDOW):
            bi = i + j
            v = ind['vols'][bi]
            vm = ind['vol_ma20'][bi]
            vec.append(min(v/vm if vm else 1, 10))
        end = i + WINDOW - 1
        last_close = ind['closes'][end]
        rsi = ind['rsi'][end]
        if np.isnan(rsi): continue
        vec.append(rsi)
        e20 = ind['ema20'][end]
        if np.isnan(e20) or e20 == 0: continue
        vec.append((last_close - e20) / e20 * 100)
        e50 = ind['ema50'][end]
        if np.isnan(e50) or e50 == 0: continue
        vec.append((last_close - e50) / e50 * 100)
        atr = ind['atr'][end]
        if np.isnan(atr) or atr == 0: continue
        vec.append((ind['highs'][end] - ind['lows'][end]) / atr)
        t = ind['times'][end]
        vec.append(t.hour)
        vec.append(t.weekday())
        vec.append(1 if t.weekday() >= 5 else 0)
        vec.append((e20 - e50) / e50 * 100)
        ts = int(bars[end]['time'].timestamp())
        current, window_rates = funding_at(ts, funding, lookback_n=9)
        if current is None:
            continue
        vec.append(current * 100)
        vec.append(float(window_rates.mean()) * 100)
        vec.append(abs(current) * 100)
        prev, _ = funding_at(ts - 24 * 3600, funding)
        vec.append(0 if prev is None else (current - prev) * 100)
        if any(np.isnan(vec)) or any(np.isinf(vec)):
            continue
        feats.append(vec)
        entry = bars[end]['close']
        exit_p = bars[end + LOOKAHEAD]['close']
        outs.append(1 if exit_p > entry else 0)
        idxs.append(i)
    return np.array(feats), np.array(outs), idxs

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

def get_cluster_examples(bars, indices_in_cluster, n_examples=6):
    """Pick N evenly-spaced examples from a cluster's time-ordered indices."""
    if len(indices_in_cluster) <= n_examples:
        return indices_in_cluster
    step = len(indices_in_cluster) // n_examples
    return [indices_in_cluster[i * step] for i in range(n_examples)]

def main():
    WINNERS = [
        {'sym': 'EURGBP', 'cid': 0, 'method': 'v2', 'K': 20, 'dir': 'LONG',
         'label': 'EURGBP C0\nLONG\nv2 K=20\nWR 56%\np=5.1e-6', 'color': '#a6e3a1'},
        {'sym': 'EURGBP', 'cid': 8, 'method': 'v2', 'K': 20, 'dir': 'SHORT',
         'label': 'EURGBP C8\nSHORT\nv2 K=20\nWR 42%\np=2.1e-5', 'color': '#f38ba8'},
        {'sym': 'XRPUSD', 'cid': 1, 'method': 'v5', 'K': 15, 'dir': 'LONG',
         'label': 'XRPUSD C1\nLONG\nv5 K=15\nWR 73%\np=8.9e-7', 'color': '#a6e3a1'},
        {'sym': 'ADAUSD', 'cid': 9, 'method': 'v5', 'K': 15, 'dir': 'LONG',
         'label': 'ADAUSD C9\nLONG (funding)\nv5 K=15\nWR 56%\np=5.5e-5', 'color': '#a6e3a1'},
    ]

    fig, axes = plt.subplots(4, 6, figsize=(26, 16))
    fig.patch.set_facecolor('#1e1e2e')

    for row_idx, w in enumerate(WINNERS):
        print(f'Processing {w["sym"]} C{w["cid"]}...')
        bars = load_csv(f'/Users/mariashchekanenko/claude-trading-tv/data/ohlcv/{w["sym"]}.csv')
        if w['method'] == 'v2':
            X, outs, idxs = extract_v2_with_indices(bars)
        else:
            X, outs, idxs = extract_v5_with_indices(bars, w['sym'])
        Xs = (X - X.mean(0)) / (X.std(0) + 1e-8)
        labels = kmeans(Xs, w['K'])
        cluster_indices = [idxs[i] for i in range(len(labels)) if labels[i] == w['cid']]
        print(f'  Found {len(cluster_indices)} members')
        examples = get_cluster_examples(bars, cluster_indices, 6)

        for col, idx in enumerate(examples):
            ax = axes[row_idx][col]
            pattern = bars[idx:idx + WINDOW]
            after = bars[idx + WINDOW:idx + WINDOW + LOOKAHEAD]
            if len(after) < LOOKAHEAD:
                ax.set_visible(False)
                continue
            entry = pattern[-1]['close']
            exit_p = after[-1]['close']
            outcome = (exit_p - entry) / entry * 100
            date_str = pattern[0]['time'].strftime('%Y-%m-%d %H:%M')
            decimals = 5 if w['sym'] in ['EURGBP'] else 4
            title = f'{date_str}\n{entry:.{decimals}f} → {exit_p:.{decimals}f}'
            draw(ax, pattern, after, title, outcome)

        axes[row_idx][0].text(-0.28, 0.5, w['label'],
                              transform=axes[row_idx][0].transAxes,
                              ha='right', va='center', color=w['color'],
                              fontsize=12, fontweight='bold')

    fig.suptitle('All 4 Bonferroni-Validated Patterns — Pattern (bright) + Aftermath (dimmed)\n'
                 '3 strategies: forex mean-reversion + crypto oversold + crypto funding-squeeze',
                 color='#cdd6f4', fontsize=16, fontweight='bold', y=0.998)
    plt.subplots_adjust(left=0.08, hspace=0.6, wspace=0.25, top=0.95)

    out = '/Users/mariashchekanenko/claude-trading-tv/charts/all-winners.png'
    fig.savefig(out, dpi=120, bbox_inches='tight', facecolor='#1e1e2e')
    plt.close(fig)
    print(f'Saved {out}')

if __name__ == '__main__':
    main()
