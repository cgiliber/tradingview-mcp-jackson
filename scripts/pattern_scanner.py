#!/usr/bin/env python3
"""
Mathematical Candlestick Pattern Scanner — NVDA 1H
Uses K-Means clustering on normalized OHLCV windows to find repeatable patterns.
"""

import csv
import os
import json
import numpy as np
from datetime import datetime
from collections import defaultdict

CSV_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'nvda-1h-ohlcv.csv')
OUTPUT_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'pattern-results.json')
CHART_PATH = os.path.join(os.path.dirname(__file__), '..', 'charts', 'pattern-clusters.png')

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

# ─── Feature extraction ───

def extract_windows(bars, window_size=5, lookahead=5):
    """
    Extract normalized feature vectors for each sliding window.
    Normalization: percentage change from first candle's open.
    """
    features = []
    outcomes = []
    meta = []

    for i in range(len(bars) - window_size - lookahead):
        window = bars[i:i + window_size]
        future = bars[i + window_size:i + window_size + lookahead]

        base_price = window[0]['open']
        if base_price == 0:
            continue

        # Normalize OHLC as % change from base
        vec = []
        for b in window:
            vec.extend([
                (b['open'] - base_price) / base_price * 100,
                (b['high'] - base_price) / base_price * 100,
                (b['low'] - base_price) / base_price * 100,
                (b['close'] - base_price) / base_price * 100,
            ])

        # Add volume profile (normalized to window average)
        vols = [b['volume'] for b in window]
        avg_vol = np.mean(vols) if np.mean(vols) > 0 else 1
        for v in vols:
            vec.append(v / avg_vol)

        features.append(vec)

        # Outcome: % change from last candle's close to future closes
        entry_price = window[-1]['close']
        future_changes = []
        max_up = 0
        max_down = 0
        for f in future:
            chg = (f['close'] - entry_price) / entry_price * 100
            hi = (f['high'] - entry_price) / entry_price * 100
            lo = (f['low'] - entry_price) / entry_price * 100
            future_changes.append(chg)
            max_up = max(max_up, hi)
            max_down = min(max_down, lo)

        outcomes.append({
            'changes': future_changes,
            'final_change': future_changes[-1] if future_changes else 0,
            'max_up': max_up,
            'max_down': max_down,
            'direction': 'UP' if future_changes[-1] > 0 else 'DOWN',
        })

        meta.append({
            'index': i,
            'time': window[0]['time'].strftime('%Y-%m-%d %H:%M'),
            'entry_price': round(entry_price, 2),
        })

    return np.array(features), outcomes, meta


# ─── K-Means (pure numpy, no sklearn needed) ───

def kmeans(X, k=15, max_iter=100, seed=42):
    """Simple K-Means clustering."""
    rng = np.random.RandomState(seed)
    n, d = X.shape

    # Initialize centroids with k-means++
    centroids = np.empty((k, d))
    centroids[0] = X[rng.randint(n)]
    for j in range(1, k):
        dists = np.min([np.sum((X - centroids[c]) ** 2, axis=1) for c in range(j)], axis=0)
        probs = dists / dists.sum()
        centroids[j] = X[rng.choice(n, p=probs)]

    labels = np.zeros(n, dtype=int)
    for iteration in range(max_iter):
        # Assign
        dists = np.array([np.sum((X - c) ** 2, axis=1) for c in centroids])
        new_labels = np.argmin(dists, axis=0)

        if np.array_equal(new_labels, labels):
            break
        labels = new_labels

        # Update
        for j in range(k):
            mask = labels == j
            if mask.sum() > 0:
                centroids[j] = X[mask].mean(axis=0)

    return labels, centroids


# ─── Cross-correlation template matching ───

def find_v_reversals(bars, template_len=5, threshold=0.8):
    """Find V-shape reversal patterns using cross-correlation."""
    # Template: price drops steadily then reverses up (V-shape)
    t = np.array([-2, -3, -4, -3, -1])  # normalized V
    t = (t - t.mean()) / (t.std() + 1e-8)

    matches = []
    for i in range(len(bars) - template_len - 5):
        window = bars[i:i + template_len]
        closes = np.array([b['close'] for b in window])
        c = (closes - closes.mean()) / (closes.std() + 1e-8)

        corr = np.dot(t, c) / template_len
        if corr > threshold:
            # Measure outcome
            entry = window[-1]['close']
            future = bars[i + template_len:i + template_len + 5]
            if len(future) >= 5:
                final_chg = (future[-1]['close'] - entry) / entry * 100
                matches.append({
                    'index': i,
                    'time': window[0]['time'].strftime('%Y-%m-%d %H:%M'),
                    'correlation': round(float(corr), 3),
                    'entry_price': round(entry, 2),
                    'outcome_5bar_pct': round(final_chg, 3),
                    'direction': 'UP' if final_chg > 0 else 'DOWN',
                })

    return matches


def find_inverted_v(bars, template_len=5, threshold=0.8):
    """Find inverted-V (top reversal) patterns."""
    t = np.array([1, 2, 3, 2, 0])  # inverted V
    t = (t - t.mean()) / (t.std() + 1e-8)

    matches = []
    for i in range(len(bars) - template_len - 5):
        window = bars[i:i + template_len]
        closes = np.array([b['close'] for b in window])
        c = (closes - closes.mean()) / (closes.std() + 1e-8)

        corr = np.dot(t, c) / template_len
        if corr > threshold:
            entry = window[-1]['close']
            future = bars[i + template_len:i + template_len + 5]
            if len(future) >= 5:
                final_chg = (future[-1]['close'] - entry) / entry * 100
                matches.append({
                    'index': i,
                    'time': window[0]['time'].strftime('%Y-%m-%d %H:%M'),
                    'correlation': round(float(corr), 3),
                    'entry_price': round(entry, 2),
                    'outcome_5bar_pct': round(final_chg, 3),
                    'direction': 'UP' if final_chg > 0 else 'DOWN',
                })

    return matches


# ─── Visualization ───

def plot_clusters(features, labels, outcomes, centroids, meta):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt

    k = len(centroids)
    window_size = 5

    # Compute stats per cluster
    cluster_stats = []
    for j in range(k):
        mask = labels == j
        n = mask.sum()
        if n == 0:
            continue
        cluster_outcomes = [outcomes[i] for i in range(len(outcomes)) if mask[i]]
        wins = sum(1 for o in cluster_outcomes if o['direction'] == 'UP')
        avg_change = np.mean([o['final_change'] for o in cluster_outcomes])
        avg_max_up = np.mean([o['max_up'] for o in cluster_outcomes])
        avg_max_down = np.mean([o['max_down'] for o in cluster_outcomes])
        cluster_stats.append({
            'cluster': j, 'n': n, 'win_rate': wins / n * 100,
            'avg_change': avg_change, 'avg_max_up': avg_max_up,
            'avg_max_down': avg_max_down, 'centroid': centroids[j],
        })

    # Sort by win rate
    cluster_stats.sort(key=lambda x: -x['win_rate'])

    # Plot top 5 bullish + top 5 bearish cluster centroids
    top_bull = cluster_stats[:5]
    top_bear = cluster_stats[-5:]

    fig, axes = plt.subplots(2, 5, figsize=(24, 8))
    fig.patch.set_facecolor('#1e1e2e')

    for idx, (row_label, clusters) in enumerate([('BULLISH', top_bull), ('BEARISH', top_bear)]):
        for col, cs in enumerate(clusters):
            ax = axes[idx][col]
            ax.set_facecolor('#1e1e2e')
            centroid = cs['centroid']

            # Extract OHLC from centroid (first 4*window_size values)
            for c_idx in range(window_size):
                o = centroid[c_idx * 4]
                h = centroid[c_idx * 4 + 1]
                l = centroid[c_idx * 4 + 2]
                cl = centroid[c_idx * 4 + 3]
                color = '#26a69a' if cl >= o else '#ef5350'
                ax.plot([c_idx, c_idx], [l, h], color=color, linewidth=1.5)
                body_lo = min(o, cl)
                body_hi = max(o, cl)
                from matplotlib.patches import Rectangle
                rect = Rectangle((c_idx - 0.35, body_lo), 0.7,
                                 max(body_hi - body_lo, 0.01),
                                 facecolor=color, edgecolor='none')
                ax.add_patch(rect)
                ax.autoscale_view()

            wr = cs['win_rate']
            title_color = '#26a69a' if wr > 50 else '#ef5350'
            ax.set_title(f'C{cs["cluster"]} | WR:{wr:.0f}% | n={cs["n"]}\n'
                         f'avg:{cs["avg_change"]:+.2f}%',
                         color=title_color, fontsize=9, fontweight='bold')
            ax.tick_params(colors='#585b70', labelsize=7)
            for spine in ax.spines.values():
                spine.set_color('#585b70')
            ax.set_ylabel('% from base' if col == 0 else '', color='#cdd6f4', fontsize=8)

    fig.suptitle('Pattern Clusters — Top 5 Bullish / Top 5 Bearish',
                 color='#cdd6f4', fontsize=14, fontweight='bold')
    plt.tight_layout()
    os.makedirs(os.path.dirname(CHART_PATH), exist_ok=True)
    fig.savefig(CHART_PATH, dpi=150, bbox_inches='tight', facecolor='#1e1e2e')
    plt.close(fig)
    print(f'Cluster chart saved to {CHART_PATH}')

    return cluster_stats


# ─── Main ───

def main():
    bars = load_bars(CSV_PATH)
    print(f'Loaded {len(bars)} bars | {bars[0]["time"]} to {bars[-1]["time"]}')

    WINDOW = 5
    LOOKAHEAD = 5
    K = 15

    # Extract features
    features, outcomes, meta = extract_windows(bars, WINDOW, LOOKAHEAD)
    print(f'Extracted {len(features)} windows | Feature vector size: {features.shape[1]}')

    # Standardize features
    mean = features.mean(axis=0)
    std = features.std(axis=0)
    std[std == 0] = 1
    X = (features - mean) / std

    # K-Means clustering
    print(f'\nRunning K-Means with K={K}...')
    labels, centroids = kmeans(X, k=K)

    # De-standardize centroids for plotting
    centroids_raw = centroids * std + mean

    # Analyze clusters
    print(f'\n{"="*90}')
    print(f'K-MEANS PATTERN CLUSTERS — NVDA 1H | {WINDOW}-candle windows | K={K}')
    print(f'{"="*90}')
    print(f'{"Cluster":>8} {"N":>5} {"WinRate":>8} {"AvgChg":>8} {"MaxUp":>8} {"MaxDn":>8} {"Bias":>7}')
    print('-' * 90)

    cluster_results = []
    for j in range(K):
        mask = labels == j
        n = mask.sum()
        if n == 0:
            continue
        cluster_outcomes = [outcomes[i] for i in range(len(outcomes)) if mask[i]]
        cluster_meta = [meta[i] for i in range(len(meta)) if mask[i]]
        wins = sum(1 for o in cluster_outcomes if o['direction'] == 'UP')
        wr = wins / n * 100
        avg_chg = np.mean([o['final_change'] for o in cluster_outcomes])
        avg_up = np.mean([o['max_up'] for o in cluster_outcomes])
        avg_dn = np.mean([o['max_down'] for o in cluster_outcomes])
        bias = 'LONG' if wr > 55 else 'SHORT' if wr < 45 else 'NEUTRAL'

        cluster_results.append({
            'cluster': j, 'n': int(n), 'win_rate': round(wr, 1),
            'avg_change_pct': round(float(avg_chg), 3),
            'avg_max_up_pct': round(float(avg_up), 3),
            'avg_max_down_pct': round(float(avg_dn), 3),
            'bias': bias,
            'examples': cluster_meta[:5],
        })

        print(f'  C{j:>2}     {n:>4}   {wr:>5.1f}%  {avg_chg:>+6.3f}%  {avg_up:>+6.3f}%  '
              f'{avg_dn:>+6.3f}%   {bias}')

    cluster_results.sort(key=lambda x: -x['win_rate'])

    # Top bullish
    print(f'\n─── TOP BULLISH CLUSTERS ───')
    for r in cluster_results[:5]:
        print(f'  Cluster {r["cluster"]}: {r["win_rate"]}% win rate, n={r["n"]}, '
              f'avg move: {r["avg_change_pct"]:+.3f}%')
        for ex in r['examples'][:3]:
            print(f'    -> {ex["time"]} @ ${ex["entry_price"]}')

    # Top bearish
    print(f'\n─── TOP BEARISH CLUSTERS ───')
    for r in cluster_results[-5:]:
        print(f'  Cluster {r["cluster"]}: {r["win_rate"]}% win rate, n={r["n"]}, '
              f'avg move: {r["avg_change_pct"]:+.3f}%')
        for ex in r['examples'][:3]:
            print(f'    -> {ex["time"]} @ ${ex["entry_price"]}')

    # Cross-correlation: V-reversals
    print(f'\n─── V-REVERSAL PATTERN MATCHES (correlation > 0.8) ───')
    v_matches = find_v_reversals(bars, template_len=5, threshold=0.8)
    if v_matches:
        v_wins = sum(1 for m in v_matches if m['direction'] == 'UP')
        print(f'Found {len(v_matches)} V-reversals | Win rate: {v_wins/len(v_matches)*100:.1f}%')
        for m in v_matches[:5]:
            print(f'  {m["time"]} @ ${m["entry_price"]} | corr={m["correlation"]} | '
                  f'outcome: {m["outcome_5bar_pct"]:+.3f}% ({m["direction"]})')
    else:
        print('No V-reversal matches found at threshold 0.8, trying 0.7...')
        v_matches = find_v_reversals(bars, template_len=5, threshold=0.7)
        if v_matches:
            v_wins = sum(1 for m in v_matches if m['direction'] == 'UP')
            print(f'Found {len(v_matches)} V-reversals | Win rate: {v_wins/len(v_matches)*100:.1f}%')
            for m in v_matches[:5]:
                print(f'  {m["time"]} @ ${m["entry_price"]} | corr={m["correlation"]} | '
                      f'outcome: {m["outcome_5bar_pct"]:+.3f}% ({m["direction"]})')

    # Inverted-V (tops)
    print(f'\n─── INVERTED-V (TOP REVERSAL) MATCHES ───')
    iv_matches = find_inverted_v(bars, template_len=5, threshold=0.8)
    if not iv_matches:
        iv_matches = find_inverted_v(bars, template_len=5, threshold=0.7)
    if iv_matches:
        iv_wins = sum(1 for m in iv_matches if m['direction'] == 'DOWN')
        print(f'Found {len(iv_matches)} inv-V tops | Sell win rate: {iv_wins/len(iv_matches)*100:.1f}%')
        for m in iv_matches[:5]:
            print(f'  {m["time"]} @ ${m["entry_price"]} | corr={m["correlation"]} | '
                  f'outcome: {m["outcome_5bar_pct"]:+.3f}% ({m["direction"]})')
    else:
        print('No inverted-V matches found')

    # Plot clusters
    cluster_stats = plot_clusters(features, labels, outcomes, centroids_raw, meta)

    # Save results
    output = {
        'scan_date': datetime.now().strftime('%Y-%m-%d %H:%M'),
        'params': {'window': WINDOW, 'lookahead': LOOKAHEAD, 'k_clusters': K},
        'total_bars': len(bars),
        'total_windows': len(features),
        'clusters': cluster_results,
        'v_reversals': v_matches[:10] if v_matches else [],
        'inverted_v': iv_matches[:10] if iv_matches else [],
    }
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, 'w') as f:
        json.dump(output, f, indent=2, default=str)
    print(f'\nFull results saved to {OUTPUT_PATH}')


if __name__ == '__main__':
    main()
