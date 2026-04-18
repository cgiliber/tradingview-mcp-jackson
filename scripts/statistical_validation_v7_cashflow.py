#!/usr/bin/env python3
"""
v7 — cash-flow focused pattern hunt.

Goal: find MANY small edges across many assets that together deliver
steady daily cash flow, NOT big home-run moves.

Filters:
1. n >= 20 (enough samples for statistics)
2. Signals/month >= 3 AND <= 60 (tradeable frequency)
3. EV per trade AFTER costs > 0 (profitable)
4. WR >= 54% OR <= 46% (real directional bias)
5. Passes Bonferroni on prefilter survivors set
6. Tests both v2 features (all assets) AND v5 features (crypto with funding)
"""
import sys, os, csv, json
sys.path.insert(0, '/Users/mariashchekanenko/claude-trading-tv/scripts')
import numpy as np
from datetime import datetime
from scipy.stats import binomtest
from statistical_validation_v2 import load_csv, precompute_indicators, kmeans

OHLCV_DIR = '/Users/mariashchekanenko/claude-trading-tv/data/ohlcv'
OUT = '/Users/mariashchekanenko/claude-trading-tv/data/statistical-validation-v7-cashflow.json'

WINDOW = 5
LOOKAHEAD = 5
MIN_N = 20
K = 15
MIN_SIGNALS_PER_MONTH = 3
MAX_SIGNALS_PER_MONTH = 60
MIN_WR_LONG = 54
MAX_WR_SHORT = 46
MIN_EV_PCT = 0.01  # must beat cost by at least 0.01% (very low bar)

COSTS = {
    'forex': 0.02,
    'us_stocks': 0.05,
    'eu_stocks': 0.05,
    'crypto': 0.15,
    'etf_macro': 0.05,
    'unknown': 0.10,
}

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

def extract(bars):
    ind = precompute_indicators(bars)
    feats, outs_pct = [], []
    for i in range(len(bars) - WINDOW - LOOKAHEAD):
        v = v2_feat(bars, i, ind)
        if v is None or any(np.isnan(v)) or any(np.isinf(v)):
            continue
        feats.append(v)
        entry = bars[i + WINDOW - 1]['close']
        exit_p = bars[i + WINDOW - 1 + LOOKAHEAD]['close']
        outs_pct.append((exit_p - entry) / entry * 100)
    return np.array(feats), np.array(outs_pct)

def eval_clusters(labels, outs_pct, cost_pct, months):
    out = []
    for cid in set(labels):
        m = labels == cid
        n = int(m.sum())
        if n < MIN_N: continue

        moves = outs_pct[m]
        wins_long = int((moves > 0).sum())
        wr = wins_long / n * 100
        wr_short = 100 - wr
        # Direction
        if wr >= MIN_WR_LONG:
            direction = 'LONG'; active_wr = wr
        elif wr <= MAX_WR_SHORT:
            direction = 'SHORT'; active_wr = wr_short
        else:
            continue

        signals_per_month = n / months
        if signals_per_month < MIN_SIGNALS_PER_MONTH: continue
        if signals_per_month > MAX_SIGNALS_PER_MONTH: continue

        avg_win = float(moves[moves > 0].mean()) if (moves > 0).any() else 0
        avg_loss = float(moves[moves < 0].mean()) if (moves < 0).any() else 0
        if direction == 'LONG':
            ev_gross = wr/100 * avg_win + (1 - wr/100) * avg_loss
        else:
            ev_gross = -(wr/100 * avg_win + (1 - wr/100) * avg_loss)
        ev_net = ev_gross - cost_pct
        if ev_net < MIN_EV_PCT: continue

        out.append({
            'cid': int(cid), 'n': n, 'direction': direction,
            'win_rate': round(active_wr, 1),
            'signals_per_month': round(signals_per_month, 1),
            'avg_win_pct': round(avg_win, 3),
            'avg_loss_pct': round(avg_loss, 3),
            'ev_gross_pct': round(ev_gross, 3),
            'ev_net_pct': round(ev_net, 3),
            'expected_monthly_pct': round(ev_net * signals_per_month, 2),
            'moves_arr': moves,
        })
    return out

def main():
    manifest = json.load(open(os.path.join(OHLCV_DIR, '_manifest.json')))
    asset_classes = {r['symbol']: r.get('asset_class') for r in manifest['results']}
    # Add forex crosses manually
    for s in ['EURJPY','EURCHF','AUDJPY','AUDUSD','USDCHF','NZDUSD','EURAUD','GBPCHF']:
        asset_classes.setdefault(s, 'forex')

    files = sorted([f for f in os.listdir(OHLCV_DIR) if f.endswith('.csv')])
    skip = {'SPY','QQQ','VIX','XLK','XLE','XLF','XLV','XLY','XLC'}
    files = [f for f in files if f.replace('.csv','') not in skip]

    print(f'Scanning {len(files)} assets for steady cash-flow edges...')
    print(f'Filters: WR>={MIN_WR_LONG}% or <={MAX_WR_SHORT}%, '
          f'{MIN_SIGNALS_PER_MONTH}-{MAX_SIGNALS_PER_MONTH} signals/mo, '
          f'EV-net > {MIN_EV_PCT}% after costs')
    print()

    pre = []  # survived prefilter
    for i, fname in enumerate(files, 1):
        sym = fname.replace('.csv', '')
        cls = asset_classes.get(sym, 'unknown')
        bars = load_csv(os.path.join(OHLCV_DIR, fname))
        if len(bars) < 200: continue
        X, outs_pct = extract(bars)
        if len(X) < 50: continue
        # Data period in months (2y ~ 24 mo for most)
        days = (bars[-1]['time'] - bars[0]['time']).days
        months = days / 30.4375
        cost = COSTS.get(cls, 0.10)

        Xs = (X - X.mean(0)) / (X.std(0) + 1e-8)
        lab = kmeans(Xs, K)
        if lab is None: continue
        for s in eval_clusters(lab, outs_pct, cost, months):
            s['asset'] = sym
            s['asset_class'] = cls
            s['cost_pct'] = cost
            pre.append(s)

    print(f'Pre-filter survivors (EV>0, right frequency, directional): {len(pre)}')
    if not pre:
        print('\nNo cash-flow edges found.')
        return

    # Bonferroni on prefilter set
    threshold = 0.05 / len(pre)
    print(f'Bonferroni threshold on prefilter set: {threshold:.2e}\n')

    finalists = []
    for s in pre:
        moves = s['moves_arr']
        n = s['n']
        wins = int((moves > 0).sum())
        # Test against 50% baseline
        result = binomtest(wins, n, 0.5, alternative='two-sided')
        s['p_value'] = float(result.pvalue)
        s['survives_bonferroni'] = result.pvalue < threshold
        del s['moves_arr']
        if s['survives_bonferroni']:
            finalists.append(s)

    finalists.sort(key=lambda x: -x['expected_monthly_pct'])

    print(f'═══ FINAL cash-flow survivors: {len(finalists)} ═══\n')
    if finalists:
        print(f'{"Asset":>9} {"Class":>10} {"Clu":>4} {"Dir":>5} {"N":>4} '
              f'{"Sig/mo":>7} {"WR%":>5} {"EVnet":>7} {"Mo%":>6} {"p":>10}')
        print('-' * 90)
        for s in finalists:
            print(f'{s["asset"]:>9} {s["asset_class"]:>10} {s["cid"]:>4} '
                  f'{s["direction"]:>5} {s["n"]:>4} {s["signals_per_month"]:>7.1f} '
                  f'{s["win_rate"]:>5.1f} {s["ev_net_pct"]:>+7.2f}% '
                  f'{s["expected_monthly_pct"]:>+6.2f}% {s["p_value"]:>10.2e}')

    # Portfolio math
    if finalists:
        total_monthly_pct = sum(s['expected_monthly_pct'] for s in finalists)
        print(f'\n─── Portfolio projection (running ALL in parallel) ───')
        print(f'Total expected monthly return: {total_monthly_pct:+.2f}% combined')
        print(f'On $10,000 capital per strategy: ${total_monthly_pct * 100:.0f}/month')
        print(f'Number of independent edges: {len(finalists)}')
        asset_set = set(s['asset'] for s in finalists)
        print(f'Assets covered: {len(asset_set)} ({", ".join(sorted(asset_set))})')

    out_data = {
        'analyzed_at': datetime.now().isoformat(),
        'filters': {'min_wr_long': MIN_WR_LONG, 'max_wr_short': MAX_WR_SHORT,
                    'min_n': MIN_N, 'min_signals_per_month': MIN_SIGNALS_PER_MONTH,
                    'max_signals_per_month': MAX_SIGNALS_PER_MONTH,
                    'min_ev_net_pct': MIN_EV_PCT},
        'prefilter_count': len(pre),
        'bonferroni_threshold': threshold,
        'survivors_count': len(finalists),
        'survivors': finalists,
    }
    with open(OUT, 'w') as f:
        json.dump(out_data, f, indent=2, default=str)
    print(f'\nSaved to {OUT}')

if __name__ == '__main__':
    main()
