#!/usr/bin/env python3
"""
Statistical validation v2 — 2y data + 7 indicator features added to OHLCV.

Features added (all real-time computable):
- RSI(14)
- EMA20 distance: (close - EMA20) / EMA20 * 100
- EMA50 distance
- Volume ratio: current / avg(20)
- ATR(14) normalized: (high - low) / ATR(14)
- Hour of day (0-23)
- Day of week (0-6)
"""
import csv
import os
import json
import numpy as np
from datetime import datetime
from scipy.stats import binomtest

OHLCV_DIR = '/Users/mariashchekanenko/claude-trading-tv/data/ohlcv'
OUT_PATH = '/Users/mariashchekanenko/claude-trading-tv/data/statistical-validation-v2.json'
WINDOW = 5
LOOKAHEAD = 5
MIN_N = 20
K = 20  # fewer clusters → more samples each

# ─── Indicators (computed from OHLCV) ───
def compute_rsi(closes, period=14):
    """Standard RSI. Returns array same length as closes (NaN for first period)."""
    deltas = np.diff(closes)
    gains = np.where(deltas > 0, deltas, 0)
    losses = np.where(deltas < 0, -deltas, 0)
    rsi = np.full(len(closes), np.nan)
    if len(deltas) < period:
        return rsi
    avg_gain = np.mean(gains[:period])
    avg_loss = np.mean(losses[:period])
    for i in range(period, len(closes)):
        if i > period:
            avg_gain = (avg_gain * (period - 1) + gains[i - 1]) / period
            avg_loss = (avg_loss * (period - 1) + losses[i - 1]) / period
        rs = avg_gain / (avg_loss + 1e-12)
        rsi[i] = 100 - (100 / (1 + rs))
    return rsi

def compute_ema(values, period):
    ema = np.full(len(values), np.nan)
    if len(values) < period:
        return ema
    alpha = 2 / (period + 1)
    ema[period - 1] = np.mean(values[:period])
    for i in range(period, len(values)):
        ema[i] = alpha * values[i] + (1 - alpha) * ema[i - 1]
    return ema

def compute_atr(highs, lows, closes, period=14):
    """Average True Range."""
    tr = np.zeros(len(closes))
    tr[0] = highs[0] - lows[0]
    for i in range(1, len(closes)):
        tr[i] = max(
            highs[i] - lows[i],
            abs(highs[i] - closes[i - 1]),
            abs(lows[i] - closes[i - 1]),
        )
    atr = np.full(len(closes), np.nan)
    if len(closes) < period:
        return atr
    atr[period - 1] = np.mean(tr[:period])
    for i in range(period, len(closes)):
        atr[i] = (atr[i - 1] * (period - 1) + tr[i]) / period
    return atr

def precompute_indicators(bars):
    """Compute all indicators for the asset, return dict of arrays."""
    n = len(bars)
    opens = np.array([b['open'] for b in bars])
    highs = np.array([b['high'] for b in bars])
    lows = np.array([b['low'] for b in bars])
    closes = np.array([b['close'] for b in bars])
    vols = np.array([b['volume'] for b in bars])
    times = [b['time'] for b in bars]

    return {
        'rsi': compute_rsi(closes, 14),
        'ema20': compute_ema(closes, 20),
        'ema50': compute_ema(closes, 50),
        'atr': compute_atr(highs, lows, closes, 14),
        'vol_ma20': compute_ema(vols, 20),
        'closes': closes, 'highs': highs, 'lows': lows, 'opens': opens,
        'vols': vols, 'times': times,
    }

# ─── Feature extraction ───
def enhanced_features(bars, ind, idx):
    """OHLC % changes + indicator snapshot at end of window."""
    window = bars[idx:idx + WINDOW]
    base = window[0]['open']
    if base == 0:
        return None

    vec = []
    # OHLC normalized (20 dims)
    for b in window:
        vec.extend([
            (b['open'] - base) / base * 100,
            (b['high'] - base) / base * 100,
            (b['low'] - base) / base * 100,
            (b['close'] - base) / base * 100,
        ])

    # Volume ratio for each candle in window (5 dims)
    end_idx = idx + WINDOW - 1
    for j in range(WINDOW):
        bar_idx = idx + j
        v = ind['vols'][bar_idx]
        v_ma = ind['vol_ma20'][bar_idx]
        ratio = v / v_ma if v_ma and not np.isnan(v_ma) else 1
        vec.append(min(ratio, 10))  # cap at 10x to avoid outliers

    # Indicator snapshot at END of pattern window (7 dims)
    last_close = ind['closes'][end_idx]

    rsi = ind['rsi'][end_idx]
    if np.isnan(rsi):
        return None
    vec.append(rsi)

    e20 = ind['ema20'][end_idx]
    if np.isnan(e20) or e20 == 0:
        return None
    vec.append((last_close - e20) / e20 * 100)

    e50 = ind['ema50'][end_idx]
    if np.isnan(e50) or e50 == 0:
        return None
    vec.append((last_close - e50) / e50 * 100)

    atr = ind['atr'][end_idx]
    if np.isnan(atr) or atr == 0:
        return None
    vec.append((ind['highs'][end_idx] - ind['lows'][end_idx]) / atr)

    # Time features
    t = ind['times'][end_idx]
    vec.append(t.hour)
    vec.append(t.weekday())

    # EMA20 vs EMA50 (trend stack)
    vec.append((e20 - e50) / e50 * 100)

    return vec

def load_csv(path):
    bars = []
    with open(path) as f:
        for r in csv.DictReader(f):
            try:
                bars.append({
                    'time': datetime.utcfromtimestamp(int(r['timestamp'])),
                    'open': float(r['open']), 'high': float(r['high']),
                    'low': float(r['low']), 'close': float(r['close']),
                    'volume': int(float(r['volume'])),
                })
            except (ValueError, KeyError):
                continue
    return bars

def extract(bars):
    ind = precompute_indicators(bars)
    feats, outs = [], []
    for i in range(len(bars) - WINDOW - LOOKAHEAD):
        v = enhanced_features(bars, ind, i)
        if v is None or any(np.isnan(v)) or any(np.isinf(v)):
            continue
        feats.append(v)
        entry = bars[i + WINDOW - 1]['close']
        exit_p = bars[i + WINDOW - 1 + LOOKAHEAD]['close']
        outs.append(1 if exit_p > entry else 0)
    return np.array(feats), np.array(outs)

def kmeans(X, k, max_iter=80, seed=42):
    rng = np.random.RandomState(seed)
    n = X.shape[0]
    if n < k:
        return None
    cent = np.empty((k, X.shape[1]))
    cent[0] = X[rng.randint(n)]
    for j in range(1, k):
        d = np.min([np.sum((X - cent[c]) ** 2, axis=1) for c in range(j)], axis=0)
        total = d.sum()
        if total == 0:
            return None
        cent[j] = X[rng.choice(n, p=d / total)]
    labels = np.zeros(n, dtype=int)
    for _ in range(max_iter):
        d = np.array([np.sum((X - c) ** 2, axis=1) for c in cent])
        new = np.argmin(d, axis=0)
        if np.array_equal(new, labels):
            break
        labels = new
        for j in range(k):
            m = labels == j
            if m.sum() > 0:
                cent[j] = X[m].mean(axis=0)
    return labels

def main():
    manifest = json.load(open(os.path.join(OHLCV_DIR, '_manifest.json')))
    asset_classes = {r['symbol']: r.get('asset_class') for r in manifest['results']}
    files = sorted([f for f in os.listdir(OHLCV_DIR) if f.endswith('.csv')])
    print(f'Analyzing {len(files)} symbols with enhanced features...\n')

    patterns = []
    for i, fname in enumerate(files, 1):
        sym = fname.replace('.csv', '')
        cls = asset_classes.get(sym, 'unknown')
        path = os.path.join(OHLCV_DIR, fname)
        bars = load_csv(path)
        if len(bars) < 100:
            continue

        try:
            X, outs = extract(bars)
        except Exception as e:
            print(f'  [{i}/{len(files)}] {sym:10} EXTRACT ERROR: {str(e)[:50]}')
            continue
        if len(X) < 50:
            continue

        baseline_p = float(outs.mean())
        Xs = (X - X.mean(0)) / (X.std(0) + 1e-8)

        lab = kmeans(Xs, K)
        if lab is None:
            continue

        clusters_added = 0
        for cid in set(lab):
            m = lab == cid
            n = int(m.sum())
            if n < MIN_N:
                continue
            k_up = int(outs[m].sum())
            patterns.append({
                'asset': sym, 'asset_class': cls, 'method': 'kmeans_v2',
                'cluster': int(cid), 'n': n, 'k_up': k_up,
                'baseline_p': baseline_p,
            })
            clusters_added += 1

        if i % 10 == 0:
            print(f'  [{i}/{len(files)}] {sym:10} {len(bars)}b | clusters added: {clusters_added} | total: {len(patterns)}')

    print(f'\nTotal patterns collected: {len(patterns)}')

    # Statistical tests
    total_tests = len(patterns)
    bonferroni_threshold = 0.05 / total_tests
    print(f'Bonferroni threshold: 0.05 / {total_tests} = {bonferroni_threshold:.2e}')

    raw_sig = 0
    for p in patterns:
        result = binomtest(p['k_up'], p['n'], p['baseline_p'], alternative='two-sided')
        p['p_value'] = float(result.pvalue)
        p['win_rate'] = p['k_up'] / p['n'] * 100
        p['baseline_pct'] = p['baseline_p'] * 100
        p['effect_size'] = (p['k_up'] / p['n'] - p['baseline_p']) * 100
        p['direction'] = 'LONG' if p['effect_size'] > 0 else 'SHORT'
        p['survives_bonferroni'] = result.pvalue < bonferroni_threshold
        if result.pvalue < 0.05:
            raw_sig += 1

    survivors = [p for p in patterns if p['survives_bonferroni']]
    survivors.sort(key=lambda x: x['p_value'])

    print(f'\nRaw p<0.05 hits: {raw_sig}/{total_tests} ({raw_sig/total_tests*100:.1f}%)')
    print(f'Expected by chance: ~{int(total_tests*0.05)}')
    print(f'Bonferroni survivors: {len(survivors)}')

    if survivors:
        print(f'\n✓ {len(survivors)} pattern(s) PASS Bonferroni:\n')
        print(f'{"Asset":>8} {"Class":>10} {"Clu":>4} {"N":>5} '
              f'{"WR%":>5} {"Base%":>6} {"Edge%":>7} {"Dir":>5} {"p-value":>10}')
        print('-' * 90)
        for p in survivors[:30]:
            print(f'{p["asset"]:>8} {p["asset_class"]:>10} '
                  f'{str(p["cluster"]):>4} {p["n"]:>5} '
                  f'{p["win_rate"]:>5.1f} {p["baseline_pct"]:>6.1f} '
                  f'{p["effect_size"]:>+7.1f} {p["direction"]:>5} '
                  f'{p["p_value"]:>10.2e}')

        by_cls = {}
        for p in survivors:
            by_cls.setdefault(p['asset_class'], []).append(p)
        print(f'\n─── Survivors by class ───')
        for cls, items in by_cls.items():
            longs = sum(1 for p in items if p['direction'] == 'LONG')
            shorts = sum(1 for p in items if p['direction'] == 'SHORT')
            print(f'  {cls:12} {len(items)} ({longs} LONG, {shorts} SHORT)')
    else:
        print(f'\n❌ STILL NO SURVIVORS. Even with 2y data + indicator features,')
        print(f'   no pattern stands out from random chance after correction.')

    out = {
        'analyzed_at': datetime.now().isoformat(),
        'feature_set': 'OHLC + volume + RSI + EMA20/50 + ATR + time + EMA stack',
        'data_period': '2y',
        'total_tests': total_tests,
        'bonferroni_threshold': bonferroni_threshold,
        'min_occurrences': MIN_N,
        'k_clusters': K,
        'survivors_count': len(survivors),
        'all_patterns': patterns,
        'survivors': survivors,
    }
    with open(OUT_PATH, 'w') as f:
        json.dump(out, f, indent=2, default=str)
    print(f'\nResults saved to {OUT_PATH}')

if __name__ == '__main__':
    main()
