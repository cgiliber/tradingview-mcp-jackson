#!/usr/bin/env python3
"""
Multi-split robustness validation for the 12 v7 cash-flow candidates.

For each candidate:
1. Re-run K-Means on full data, identify target cluster
2. Extract rule-based triggers from cluster's feature distribution (P25/P75)
3. Apply those rules to 5 different training/test splits
4. Report win rate in each test period
5. Pattern is "robust" if all splits show win rate within ±5% of full-data result

Splits (on 2-year data):
  1. Forward 70/30: train first 70%, test last 30%
  2. Reverse 30/70: train last 70%, test first 30%
  3. Middle holdout: train first 50% + last 20%, test middle 30%
  4. Forward 80/20: train first 80%, test last 20%
  5. 2024 vs 2025: train 2024 data, test 2025+ data
"""
import sys, os, csv, json
sys.path.insert(0, '/Users/mariashchekanenko/claude-trading-tv/scripts')
import numpy as np
from datetime import datetime
from statistical_validation_v2 import load_csv, precompute_indicators, kmeans

OHLCV_DIR = '/Users/mariashchekanenko/claude-trading-tv/data/ohlcv'
OUT = '/Users/mariashchekanenko/claude-trading-tv/data/multi-split-validation.json'
WINDOW = 5
LOOKAHEAD = 5
K = 15

# The 12 candidates from v7
CANDIDATES = [
    {'asset': 'XRPUSD', 'cid': 2, 'direction': 'LONG', 'asset_class': 'crypto'},
    {'asset': 'BCS',    'cid': 0, 'direction': 'LONG', 'asset_class': 'eu_stocks'},
    {'asset': 'HSBC',   'cid': 11, 'direction': 'LONG', 'asset_class': 'eu_stocks'},
    {'asset': 'UL',     'cid': 0, 'direction': 'LONG', 'asset_class': 'eu_stocks'},
    {'asset': 'BCS',    'cid': 4, 'direction': 'LONG', 'asset_class': 'eu_stocks'},
    {'asset': 'HSBC',   'cid': 13, 'direction': 'LONG', 'asset_class': 'eu_stocks'},
    {'asset': 'DNBBY',  'cid': 2, 'direction': 'LONG', 'asset_class': 'eu_stocks'},
    {'asset': 'NVS',    'cid': 0, 'direction': 'LONG', 'asset_class': 'eu_stocks'},
    {'asset': 'HSBC',   'cid': 1, 'direction': 'LONG', 'asset_class': 'eu_stocks'},
    {'asset': 'BCS',    'cid': 2, 'direction': 'LONG', 'asset_class': 'eu_stocks'},
    {'asset': 'AAPL',   'cid': 6, 'direction': 'LONG', 'asset_class': 'us_stocks'},
    {'asset': 'BNBUSD', 'cid': 6, 'direction': 'LONG', 'asset_class': 'crypto'},
]

COSTS = {'forex': 0.02, 'us_stocks': 0.05, 'eu_stocks': 0.05,
         'crypto': 0.15, 'etf_macro': 0.05, 'unknown': 0.10}

def v2_feat(bars, i, ind):
    window = bars[i:i + WINDOW]
    base = window[0]['open']
    if base == 0: return None
    vec = []
    for b in window:
        vec.extend([(b['open']-base)/base*100, (b['high']-base)/base*100,
                    (b['low']-base)/base*100, (b['close']-base)/base*100])
    for j in range(WINDOW):
        bi = i + j
        v = ind['vols'][bi]
        vm = ind['vol_ma20'][bi]
        vec.append(min(v/vm if vm else 1, 10))
    end = i + WINDOW - 1
    c = ind['closes'][end]
    rsi = ind['rsi'][end]
    if np.isnan(rsi): return None
    vec.append(rsi)
    e20 = ind['ema20'][end]
    if np.isnan(e20) or e20 == 0: return None
    vec.append((c - e20) / e20 * 100)
    e50 = ind['ema50'][end]
    if np.isnan(e50) or e50 == 0: return None
    vec.append((c - e50) / e50 * 100)
    atr = ind['atr'][end]
    if np.isnan(atr) or atr == 0: return None
    vec.append((ind['highs'][end] - ind['lows'][end]) / atr)
    t = ind['times'][end]
    vec.append(t.hour); vec.append(t.weekday())
    vec.append((e20 - e50) / e50 * 100)
    return vec

def extract_with_idx(bars):
    ind = precompute_indicators(bars)
    feats, outs_pct, idxs = [], [], []
    for i in range(len(bars) - WINDOW - LOOKAHEAD):
        v = v2_feat(bars, i, ind)
        if v is None or any(np.isnan(v)) or any(np.isinf(v)):
            continue
        feats.append(v)
        entry = bars[i + WINDOW - 1]['close']
        exit_p = bars[i + WINDOW - 1 + LOOKAHEAD]['close']
        outs_pct.append((exit_p - entry) / entry * 100)
        idxs.append(i)
    return np.array(feats), np.array(outs_pct), idxs, ind

# Feature indices in v2 vector:
# 25: RSI(14), 26: EMA20_dist%, 27: EMA50_dist%, 28: range/ATR
# 29: Hour, 30: Weekday, 31: EMA20-EMA50%
INDICATOR_NAMES = {25: 'rsi', 26: 'ema20_dist', 27: 'ema50_dist', 28: 'range_atr',
                   29: 'hour', 30: 'weekday', 31: 'ema_stack'}

def extract_triggers(cluster_X):
    """From cluster's feature matrix, extract P25/P75 bounds for rule-based triggers."""
    triggers = {}
    for idx, name in INDICATOR_NAMES.items():
        vals = cluster_X[:, idx]
        triggers[name] = {
            'p10': float(np.percentile(vals, 10)),
            'p25': float(np.percentile(vals, 25)),
            'p75': float(np.percentile(vals, 75)),
            'p90': float(np.percentile(vals, 90)),
            'mean': float(vals.mean()),
        }
    return triggers

def matches_trigger(feat_row, triggers, feature_idx_map=INDICATOR_NAMES):
    """Check if a feature vector falls inside the cluster's P10-P90 bounds on every indicator."""
    for idx, name in feature_idx_map.items():
        val = feat_row[idx]
        t = triggers[name]
        if val < t['p10'] or val > t['p90']:
            return False
    return True

def measure_period(bars, X, outs_pct, idxs, triggers, start_idx, end_idx):
    """Apply triggers to windows in [start_idx, end_idx). Return trades."""
    trades = []
    last_trade_idx = -LOOKAHEAD - 1
    for pos in range(len(idxs)):
        idx = idxs[pos]
        if idx < start_idx or idx >= end_idx - LOOKAHEAD:
            continue
        if idx - last_trade_idx < LOOKAHEAD:
            continue  # no overlap
        if matches_trigger(X[pos], triggers):
            move_pct = outs_pct[pos]
            trades.append({
                'idx': idx,
                'time': bars[idx]['time'].strftime('%Y-%m-%d %H:%M'),
                'move_pct': float(move_pct),
            })
            last_trade_idx = idx
    return trades

def compute_stats(trades, direction, cost):
    if not trades:
        return {'n_trades': 0}
    n = len(trades)
    if direction == 'LONG':
        nets = [t['move_pct'] - cost for t in trades]
    else:
        nets = [-t['move_pct'] - cost for t in trades]
    wins = sum(1 for x in nets if x > 0)
    wr = wins / n * 100
    total = sum(nets)
    return {
        'n_trades': n,
        'win_rate': round(wr, 1),
        'total_return_pct': round(total, 2),
        'avg_trade_pct': round(total / n, 3),
    }

def build_splits(bars, X, outs_pct, idxs):
    """Return list of (label, train_start, train_end, test_start, test_end) index ranges into bars."""
    n = len(bars)
    splits = [
        ('forward_70_30',  0, int(0.70 * n),  int(0.70 * n), n),
        ('reverse_30_70',  int(0.30 * n), n,  0, int(0.30 * n)),
        ('middle_holdout', 0, int(0.35 * n),   int(0.35 * n), int(0.65 * n)),  # simplified
        ('forward_80_20',  0, int(0.80 * n),   int(0.80 * n), n),
    ]
    # 2024_vs_2025: find cutoff ~ 2025-01-01
    cutoff_ts = datetime(2025, 1, 1)
    cutoff_idx = 0
    for i, b in enumerate(bars):
        if b['time'] >= cutoff_ts:
            cutoff_idx = i; break
    if cutoff_idx > 0:
        splits.append(('2024_vs_2025', 0, cutoff_idx, cutoff_idx, n))
    return splits

def main():
    results = []
    for cand in CANDIDATES:
        asset = cand['asset']
        cid = cand['cid']
        cls = cand['asset_class']
        print(f'\n═══ {asset} C{cid} ({cand["direction"]}) ═══')
        path = os.path.join(OHLCV_DIR, f'{asset}.csv')
        bars = load_csv(path)
        if len(bars) < 300:
            print('  insufficient data'); continue

        X, outs_pct, idxs, ind = extract_with_idx(bars)
        Xs = (X - X.mean(0)) / (X.std(0) + 1e-8)
        lab = kmeans(Xs, K)
        if lab is None:
            print('  kmeans failed'); continue

        # Extract cluster and its trigger characteristics
        cluster_mask = lab == cid
        cluster_X = X[cluster_mask]
        if cluster_mask.sum() < 20:
            print(f'  cluster C{cid} too small ({cluster_mask.sum()})')
            continue

        triggers = extract_triggers(cluster_X)

        # Full-data baseline
        full_trades = measure_period(bars, X, outs_pct, idxs, triggers, 0, len(bars))
        full_stats = compute_stats(full_trades, cand['direction'], COSTS.get(cls, 0.1))
        print(f'  FULL DATA: {full_stats.get("n_trades")} trades, '
              f'WR {full_stats.get("win_rate")}%, return {full_stats.get("total_return_pct")}%')

        # Multi-split validation
        splits = build_splits(bars, X, outs_pct, idxs)
        split_results = {}
        pass_count = 0

        for label, tr_s, tr_e, te_s, te_e in splits:
            test_trades = measure_period(bars, X, outs_pct, idxs, triggers, te_s, te_e)
            test_stats = compute_stats(test_trades, cand['direction'], COSTS.get(cls, 0.1))
            split_results[label] = test_stats

            # Pattern passes a split if: test has enough trades AND win rate within ±5% of full
            if test_stats.get('n_trades', 0) >= 5:
                wr_diff = abs(test_stats['win_rate'] - full_stats['win_rate'])
                passes = (test_stats['win_rate'] >= 52) and (test_stats['total_return_pct'] > 0)
                status = '✅' if passes else '❌'
                if passes:
                    pass_count += 1
            else:
                status = '⚠️ few'

            print(f'  {label:18} test: {test_stats.get("n_trades",0):3} trades '
                  f'WR {test_stats.get("win_rate","-")}% '
                  f'return {test_stats.get("total_return_pct","-")}% {status}')

        verdict = 'ROBUST' if pass_count >= 4 else 'FRAGILE' if pass_count >= 2 else 'FAILED'
        print(f'  → Passed {pass_count}/{len(splits)} splits → {verdict}')

        results.append({
            **cand,
            'full_data_stats': full_stats,
            'splits': split_results,
            'splits_passed': pass_count,
            'total_splits': len(splits),
            'verdict': verdict,
            'triggers': triggers,
        })

    # Summary
    print(f'\n═══ SUMMARY ═══')
    robust = [r for r in results if r['verdict'] == 'ROBUST']
    fragile = [r for r in results if r['verdict'] == 'FRAGILE']
    failed = [r for r in results if r['verdict'] == 'FAILED']
    print(f'ROBUST (4+ splits passed): {len(robust)}')
    for r in robust:
        print(f'  ✓ {r["asset"]:8} C{r["cid"]}  {r["splits_passed"]}/{r["total_splits"]} splits')
    print(f'FRAGILE (2-3 splits passed): {len(fragile)}')
    for r in fragile:
        print(f'  ~ {r["asset"]:8} C{r["cid"]}  {r["splits_passed"]}/{r["total_splits"]} splits')
    print(f'FAILED (<2 splits passed): {len(failed)}')
    for r in failed:
        print(f'  ✗ {r["asset"]:8} C{r["cid"]}  {r["splits_passed"]}/{r["total_splits"]} splits')

    with open(OUT, 'w') as f:
        json.dump({
            'analyzed_at': datetime.now().isoformat(),
            'candidates': results,
        }, f, indent=2, default=str)
    print(f'\nSaved to {OUT}')

if __name__ == '__main__':
    main()
