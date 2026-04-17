#!/usr/bin/env python3
"""
Statistical validation of all patterns/clusters across all 74 assets.

For each pattern:
- Null hypothesis: pattern's win rate = baseline buy rate of that asset
- Two-sided binomial test (testing both LONG and SHORT directions)
- Bonferroni correction across ALL tested patterns

Filter: only patterns with n >= 20 occurrences.
Output: only patterns surviving Bonferroni correction (or report none survived).
"""
import csv
import os
import json
import numpy as np
from datetime import datetime
from scipy.stats import binomtest

OHLCV_DIR = '/Users/mariashchekanenko/claude-trading-tv/data/ohlcv'
OUT_PATH = '/Users/mariashchekanenko/claude-trading-tv/data/statistical-validation.json'
WINDOW = 5
LOOKAHEAD = 5
MIN_N = 20

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
            outs.append(0)  # 0 = down/flat
        else:
            outs.append(1 if exit_p > entry else 0)  # 1 = up
    return np.array(feats), np.array(outs)

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

def template_match_outcomes(bars, template, threshold):
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
                matches.append(1 if fut[-1]['close'] > entry else 0)
    return np.array(matches)

def collect_all_patterns():
    """Return list of (asset, asset_class, method, cluster_id, n, k_wins, baseline_p)."""
    manifest = json.load(open(os.path.join(OHLCV_DIR, '_manifest.json')))
    asset_classes = {r['symbol']: r.get('asset_class') for r in manifest['results']}

    files = sorted([f for f in os.listdir(OHLCV_DIR) if f.endswith('.csv')])
    print(f'Collecting patterns from {len(files)} symbols...')

    patterns = []
    for i, fname in enumerate(files, 1):
        sym = fname.replace('.csv', '')
        cls = asset_classes.get(sym, 'unknown')
        path = os.path.join(OHLCV_DIR, fname)

        bars = load_csv(path)
        if len(bars) < 100:
            continue

        X_full, outs = extract(bars, full_features)
        X_shape, _ = extract(bars, shape_features)
        if len(X_full) < 30:
            continue

        # Baseline: % of all 5-bar entries that go UP after 5 bars on this asset
        baseline_p = float(outs.mean())  # P(UP)

        # Standardize
        X_full_s = (X_full - X_full.mean(0)) / (X_full.std(0) + 1e-8)
        X_shape_s = (X_shape - X_shape.mean(0)) / (X_shape.std(0) + 1e-8)

        # K-Means FULL K=30
        lab = kmeans(X_full_s, 30)
        if lab is not None:
            for cid in set(lab):
                m = lab == cid
                n = int(m.sum())
                if n < MIN_N:
                    continue
                k_up = int(outs[m].sum())
                patterns.append({
                    'asset': sym, 'asset_class': cls, 'method': 'kmeans_full',
                    'cluster': int(cid), 'n': n, 'k_up': k_up,
                    'baseline_p': baseline_p,
                })

        # K-Means SHAPE K=30
        lab = kmeans(X_shape_s, 30)
        if lab is not None:
            for cid in set(lab):
                m = lab == cid
                n = int(m.sum())
                if n < MIN_N:
                    continue
                k_up = int(outs[m].sum())
                patterns.append({
                    'asset': sym, 'asset_class': cls, 'method': 'kmeans_shape',
                    'cluster': int(cid), 'n': n, 'k_up': k_up,
                    'baseline_p': baseline_p,
                })

        # Templates: V and Inv-V at 3 thresholds
        templates = {
            'v_reversal': [-2, -3, -4, -3, -1],
            'inverted_v': [1, 2, 3, 2, 0],
        }
        for tname, tvec in templates.items():
            for thr in [0.6, 0.7, 0.8]:
                m_outs = template_match_outcomes(bars, tvec, thr)
                if len(m_outs) < MIN_N:
                    continue
                patterns.append({
                    'asset': sym, 'asset_class': cls, 'method': tname,
                    'cluster': f'thr_{thr}', 'n': int(len(m_outs)),
                    'k_up': int(m_outs.sum()),
                    'baseline_p': baseline_p,
                })

        if i % 10 == 0:
            print(f'  [{i}/{len(files)}] {sym} done — patterns so far: {len(patterns)}')

    print(f'Total patterns collected: {len(patterns)}')
    return patterns

def validate(patterns):
    """Compute p-values and Bonferroni correction."""
    total_tests = len(patterns)
    bonferroni_threshold = 0.05 / total_tests
    print(f'\nTotal patterns to test: {total_tests}')
    print(f'Bonferroni threshold: 0.05 / {total_tests} = {bonferroni_threshold:.2e}')
    print(f'Original threshold (no correction): 0.05')

    for p in patterns:
        n = p['n']
        k = p['k_up']
        p0 = p['baseline_p']
        # Two-sided binomial test
        result = binomtest(k, n, p0, alternative='two-sided')
        p['p_value'] = float(result.pvalue)
        p['win_rate'] = k / n * 100
        p['baseline_pct'] = p0 * 100
        p['effect_size'] = (k / n - p0) * 100  # signed: + means MORE up than baseline
        p['direction'] = 'LONG' if p['effect_size'] > 0 else 'SHORT'
        p['survives_bonferroni'] = result.pvalue < bonferroni_threshold

    survivors = [p for p in patterns if p['survives_bonferroni']]
    survivors.sort(key=lambda x: x['p_value'])
    return survivors, bonferroni_threshold, total_tests

def print_results(survivors, threshold, total_tests, all_patterns):
    print(f'\n{"="*100}')
    print(f'STATISTICAL VALIDATION RESULTS')
    print(f'{"="*100}')

    # Summary stats first
    raw_sig = sum(1 for p in all_patterns if p['p_value'] < 0.05)
    print(f'\nTotal patterns tested: {total_tests}')
    print(f'Patterns "significant" at raw p<0.05: {raw_sig} ({raw_sig/total_tests*100:.1f}%)')
    print(f'(of these, ~{int(total_tests*0.05)} would be expected by pure chance — false positive rate)')
    print(f'\nBonferroni threshold: p < {threshold:.2e}')
    print(f'Patterns surviving Bonferroni: {len(survivors)}')

    if not survivors:
        print(f'\n❌ NO PATTERNS SURVIVE BONFERRONI CORRECTION.')
        print(f'   This means: every "edge" we found could be explained by random chance')
        print(f'   given the number of tests we ran. We were curve-fitting noise.')
        return

    print(f'\n✓ {len(survivors)} pattern(s) PASS Bonferroni-corrected significance:\n')
    print(f'{"Asset":>8} {"Class":>10} {"Method":>13} {"Clu":>4} {"N":>4} '
          f'{"WR%":>5} {"Base%":>6} {"Edge%":>6} {"Dir":>5} {"p-value":>10}')
    print('-' * 100)
    for p in survivors:
        print(f'{p["asset"]:>8} {p["asset_class"]:>10} {p["method"]:>13} '
              f'{str(p["cluster"]):>4} {p["n"]:>4} '
              f'{p["win_rate"]:>5.1f} {p["baseline_pct"]:>6.1f} '
              f'{p["effect_size"]:>+6.1f} {p["direction"]:>5} '
              f'{p["p_value"]:>10.2e}')

    # Group by asset class
    print(f'\n─── Survivors by asset class ───')
    by_cls = {}
    for p in survivors:
        by_cls.setdefault(p['asset_class'], []).append(p)
    for cls, items in by_cls.items():
        long_count = sum(1 for p in items if p['direction'] == 'LONG')
        short_count = sum(1 for p in items if p['direction'] == 'SHORT')
        print(f'  {cls:12} {len(items)} survivors ({long_count} LONG, {short_count} SHORT)')

def main():
    patterns = collect_all_patterns()
    survivors, threshold, total = validate(patterns)
    print_results(survivors, threshold, total, patterns)

    # Save
    out = {
        'analyzed_at': datetime.now().isoformat(),
        'total_tests': total,
        'bonferroni_threshold': threshold,
        'min_occurrences': MIN_N,
        'survivors_count': len(survivors),
        'all_patterns': patterns,
        'survivors': survivors,
    }
    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    with open(OUT_PATH, 'w') as f:
        json.dump(out, f, indent=2, default=str)
    print(f'\nFull results saved to {OUT_PATH}')

if __name__ == '__main__':
    main()
