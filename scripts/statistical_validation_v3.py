#!/usr/bin/env python3
"""
Statistical validation v3 — adds central bank rate features to v2.

NEW features per forex pair:
- rate_diff: policy rate A minus policy rate B (e.g., ECB - SONIA for EURGBP)
- rate_diff_change_30d: change in differential over last 30 days
- days_since_A_change: days since rate A last moved
- days_since_B_change: days since rate B last moved

Asset→Rate mapping:
  EURGBP → ECB_MRO vs BOE_SONIA
  EURJPY → ECB_MRO vs JPY_3M_IB
  EURCHF → ECB_MRO vs CHF_3M_IB
  EURUSD → ECB_MRO vs FED_FUNDS
  EURAUD → ECB_MRO vs (no AU data — skip)
  GBPUSD → BOE_SONIA vs FED_FUNDS
  GBPJPY → BOE_SONIA vs JPY_3M_IB
  GBPCHF → BOE_SONIA vs CHF_3M_IB
  USDJPY → FED_FUNDS vs JPY_3M_IB
  USDCHF → FED_FUNDS vs CHF_3M_IB
  AUDJPY, AUDUSD, NZDUSD → skip (no policy rate data)
"""
import sys, os, csv, json
sys.path.insert(0, '/Users/mariashchekanenko/claude-trading-tv/scripts')
import numpy as np
import pandas as pd
from datetime import datetime
from scipy.stats import binomtest
from statistical_validation_v2 import (
    load_csv, precompute_indicators, kmeans
)

OHLCV_DIR = '/Users/mariashchekanenko/claude-trading-tv/data/ohlcv'
RATES_DIR = '/Users/mariashchekanenko/claude-trading-tv/data/rates'
OUT = '/Users/mariashchekanenko/claude-trading-tv/data/statistical-validation-v3.json'
WINDOW = 5
LOOKAHEAD = 5
MIN_N = 20
K = 20

# Asset → (base_rate_file, quote_rate_file)
PAIR_RATES = {
    'EURGBP': ('ECB_MRO', 'BOE_SONIA'),
    'EURJPY': ('ECB_MRO', 'JPY_3M_IB'),
    'EURCHF': ('ECB_MRO', 'CHF_3M_IB'),
    'EURUSD': ('ECB_MRO', 'FED_FUNDS'),
    'GBPUSD': ('BOE_SONIA', 'FED_FUNDS'),
    'GBPJPY': ('BOE_SONIA', 'JPY_3M_IB'),
    'GBPCHF': ('BOE_SONIA', 'CHF_3M_IB'),
    'USDJPY': ('FED_FUNDS', 'JPY_3M_IB'),
    'USDCHF': ('FED_FUNDS', 'CHF_3M_IB'),
}

def load_rate_series(name):
    """Load a rate series from CSV, return DataFrame indexed by date."""
    path = os.path.join(RATES_DIR, f'{name}.csv')
    df = pd.read_csv(path, parse_dates=['DATE'])
    df = df.set_index('DATE').sort_index()
    return df

def build_rate_features_for_asset(asset, bars):
    """For each bar, return dict with rate_diff, rate_diff_change_30d,
    days_since_base_change, days_since_quote_change. If asset has no rate mapping,
    return array of zeros (neutral).
    """
    n = len(bars)
    if asset not in PAIR_RATES:
        return np.zeros((n, 4))

    base_name, quote_name = PAIR_RATES[asset]
    try:
        base = load_rate_series(base_name)
        quote = load_rate_series(quote_name)
    except FileNotFoundError:
        return np.zeros((n, 4))

    # Resample to daily and forward-fill
    date_range = pd.date_range(
        start=min(base.index[0], quote.index[0]),
        end=max(base.index[-1], quote.index[-1]),
        freq='D')
    base_daily = base.reindex(date_range).ffill()
    quote_daily = quote.reindex(date_range).ffill()

    # Rate differential
    diff = (base_daily.iloc[:, 0] - quote_daily.iloc[:, 0])

    # 30-day differential change
    diff_30d_change = diff - diff.shift(30)

    # Days since each rate last changed
    base_changed = (base_daily.iloc[:, 0].diff().abs() > 1e-6).astype(int)
    quote_changed = (quote_daily.iloc[:, 0].diff().abs() > 1e-6).astype(int)

    def days_since_change(change_flag):
        result = np.zeros(len(change_flag))
        counter = 0
        for i in range(len(change_flag)):
            if change_flag.iloc[i] == 1:
                counter = 0
            else:
                counter += 1
            result[i] = counter
        return result

    days_base = days_since_change(base_changed)
    days_quote = days_since_change(quote_changed)

    # Lookup for each bar
    features = np.zeros((n, 4))
    for i, bar in enumerate(bars):
        d = pd.Timestamp(bar['time'].date())
        if d in diff.index:
            features[i, 0] = diff.loc[d] if pd.notna(diff.loc[d]) else 0
            features[i, 1] = diff_30d_change.loc[d] if pd.notna(diff_30d_change.loc[d]) else 0
            idx = date_range.get_loc(d) if d in date_range else -1
            features[i, 2] = days_base[idx] if idx >= 0 else 0
            features[i, 3] = days_quote[idx] if idx >= 0 else 0
    return features

def extract_v3(bars, asset):
    """v2 enhanced features + 4 rate features = 32+4 = 36 dims."""
    ind = precompute_indicators(bars)
    rate_feats = build_rate_features_for_asset(asset, bars)

    feats, outs = [], []
    for i in range(len(bars) - WINDOW - LOOKAHEAD):
        window = bars[i:i + WINDOW]
        base_price = window[0]['open']
        if base_price == 0:
            continue

        vec = []
        # 20 OHLC %
        for b in window:
            vec.extend([
                (b['open'] - base_price) / base_price * 100,
                (b['high'] - base_price) / base_price * 100,
                (b['low'] - base_price) / base_price * 100,
                (b['close'] - base_price) / base_price * 100,
            ])
        # 5 volume ratios
        for j in range(WINDOW):
            bi = i + j
            v = ind['vols'][bi]
            vm = ind['vol_ma20'][bi]
            ratio = v / vm if vm and not np.isnan(vm) else 1
            vec.append(min(ratio, 10))

        end = i + WINDOW - 1
        last_close = ind['closes'][end]

        rsi = ind['rsi'][end]
        if np.isnan(rsi):
            continue
        vec.append(rsi)

        e20 = ind['ema20'][end]
        if np.isnan(e20) or e20 == 0:
            continue
        vec.append((last_close - e20) / e20 * 100)

        e50 = ind['ema50'][end]
        if np.isnan(e50) or e50 == 0:
            continue
        vec.append((last_close - e50) / e50 * 100)

        atr = ind['atr'][end]
        if np.isnan(atr) or atr == 0:
            continue
        vec.append((ind['highs'][end] - ind['lows'][end]) / atr)

        t = ind['times'][end]
        vec.append(t.hour)
        vec.append(t.weekday())
        vec.append((e20 - e50) / e50 * 100)

        # 4 rate features
        vec.extend(rate_feats[end].tolist())

        if any(np.isnan(vec)) or any(np.isinf(vec)):
            continue

        feats.append(vec)
        entry = bars[i + WINDOW - 1]['close']
        exit_p = bars[i + WINDOW - 1 + LOOKAHEAD]['close']
        outs.append(1 if exit_p > entry else 0)

    return np.array(feats), np.array(outs)

def main():
    manifest = json.load(open(os.path.join(OHLCV_DIR, '_manifest.json')))
    asset_classes = {r['symbol']: r.get('asset_class') for r in manifest['results']}

    # Focus on forex pairs that have rate data
    forex_symbols = list(PAIR_RATES.keys())
    # Only those with downloaded data
    available = []
    for s in forex_symbols:
        if os.path.exists(os.path.join(OHLCV_DIR, f'{s}.csv')):
            available.append(s)
    print(f'Forex pairs with OHLCV + rate data: {len(available)}')
    print(f'  {available}')

    patterns = []
    for i, sym in enumerate(available, 1):
        path = os.path.join(OHLCV_DIR, f'{sym}.csv')
        bars = load_csv(path)
        if len(bars) < 200:
            continue

        try:
            X, outs = extract_v3(bars, sym)
        except Exception as e:
            print(f'  [{i}] {sym} FAILED: {e}')
            continue
        if len(X) < 50:
            continue

        baseline = float(outs.mean())
        Xs = (X - X.mean(0)) / (X.std(0) + 1e-8)
        lab = kmeans(Xs, K)
        if lab is None:
            continue

        clusters = 0
        for cid in set(lab):
            m = lab == cid
            n = int(m.sum())
            if n < MIN_N:
                continue
            k_up = int(outs[m].sum())
            patterns.append({
                'asset': sym, 'method': 'kmeans_v3_with_rates',
                'cluster': int(cid), 'n': n, 'k_up': k_up,
                'baseline_p': baseline,
            })
            clusters += 1
        print(f'  [{i}/{len(available)}] {sym:8} {len(bars)}b | {len(X)} windows | {clusters} clusters with n>={MIN_N}')

    total = len(patterns)
    threshold = 0.05 / total
    print(f'\nTotal patterns: {total}')
    print(f'Bonferroni threshold: {threshold:.2e}')

    for p in patterns:
        result = binomtest(p['k_up'], p['n'], p['baseline_p'], alternative='two-sided')
        p['p_value'] = float(result.pvalue)
        p['win_rate'] = p['k_up'] / p['n'] * 100
        p['baseline_pct'] = p['baseline_p'] * 100
        p['effect_size'] = (p['k_up'] / p['n'] - p['baseline_p']) * 100
        p['direction'] = 'LONG' if p['effect_size'] > 0 else 'SHORT'
        p['survives_bonferroni'] = result.pvalue < threshold

    survivors = [p for p in patterns if p['survives_bonferroni']]
    survivors.sort(key=lambda x: x['p_value'])

    print(f'\nBonferroni survivors: {len(survivors)}')
    if survivors:
        print(f'\n{"Asset":>8} {"Clu":>4} {"N":>5} {"WR%":>5} {"Base%":>6} '
              f'{"Edge":>6} {"Dir":>5} {"p-value":>10}')
        print('-' * 75)
        for p in survivors:
            print(f'{p["asset"]:>8} {p["cluster"]:>4} {p["n"]:>5} '
                  f'{p["win_rate"]:>5.1f} {p["baseline_pct"]:>6.1f} '
                  f'{p["effect_size"]:>+6.1f} {p["direction"]:>5} '
                  f'{p["p_value"]:>10.2e}')

    # Compare to v2 (which had 2 EURGBP survivors)
    print(f'\n─── Comparison ───')
    print(f'v2 (no rate features): 2 EURGBP survivors, threshold p < 3.76e-5')
    print(f'v3 (with rate features): {len(survivors)} survivors, threshold p < {threshold:.2e}')

    out_data = {
        'analyzed_at': datetime.now().isoformat(),
        'feature_set': 'v2 + rate_diff + rate_change_30d + days_since_rate_changes',
        'assets_tested': available,
        'total_patterns': total,
        'bonferroni_threshold': threshold,
        'survivors_count': len(survivors),
        'survivors': survivors,
        'all_patterns': patterns,
    }
    with open(OUT, 'w') as f:
        json.dump(out_data, f, indent=2, default=str)
    print(f'\nSaved to {OUT}')

if __name__ == '__main__':
    main()
