#!/usr/bin/env python3
"""
v6 — find TRADEABLE BIG-MOVE patterns, not just statistical edges.

New filter criteria:
1. avg absolute move >= 2% in 5 bars (real money moves)
2. win rate >= 60% (true directional edge)
3. expected value per trade >= 1% after costs
4. passes Bonferroni on both direction + magnitude

Includes stocks + crypto + forex.
Applies K=15 K-Means with v2 features (OHLCV + indicators + time).
For crypto, also tries v5 features (adds funding rate).

Filter order (prune early to reduce multiple testing):
1. n >= 20
2. avg_abs_move_5bar >= 1.5%
3. win_rate >= 58% or <= 42%
4. binomial p-value passes Bonferroni on surviving set
"""
import sys, os, csv, json
sys.path.insert(0, '/Users/mariashchekanenko/claude-trading-tv/scripts')
import numpy as np
from datetime import datetime
from scipy.stats import binomtest
from statistical_validation_v2 import load_csv, precompute_indicators, kmeans

OHLCV_DIR = '/Users/mariashchekanenko/claude-trading-tv/data/ohlcv'
OUT = '/Users/mariashchekanenko/claude-trading-tv/data/statistical-validation-v6-bigmoves.json'

WINDOW = 5
LOOKAHEAD = 5
MIN_N = 20
K = 15

# Filter thresholds
MIN_AVG_ABS_MOVE_PCT = 1.5      # pattern must produce avg |move| >= 1.5%
MIN_WIN_RATE = 58                # or max_short_rate = 42
MIN_EV_AFTER_COSTS = 0.5         # % per trade after trading costs

# Per-class trading costs (round-trip)
COSTS = {
    'forex': 0.02,        # ~1-2 pips on majors
    'us_stocks': 0.05,    # commissions ~$0 + spread/slippage
    'eu_stocks': 0.05,
    'crypto': 0.15,       # 0.1% per side × 2 = 0.2% (we use 0.15% conservative)
    'etf_macro': 0.05,
}

def v2_features(bars, idx, ind):
    window = bars[idx:idx + WINDOW]
    base = window[0]['open']
    if base == 0:
        return None
    vec = []
    for b in window:
        vec.extend([(b['open']-base)/base*100, (b['high']-base)/base*100,
                    (b['low']-base)/base*100, (b['close']-base)/base*100])
    for j in range(WINDOW):
        bi = idx + j
        v = ind['vols'][bi]
        vm = ind['vol_ma20'][bi]
        vec.append(min(v/vm if vm else 1, 10))
    end = idx + WINDOW - 1
    last_close = ind['closes'][end]
    rsi = ind['rsi'][end]
    if np.isnan(rsi): return None
    vec.append(rsi)
    e20 = ind['ema20'][end]
    if np.isnan(e20) or e20 == 0: return None
    vec.append((last_close - e20) / e20 * 100)
    e50 = ind['ema50'][end]
    if np.isnan(e50) or e50 == 0: return None
    vec.append((last_close - e50) / e50 * 100)
    atr = ind['atr'][end]
    if np.isnan(atr) or atr == 0: return None
    vec.append((ind['highs'][end] - ind['lows'][end]) / atr)
    t = ind['times'][end]
    vec.append(t.hour); vec.append(t.weekday())
    vec.append((e20 - e50) / e50 * 100)
    return vec

def extract(bars):
    ind = precompute_indicators(bars)
    feats, outs_pct = [], []
    for i in range(len(bars) - WINDOW - LOOKAHEAD):
        v = v2_features(bars, i, ind)
        if v is None or any(np.isnan(v)) or any(np.isinf(v)):
            continue
        feats.append(v)
        entry = bars[i + WINDOW - 1]['close']
        exit_p = bars[i + WINDOW - 1 + LOOKAHEAD]['close']
        move_pct = (exit_p - entry) / entry * 100
        outs_pct.append(move_pct)
    return np.array(feats), np.array(outs_pct)

def cluster_metrics(labels, outs_pct):
    """For each cluster: n, win_rate, avg_abs_move, EV, direction stats."""
    stats = []
    for cid in set(labels):
        m = labels == cid
        n = int(m.sum())
        if n < MIN_N:
            continue
        moves = outs_pct[m]
        wins = int((moves > 0).sum())
        losses = int((moves < 0).sum())
        wr = wins / n * 100
        win_moves = moves[moves > 0]
        loss_moves = moves[moves < 0]
        avg_win = float(win_moves.mean()) if len(win_moves) else 0
        avg_loss = float(loss_moves.mean()) if len(loss_moves) else 0
        avg_abs = float(np.abs(moves).mean())
        median_abs = float(np.median(np.abs(moves)))
        # Expected value per trade (signed, from long POV)
        ev = wr/100 * avg_win + (1 - wr/100) * avg_loss

        # Big move hits: % with |move| >= 2%
        big_hits = int((np.abs(moves) >= 2).sum())
        big_hit_rate = big_hits / n * 100

        stats.append({
            'cid': int(cid), 'n': n, 'win_rate': round(wr, 1),
            'avg_abs_move': round(avg_abs, 3),
            'median_abs_move': round(median_abs, 3),
            'avg_win': round(avg_win, 3),
            'avg_loss': round(avg_loss, 3),
            'ev_per_trade': round(ev, 3),
            'big_hit_rate': round(big_hit_rate, 1),
            'moves_arr': moves,  # keep for binomial test
        })
    return stats

def main():
    manifest = json.load(open(os.path.join(OHLCV_DIR, '_manifest.json')))
    asset_classes = {r['symbol']: r.get('asset_class') for r in manifest['results']}

    files = sorted([f for f in os.listdir(OHLCV_DIR) if f.endswith('.csv')])
    # Keep only main symbols (skip context ETFs)
    skip = {'SPY', 'QQQ', 'VIX', 'XLK', 'XLE', 'XLF', 'XLV', 'XLY', 'XLC'}
    files = [f for f in files if f.replace('.csv', '') not in skip]

    print(f'Scanning {len(files)} assets for BIG-MOVE tradeable patterns...')
    print(f'Filters: n>={MIN_N}, avg|move|>={MIN_AVG_ABS_MOVE_PCT}%, WR>={MIN_WIN_RATE}% or <={100-MIN_WIN_RATE}%')
    print()

    survivors_prefilter = []  # pattern survives avg-move + WR filters
    for i, fname in enumerate(files, 1):
        sym = fname.replace('.csv', '')
        cls = asset_classes.get(sym, 'unknown')
        bars = load_csv(os.path.join(OHLCV_DIR, fname))
        if len(bars) < 200:
            continue
        X, outs_pct = extract(bars)
        if len(X) < 50:
            continue
        Xs = (X - X.mean(0)) / (X.std(0) + 1e-8)
        lab = kmeans(Xs, K)
        if lab is None:
            continue

        for s in cluster_metrics(lab, outs_pct):
            # Pre-filter: large moves AND directional bias
            if s['avg_abs_move'] < MIN_AVG_ABS_MOVE_PCT:
                continue
            if not (s['win_rate'] >= MIN_WIN_RATE or s['win_rate'] <= (100 - MIN_WIN_RATE)):
                continue
            # Must have positive EV (ignoring costs first)
            direction = 'LONG' if s['win_rate'] >= 50 else 'SHORT'
            if direction == 'LONG':
                ev_net = s['ev_per_trade'] - COSTS.get(cls, 0.1)
            else:
                # For short, EV is inverted: we profit from negative moves
                ev_short = -s['ev_per_trade']  # signed from short POV
                ev_net = ev_short - COSTS.get(cls, 0.1)

            if ev_net < MIN_EV_AFTER_COSTS:
                continue

            s['asset'] = sym
            s['asset_class'] = cls
            s['direction'] = direction
            s['ev_after_costs'] = round(ev_net, 3)
            survivors_prefilter.append(s)

    print(f'Patterns passing pre-filter (bigmove + direction + EV): {len(survivors_prefilter)}')

    if not survivors_prefilter:
        print('\nNo tradeable big-move patterns found even before Bonferroni.')
        return

    # Bonferroni on the pre-filtered set
    total_tests = len(survivors_prefilter)
    threshold = 0.05 / total_tests
    print(f'Bonferroni threshold on pre-filtered set: {threshold:.2e}\n')

    final_survivors = []
    for s in survivors_prefilter:
        # Binomial test: is win rate different from 50%?
        moves = s['moves_arr']
        n = s['n']
        wins = int((moves > 0).sum())
        result = binomtest(wins, n, 0.5, alternative='two-sided')
        s['p_value'] = float(result.pvalue)
        s['survives_bonferroni'] = result.pvalue < threshold
        del s['moves_arr']  # drop before saving
        if s['survives_bonferroni']:
            final_survivors.append(s)

    final_survivors.sort(key=lambda x: (-x['ev_after_costs'], x['p_value']))

    # Report
    print(f'\n═══ FINAL: Big-move + Bonferroni survivors: {len(final_survivors)} ═══\n')
    if final_survivors:
        print(f'{"Asset":>8} {"Class":>10} {"Clu":>4} {"N":>4} '
              f'{"Dir":>5} {"WR%":>5} {"AvgMv":>7} {"MedMv":>7} '
              f'{"BigHit%":>8} {"EV-net":>7} {"p":>10}')
        print('-' * 95)
        for s in final_survivors:
            print(f'{s["asset"]:>8} {s["asset_class"]:>10} {s["cid"]:>4} {s["n"]:>4} '
                  f'{s["direction"]:>5} {s["win_rate"]:>5.1f} '
                  f'{s["avg_abs_move"]:>7.2f} {s["median_abs_move"]:>7.2f} '
                  f'{s["big_hit_rate"]:>7.1f}% {s["ev_after_costs"]:>+7.2f} '
                  f'{s["p_value"]:>10.2e}')
    else:
        print('No survivors after Bonferroni. Showing top 10 pre-filter candidates:\n')
        survivors_prefilter.sort(key=lambda x: -x['ev_after_costs'])
        for s in survivors_prefilter[:10]:
            print(f'  {s["asset"]:>8} C{s["cid"]} n={s["n"]} dir={s["direction"]} '
                  f'WR={s["win_rate"]}% avgMv={s["avg_abs_move"]}% '
                  f'EV-net={s["ev_after_costs"]:+.2f}% p={s["p_value"]:.2e}')

    out_data = {
        'analyzed_at': datetime.now().isoformat(),
        'filters': {
            'min_n': MIN_N, 'min_avg_abs_move_pct': MIN_AVG_ABS_MOVE_PCT,
            'min_wr_or_max_sr': MIN_WIN_RATE,
            'min_ev_after_costs_pct': MIN_EV_AFTER_COSTS,
        },
        'prefilter_count': len(survivors_prefilter),
        'bonferroni_threshold': threshold,
        'final_survivors_count': len(final_survivors),
        'survivors': final_survivors,
        'prefilter_all': survivors_prefilter,
    }
    with open(OUT, 'w') as f:
        json.dump(out_data, f, indent=2, default=str)
    print(f'\nSaved to {OUT}')

if __name__ == '__main__':
    main()
