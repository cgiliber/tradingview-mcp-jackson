#!/usr/bin/env python3
"""
Crypto v5 — adds Binance perpetual funding rate as a feature.

Funding rate features (computed at end of pattern window):
- current_funding: most recent funding rate (signed, %)
- funding_avg_3day: mean funding over last 9 periods (3 days × 3 fundings/day)
- funding_extremity: abs(current) as "sentiment extreme" signal
- funding_change_1d: current - 3 periods ago (sentiment shift)

Hypothesis: extreme positive funding → longs crowded → mean reversion down.
Extreme negative → shorts crowded → mean reversion up.
"""
import sys, os, csv, json, bisect
sys.path.insert(0, '/Users/mariashchekanenko/claude-trading-tv/scripts')
import numpy as np
from datetime import datetime
from scipy.stats import binomtest
from statistical_validation_v2 import load_csv, precompute_indicators, kmeans

OHLCV_DIR = '/Users/mariashchekanenko/claude-trading-tv/data/ohlcv'
FUNDING_DIR = '/Users/mariashchekanenko/claude-trading-tv/data/funding'
OUT = '/Users/mariashchekanenko/claude-trading-tv/data/statistical-validation-v5-crypto.json'

WINDOW = 5
LOOKAHEAD = 5
MIN_N = 20
K = 15

# Asset → Binance perpetual symbol
ASSET_FUNDING = {
    'BTCUSD': 'BTCUSDT',
    'ETHUSD': 'ETHUSDT',
    'SOLUSD': 'SOLUSDT',
    'XRPUSD': 'XRPUSDT',
    'ADAUSD': 'ADAUSDT',
    'BNBUSD': 'BNBUSDT',
    'AVAXUSD': 'AVAXUSDT',
    'LINKUSD': 'LINKUSDT',
}

def load_funding(symbol):
    """Load funding rates as (sorted_ts_seconds, rate) lists for fast lookup."""
    path = os.path.join(FUNDING_DIR, f'{symbol}.csv')
    if not os.path.exists(path):
        return None
    ts_list, rates = [], []
    with open(path) as f:
        for r in csv.DictReader(f):
            try:
                ts = int(r['funding_time']) // 1000  # ms → s
                rate = float(r['funding_rate'])
                ts_list.append(ts)
                rates.append(rate)
            except (ValueError, KeyError):
                continue
    # Already sorted
    return np.array(ts_list), np.array(rates)

def funding_at(ts_seconds, funding_data, lookback_n=1):
    """Get most recent funding rate at or before ts. Optionally lookback N periods."""
    ts_arr, rates = funding_data
    idx = bisect.bisect_right(ts_arr, ts_seconds) - 1
    if idx < 0:
        return None, None
    if lookback_n > 1:
        start = max(0, idx - lookback_n + 1)
        window_rates = rates[start:idx+1]
        return rates[idx], window_rates
    return rates[idx], rates[idx:idx+1]

def extract_v5(bars, asset):
    """Extract v2 features + 4 funding rate features."""
    funding_key = ASSET_FUNDING.get(asset)
    if not funding_key:
        return None, None
    funding = load_funding(funding_key)
    if funding is None:
        return None, None

    ind = precompute_indicators(bars)
    feats, outs = [], []

    for i in range(len(bars) - WINDOW - LOOKAHEAD):
        window = bars[i:i + WINDOW]
        base_p = window[0]['open']
        if base_p == 0:
            continue

        vec = []
        # 20 OHLC %
        for b in window:
            vec.extend([(b['open']-base_p)/base_p*100, (b['high']-base_p)/base_p*100,
                        (b['low']-base_p)/base_p*100, (b['close']-base_p)/base_p*100])
        # 5 volume ratios
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
        vec.append(1 if t.weekday() >= 5 else 0)  # weekend flag
        vec.append((e20 - e50) / e50 * 100)

        # Funding rate features
        ts = int(bars[end]['time'].timestamp())
        current, window_rates = funding_at(ts, funding, lookback_n=9)  # last 3 days
        if current is None:
            continue
        vec.append(current * 100)                             # current funding %
        vec.append(float(window_rates.mean()) * 100)          # 3-day avg %
        vec.append(abs(current) * 100)                        # extremity
        prev, _ = funding_at(ts - 24 * 3600, funding)         # 1 day ago
        if prev is None:
            vec.append(0)
        else:
            vec.append((current - prev) * 100)                # 1-day change

        if any(np.isnan(vec)) or any(np.isinf(vec)):
            continue

        feats.append(vec)
        entry = bars[end]['close']
        exit_p = bars[end + LOOKAHEAD]['close']
        outs.append(1 if exit_p > entry else 0)

    return np.array(feats), np.array(outs)

def main():
    available = [s for s in ASSET_FUNDING
                 if os.path.exists(os.path.join(OHLCV_DIR, f'{s}.csv'))]
    print(f'Crypto assets with OHLCV + funding data: {available}\n')

    patterns = []
    for sym in available:
        path = os.path.join(OHLCV_DIR, f'{sym}.csv')
        bars = load_csv(path)
        if len(bars) < 200:
            continue
        X, outs = extract_v5(bars, sym)
        if X is None or len(X) < 50:
            print(f'  {sym} skipped ({len(X) if X is not None else 0} windows)')
            continue

        baseline = float(outs.mean())
        Xs = (X - X.mean(0)) / (X.std(0) + 1e-8)
        lab = kmeans(Xs, K)
        if lab is None:
            continue

        added = 0
        for cid in set(lab):
            m = lab == cid
            n = int(m.sum())
            if n < MIN_N: continue
            k_up = int(outs[m].sum())
            patterns.append({
                'asset': sym, 'cluster': int(cid), 'n': n, 'k_up': k_up,
                'baseline_p': baseline,
                'mean_funding': float(X[m][:, 32].mean()),
                'mean_funding_3d': float(X[m][:, 33].mean()),
                'mean_funding_extremity': float(X[m][:, 34].mean()),
                'mean_rsi': float(X[m][:, 25].mean()),
            })
            added += 1
        print(f'  {sym:8} {len(bars)}b | {len(X)} windows | {added} clusters')

    total = len(patterns)
    threshold = 0.05 / total if total else 1
    print(f'\nTotal patterns: {total}')
    print(f'Bonferroni threshold: {threshold:.2e}')

    raw_sig = 0
    for p in patterns:
        result = binomtest(p['k_up'], p['n'], p['baseline_p'], alternative='two-sided')
        p['p_value'] = float(result.pvalue)
        p['win_rate'] = p['k_up'] / p['n'] * 100
        p['baseline_pct'] = p['baseline_p'] * 100
        p['effect_size'] = (p['k_up'] / p['n'] - p['baseline_p']) * 100
        p['direction'] = 'LONG' if p['effect_size'] > 0 else 'SHORT'
        p['survives_bonferroni'] = result.pvalue < threshold
        if result.pvalue < 0.05:
            raw_sig += 1

    survivors = [p for p in patterns if p['survives_bonferroni']]
    survivors.sort(key=lambda x: x['p_value'])

    print(f'Raw p<0.05 hits: {raw_sig}/{total}')
    print(f'Bonferroni survivors: {len(survivors)}\n')

    if survivors:
        print(f'{"Asset":>8} {"Clu":>4} {"N":>5} {"WR%":>5} {"Base%":>6} {"Edge":>6} '
              f'{"Dir":>5} {"Fund%":>7} {"Fund3d":>7} {"RSI":>5} {"p-value":>11}')
        print('-' * 105)
        for p in survivors:
            print(f'{p["asset"]:>8} {p["cluster"]:>4} {p["n"]:>5} '
                  f'{p["win_rate"]:>5.1f} {p["baseline_pct"]:>6.1f} '
                  f'{p["effect_size"]:>+6.1f} {p["direction"]:>5} '
                  f'{p["mean_funding"]:>+7.4f} {p["mean_funding_3d"]:>+7.4f} '
                  f'{p["mean_rsi"]:>5.1f} {p["p_value"]:>11.2e}')
    else:
        print('❌ No crypto patterns survive Bonferroni.')
        patterns.sort(key=lambda x: x['p_value'])
        print(f'\nTop 5 closest to significance:')
        for p in patterns[:5]:
            print(f'  {p["asset"]:>8} C{p["cluster"]:>2} n={p["n"]:>4} '
                  f'WR={p["win_rate"]:.1f}% edge={p["effect_size"]:+.1f}% '
                  f'fund={p["mean_funding"]:+.4f}% fund3d={p["mean_funding_3d"]:+.4f}% '
                  f'p={p["p_value"]:.2e}')

    with open(OUT, 'w') as f:
        json.dump({
            'analyzed_at': datetime.now().isoformat(),
            'feature_set': 'v2 + funding rate (current, 3d avg, extremity, 1d change)',
            'assets': available,
            'total_patterns': total,
            'bonferroni_threshold': threshold,
            'survivors_count': len(survivors),
            'survivors': survivors,
            'all_patterns': patterns,
        }, f, indent=2, default=str)
    print(f'\nSaved to {OUT}')

if __name__ == '__main__':
    main()
