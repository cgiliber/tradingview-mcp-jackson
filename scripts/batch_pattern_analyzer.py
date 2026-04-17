#!/usr/bin/env python3
"""
Batch Pattern Analyzer — run 4 methods on all downloaded assets,
group results by asset class, find the best patterns per asset.

Methods:
1. K-Means FULL K=30 (OHLC % + volume normalized)
2. K-Means SHAPE K=30 (body/wick ratios + momentum)
3. V-reversal template match
4. Inverted-V template match
"""
import csv
import os
import json
import numpy as np
from datetime import datetime
from collections import defaultdict

OHLCV_DIR = '/Users/mariashchekanenko/claude-trading-tv/data/ohlcv'
OUT_PATH = '/Users/mariashchekanenko/claude-trading-tv/data/batch-results.json'
WINDOW = 5
LOOKAHEAD = 5

# ─── Features ───
def full_features(window):
    base = window[0]['open']
    if base == 0:
        return None
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
        prev = closes[i-1]
        if prev == 0:
            vec.append(0)
        else:
            vec.append((closes[i]-prev)/prev*100)
    return vec

def load_csv(path):
    bars = []
    with open(path) as f:
        for r in csv.DictReader(f):
            try:
                bars.append({
                    'open': float(r['open']), 'high': float(r['high']),
                    'low': float(r['low']), 'close': float(r['close']),
                    'volume': int(float(r['volume'])),
                })
            except (ValueError, KeyError):
                continue
    return bars

def extract(bars, feat_fn):
    feats, outs = [], []
    for i in range(len(bars) - WINDOW - LOOKAHEAD):
        w = bars[i:i+WINDOW]
        fut = bars[i+WINDOW:i+WINDOW+LOOKAHEAD]
        v = feat_fn(w)
        if v is None or any(np.isnan(v)) or any(np.isinf(v)):
            continue
        feats.append(v)
        entry = w[-1]['close']
        exit_p = fut[-1]['close']
        if entry == 0:
            outs.append({'change': 0, 'direction': 'UP'})
        else:
            chg = (exit_p - entry) / entry * 100
            outs.append({'change': chg, 'direction': 'UP' if chg > 0 else 'DOWN'})
    return np.array(feats), outs

def kmeans(X, k, max_iter=80, seed=42):
    rng = np.random.RandomState(seed)
    n = X.shape[0]
    if n < k:
        return None
    cent = np.empty((k, X.shape[1]))
    cent[0] = X[rng.randint(n)]
    for j in range(1, k):
        d = np.min([np.sum((X-cent[c])**2, axis=1) for c in range(j)], axis=0)
        total = d.sum()
        if total == 0:
            return None
        cent[j] = X[rng.choice(n, p=d/total)]
    labels = np.zeros(n, dtype=int)
    for _ in range(max_iter):
        d = np.array([np.sum((X-c)**2, axis=1) for c in cent])
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
    """Return significant clusters with 95% CI."""
    stats = []
    for j in set(labels):
        m = labels == j
        n = int(m.sum())
        if n < min_n:
            continue
        co = [outs[i] for i in range(len(outs)) if m[i]]
        wr_up = sum(1 for o in co if o['direction'] == 'UP') / n * 100
        best_edge = max(wr_up, 100 - wr_up)
        p = best_edge / 100
        ci_half = 1.96 * np.sqrt(p*(1-p)/n) * 100
        lower = best_edge - ci_half
        avg = np.mean([o['change'] for o in co])
        stats.append({
            'cid': int(j), 'n': n, 'wr_up': round(wr_up, 1),
            'best_edge': round(best_edge, 1), 'ci_half': round(ci_half, 1),
            'lower_bound': round(lower, 1), 'significant': lower > 50,
            'avg_move': round(avg, 3),
            'direction': 'LONG' if wr_up > 50 else 'SHORT',
        })
    return stats

def template_match(bars, template, threshold):
    t = np.array(template)
    t = (t - t.mean()) / (t.std() + 1e-8)
    matches = []
    for i in range(len(bars) - WINDOW - LOOKAHEAD):
        window = bars[i:i+WINDOW]
        closes = np.array([b['close'] for b in window])
        if closes.std() == 0:
            continue
        c = (closes - closes.mean()) / (closes.std() + 1e-8)
        corr = np.dot(t, c) / WINDOW
        if corr > threshold:
            entry = window[-1]['close']
            fut = bars[i+WINDOW:i+WINDOW+LOOKAHEAD]
            if entry > 0 and len(fut) >= LOOKAHEAD:
                chg = (fut[-1]['close'] - entry) / entry * 100
                matches.append({'change': chg, 'direction': 'UP' if chg > 0 else 'DOWN'})
    if len(matches) < 10:
        return None
    n = len(matches)
    wr_up = sum(1 for m in matches if m['direction'] == 'UP') / n * 100
    best_edge = max(wr_up, 100 - wr_up)
    p = best_edge / 100
    ci_half = 1.96 * np.sqrt(p*(1-p)/n) * 100
    lower = best_edge - ci_half
    avg = np.mean([m['change'] for m in matches])
    return {
        'n': n, 'wr_up': round(wr_up, 1), 'best_edge': round(best_edge, 1),
        'ci_half': round(ci_half, 1), 'lower_bound': round(lower, 1),
        'significant': lower > 50, 'avg_move': round(avg, 3),
        'direction': 'LONG' if wr_up > 50 else 'SHORT',
    }

def analyze_symbol(path, asset_class):
    bars = load_csv(path)
    if len(bars) < 100:
        return None

    X_full, outs = extract(bars, full_features)
    X_shape, _ = extract(bars, shape_features)
    if len(X_full) < 30:
        return None

    # Standardize
    X_full_s = (X_full - X_full.mean(0)) / (X_full.std(0) + 1e-8)
    X_shape_s = (X_shape - X_shape.mean(0)) / (X_shape.std(0) + 1e-8)

    # Run all 4 methods
    K = 30
    result = {
        'bars': len(bars),
        'windows': len(outs),
        'asset_class': asset_class,
    }

    # Method 1: K-Means FULL K=30
    lab_full = kmeans(X_full_s, K)
    if lab_full is not None:
        stats = cluster_stats(lab_full, outs)
        sig = [s for s in stats if s['significant']]
        sig.sort(key=lambda s: -s['lower_bound'])
        result['kmeans_full'] = {
            'total_clusters': len(stats),
            'significant': len(sig),
            'top': sig[:3],
        }

    # Method 2: K-Means SHAPE K=30
    lab_shape = kmeans(X_shape_s, K)
    if lab_shape is not None:
        stats = cluster_stats(lab_shape, outs)
        sig = [s for s in stats if s['significant']]
        sig.sort(key=lambda s: -s['lower_bound'])
        result['kmeans_shape'] = {
            'total_clusters': len(stats),
            'significant': len(sig),
            'top': sig[:3],
        }

    # Method 3: V-reversal template
    v_template = [-2, -3, -4, -3, -1]
    best_v = None
    for thr in [0.6, 0.7, 0.8]:
        r = template_match(bars, v_template, thr)
        if r and r['significant']:
            if best_v is None or r['lower_bound'] > best_v['lower_bound']:
                best_v = {'threshold': thr, **r}
    result['v_reversal'] = best_v

    # Method 4: Inverted-V template
    iv_template = [1, 2, 3, 2, 0]
    best_iv = None
    for thr in [0.6, 0.7, 0.8]:
        r = template_match(bars, iv_template, thr)
        if r and r['significant']:
            if best_iv is None or r['lower_bound'] > best_iv['lower_bound']:
                best_iv = {'threshold': thr, **r}
    result['inverted_v'] = best_iv

    return result

def main():
    # Load manifest
    manifest = json.load(open(os.path.join(OHLCV_DIR, '_manifest.json')))
    asset_classes = {r['symbol']: r.get('asset_class') for r in manifest['results']}

    # Find all CSV files
    files = [f for f in os.listdir(OHLCV_DIR) if f.endswith('.csv')]
    print(f'Analyzing {len(files)} symbols...\n')

    all_results = {}
    for i, fname in enumerate(sorted(files), 1):
        sym = fname.replace('.csv', '')
        cls = asset_classes.get(sym, 'unknown')
        path = os.path.join(OHLCV_DIR, fname)
        try:
            res = analyze_symbol(path, cls)
            if res is None:
                print(f'  [{i}/{len(files)}] {sym:10} SKIPPED (insufficient data)')
                continue
            all_results[sym] = res

            # Brief per-symbol summary
            sigs = []
            if res.get('kmeans_full') and res['kmeans_full']['top']:
                s = res['kmeans_full']['top'][0]
                sigs.append(f'F:{s["best_edge"]}%({s["direction"][0]},n={s["n"]})')
            if res.get('kmeans_shape') and res['kmeans_shape']['top']:
                s = res['kmeans_shape']['top'][0]
                sigs.append(f'S:{s["best_edge"]}%({s["direction"][0]},n={s["n"]})')
            if res.get('v_reversal'):
                sigs.append(f'V:{res["v_reversal"]["best_edge"]}%')
            if res.get('inverted_v'):
                sigs.append(f'IV:{res["inverted_v"]["best_edge"]}%')
            sig_str = ' | '.join(sigs) if sigs else 'no significant edge'
            print(f'  [{i}/{len(files)}] {sym:10} [{cls:12}] {res["bars"]:5}bars | {sig_str}')
        except Exception as e:
            print(f'  [{i}/{len(files)}] {sym:10} ERROR: {str(e)[:60]}')

    # Save
    with open(OUT_PATH, 'w') as f:
        json.dump({'analyzed_at': datetime.now().isoformat(),
                   'window': WINDOW, 'lookahead': LOOKAHEAD,
                   'results': all_results}, f, indent=2, default=str)

    # Aggregate by asset class
    print(f'\n{"="*80}')
    print(f'AGGREGATE BY ASSET CLASS')
    print(f'{"="*80}')
    by_class = defaultdict(list)
    for sym, r in all_results.items():
        by_class[r['asset_class']].append((sym, r))

    for cls, items in by_class.items():
        print(f'\n── {cls.upper()} ({len(items)} symbols) ──')
        # Count how many symbols have a significant edge in each method
        counts = {'kmeans_full': 0, 'kmeans_shape': 0, 'v_reversal': 0, 'inverted_v': 0}
        best_edges = {'kmeans_full': [], 'kmeans_shape': [], 'v_reversal': [], 'inverted_v': []}
        for sym, r in items:
            for m in counts:
                if m in ('kmeans_full', 'kmeans_shape'):
                    if r.get(m) and r[m]['top']:
                        counts[m] += 1
                        best_edges[m].append(r[m]['top'][0]['best_edge'])
                else:
                    if r.get(m):
                        counts[m] += 1
                        best_edges[m].append(r[m]['best_edge'])

        for m, c in counts.items():
            if c > 0:
                avg_edge = np.mean(best_edges[m])
                print(f'  {m:15} {c}/{len(items)} symbols have sig. edge | avg best edge: {avg_edge:.1f}%')
            else:
                print(f'  {m:15} 0/{len(items)} — no significant edges')

    print(f'\nFull results saved to {OUT_PATH}')

if __name__ == '__main__':
    main()
