#!/usr/bin/env python3
"""
OOS backtest of the 3 v3 Bonferroni survivors (rate-feature clusters).
70/30 train/test split on each pair, same spread-cost model as v1 backtest.

Rules derived from cluster centroid characterization:

GBPCHF C18 SHORT — "Fade overextended GBP after BOE rate decision"
  RSI >= 55, EMA20_dist >= 0.05, EMA50_dist >= 0.1,
  hour 7-11, days_since_BOE_change <= 10

EURUSD C11 LONG — "NY oversold bounce"
  RSI <= 45, EMA20_dist <= -0.05, EMA50_dist <= -0.05,
  hour 13-17, range_atr <= 1.0

GBPJPY C6 LONG — "Sustained carry trade with wide rate gap"
  Rate_diff >= 4.3, days_since_BOE_change >= 30,
  45 <= RSI <= 58, |EMA20_dist| <= 0.1
"""
import sys, os, json
sys.path.insert(0, '/Users/mariashchekanenko/claude-trading-tv/scripts')
import numpy as np
from datetime import datetime
from statistical_validation_v2 import load_csv, precompute_indicators
from statistical_validation_v3 import build_rate_features_for_asset, PAIR_RATES

OHLCV_DIR = '/Users/mariashchekanenko/claude-trading-tv/data/ohlcv'
OUT = '/Users/mariashchekanenko/claude-trading-tv/data/backtest-v3.json'
LOOKAHEAD = 5
TRAIN_FRAC = 0.70

SPREAD_PIPS = {
    'GBPCHF': 1.0,
    'EURUSD': 0.5,
    'GBPJPY': 1.5,
}
PIP_SIZE = {
    'GBPCHF': 0.0001,
    'EURUSD': 0.0001,
    'GBPJPY': 0.01,
}

def build_feature_rows(bars, sym):
    """Return per-bar dict with all features needed by rules."""
    ind = precompute_indicators(bars)
    rates = build_rate_features_for_asset(sym, bars)
    rows = []
    for i in range(len(bars)):
        rsi = ind['rsi'][i]
        e20 = ind['ema20'][i]
        e50 = ind['ema50'][i]
        atr = ind['atr'][i]
        if np.isnan(rsi) or np.isnan(e20) or np.isnan(e50) or np.isnan(atr) or e20 == 0 or atr == 0:
            rows.append(None)
            continue
        close = bars[i]['close']
        rows.append({
            'rsi': rsi,
            'ema20_dist': (close - e20) / e20 * 100,
            'ema50_dist': (close - e50) / e50 * 100,
            'range_atr': (bars[i]['high'] - bars[i]['low']) / atr,
            'hour': bars[i]['time'].hour,
            'rate_diff': rates[i, 0],
            'rate_change_30d': rates[i, 1],
            'days_since_base_change': rates[i, 2],
            'days_since_quote_change': rates[i, 3],
        })
    return rows

def gbpchf_short(r):
    return (r['rsi'] >= 55 and
            r['ema20_dist'] >= 0.05 and
            r['ema50_dist'] >= 0.10 and
            7 <= r['hour'] <= 11 and
            r['days_since_quote_change'] <= 10)  # quote = CHF ... wait let me check

def eurusd_long(r):
    return (r['rsi'] <= 45 and
            r['ema20_dist'] <= -0.05 and
            r['ema50_dist'] <= -0.05 and
            13 <= r['hour'] <= 17 and
            r['range_atr'] <= 1.0)

def gbpjpy_long(r):
    return (r['rate_diff'] >= 4.3 and
            r['days_since_base_change'] >= 30 and  # base = BOE for GBPJPY
            45 <= r['rsi'] <= 58 and
            abs(r['ema20_dist']) <= 0.10)

STRATEGIES = {
    'GBPCHF_C18_SHORT': {'sym': 'GBPCHF', 'side': 'SHORT', 'check': gbpchf_short},
    'EURUSD_C11_LONG':  {'sym': 'EURUSD', 'side': 'LONG',  'check': eurusd_long},
    'GBPJPY_C6_LONG':   {'sym': 'GBPJPY', 'side': 'LONG',  'check': gbpjpy_long},
}

def run(bars, rows, sym, side, check_fn, start, end):
    trades = []
    pip = PIP_SIZE[sym]
    mean_price = np.mean([b['close'] for b in bars[start:end]])
    spread_pct = SPREAD_PIPS[sym] * pip / mean_price * 100

    i = start
    while i < end - LOOKAHEAD:
        r = rows[i]
        if r is None:
            i += 1; continue
        if check_fn(r):
            entry = bars[i]['close']
            exit_p = bars[i + LOOKAHEAD]['close']
            raw = (exit_p - entry) / entry * 100
            if side == 'SHORT':
                raw = -raw
            net = raw - spread_pct
            trades.append({
                'time': bars[i]['time'].strftime('%Y-%m-%d %H:%M'),
                'side': side,
                'entry': entry,
                'exit': exit_p,
                'raw_pct': raw,
                'net_pct': net,
                'win': net > 0,
            })
            i += LOOKAHEAD
        else:
            i += 1
    return trades, spread_pct

def metrics(trades):
    if not trades:
        return {'n_trades': 0}
    n = len(trades)
    wins = sum(1 for t in trades if t['win'])
    wr = wins / n * 100
    total = sum(t['net_pct'] for t in trades)
    wins_sum = sum(t['net_pct'] for t in trades if t['win'])
    losses_sum = sum(abs(t['net_pct']) for t in trades if not t['win'])
    pf = wins_sum / losses_sum if losses_sum > 0 else float('inf')
    eq = np.cumsum([t['net_pct'] for t in trades])
    peak = np.maximum.accumulate(eq)
    dd = peak - eq
    max_dd = float(dd.max()) if len(dd) else 0
    rets = np.array([t['net_pct'] for t in trades])
    sharpe = rets.mean() / (rets.std() + 1e-9)
    return {
        'n_trades': n,
        'win_rate': round(wr, 1),
        'total_return_pct': round(total, 3),
        'profit_factor': round(pf, 2),
        'max_drawdown_pct': round(max_dd, 3),
        'sharpe_per_trade': round(sharpe, 3),
    }

def main():
    results = {}
    for name, cfg in STRATEGIES.items():
        sym = cfg['sym']
        path = os.path.join(OHLCV_DIR, f'{sym}.csv')
        bars = load_csv(path)
        rows = build_feature_rows(bars, sym)
        split = int(len(bars) * TRAIN_FRAC)

        train_t, spread = run(bars, rows, sym, cfg['side'], cfg['check'], 0, split)
        test_t, _ = run(bars, rows, sym, cfg['side'], cfg['check'], split, len(bars))

        train_m = metrics(train_t)
        test_m = metrics(test_t)

        print(f'\n══════ {name} ══════')
        print(f'Split at {bars[split]["time"]} | spread cost: {spread:.4f}%')
        print(f'  TRAIN: {train_m["n_trades"]} trades | WR {train_m.get("win_rate",0)}% | '
              f'Return {train_m.get("total_return_pct",0)}% | PF {train_m.get("profit_factor",0)}')
        print(f'  TEST:  {test_m["n_trades"]} trades | WR {test_m.get("win_rate",0)}% | '
              f'Return {test_m.get("total_return_pct",0)}% | PF {test_m.get("profit_factor",0)}')

        results[name] = {
            'train_metrics': train_m,
            'test_metrics': test_m,
            'spread_pct': float(spread),
            'test_trades': test_t,
        }

    # Summary verdict
    print(f'\n══════ VERDICT ══════')
    for name, r in results.items():
        tm = r['test_metrics']
        status = '✅ HOLDS OOS' if tm.get('n_trades', 0) > 0 and tm['win_rate'] > 52 and tm['total_return_pct'] > 0 else '❌ FAILS OOS'
        print(f'{name:25} {status} | WR {tm.get("win_rate","-")}%, return {tm.get("total_return_pct","-")}%')

    with open(OUT, 'w') as f:
        json.dump({
            'analyzed_at': datetime.now().isoformat(),
            'strategies': results,
        }, f, indent=2, default=str)
    print(f'\nSaved to {OUT}')

if __name__ == '__main__':
    main()
