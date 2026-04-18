#!/usr/bin/env python3
"""
OOS backtest of 4 v5 crypto Bonferroni survivors.
Rules derived from actual cluster characteristics (corrected).

XRPUSD C1 LONG — "Deep oversold bounce"
  RSI <= 40, EMA20_dist <= -3, EMA50_dist <= -3

ADAUSD C9 LONG — "Funding-driven short crowd"
  40 <= RSI <= 52, -1.0 <= EMA20_dist <= 0.5,
  funding_now <= -0.010%, funding_change_1d <= -0.010

XRPUSD C10 SHORT — "Mild overbought on weekdays"
  48 <= RSI <= 60, 0 <= EMA20_dist <= 0.8, weekday in [1..5]

XRPUSD C0 LONG — "Volatile oversold"
  RSI <= 42, EMA20_dist <= -0.5, range/ATR >= 1.3
"""
import sys, os, json, csv, bisect
sys.path.insert(0, '/Users/mariashchekanenko/claude-trading-tv/scripts')
import numpy as np
from datetime import datetime
from statistical_validation_v2 import load_csv, precompute_indicators
from statistical_validation_v5_crypto import ASSET_FUNDING

OHLCV_DIR = '/Users/mariashchekanenko/claude-trading-tv/data/ohlcv'
FUNDING_DIR = '/Users/mariashchekanenko/claude-trading-tv/data/funding'
OUT = '/Users/mariashchekanenko/claude-trading-tv/data/backtest-v5-crypto.json'
LOOKAHEAD = 5
TRAIN_FRAC = 0.70

# Crypto trading costs (Binance spot maker/taker)
# Round-trip: 0.1% taker × 2 = 0.2% — using 0.15% as conservative spot+fee
TRADING_COST_PCT = 0.15

def load_funding_series(symbol):
    """Returns (ts_list_seconds, rate_array)."""
    path = os.path.join(FUNDING_DIR, f'{symbol}.csv')
    ts_list, rates = [], []
    with open(path) as f:
        for r in csv.DictReader(f):
            try:
                ts_list.append(int(r['funding_time']) // 1000)
                rates.append(float(r['funding_rate']))
            except (ValueError, KeyError):
                continue
    return np.array(ts_list), np.array(rates)

def funding_lookback(ts_arr, rates, ts_seconds, n_periods=1):
    """Get most recent funding at or before ts, optionally over window."""
    idx = bisect.bisect_right(ts_arr, ts_seconds) - 1
    if idx < 0:
        return None, None
    if n_periods > 1:
        start = max(0, idx - n_periods + 1)
        return rates[idx], rates[start:idx+1]
    return rates[idx], rates[idx:idx+1]

def build_rows(bars, asset):
    """Per-bar feature dict."""
    ind = precompute_indicators(bars)
    funding_key = ASSET_FUNDING.get(asset)
    ts_arr, rates = load_funding_series(funding_key) if funding_key else (None, None)

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
        row = {
            'rsi': rsi,
            'ema20_dist': (close - e20) / e20 * 100,
            'ema50_dist': (close - e50) / e50 * 100,
            'range_atr': (bars[i]['high'] - bars[i]['low']) / atr,
            'hour': bars[i]['time'].hour,
            'weekday': bars[i]['time'].weekday(),
        }
        if ts_arr is not None:
            ts = int(bars[i]['time'].timestamp())
            current, _ = funding_lookback(ts_arr, rates, ts)
            prev, _ = funding_lookback(ts_arr, rates, ts - 24 * 3600)
            row['funding_now'] = (current * 100) if current is not None else 0
            row['funding_change_1d'] = ((current - prev) * 100) if (current is not None and prev is not None) else 0
        else:
            row['funding_now'] = 0
            row['funding_change_1d'] = 0
        rows.append(row)
    return rows

# Rules
def xrp_c1_long(r):
    return r['rsi'] <= 40 and r['ema20_dist'] <= -3.0 and r['ema50_dist'] <= -3.0

def ada_c9_long(r):
    return (40 <= r['rsi'] <= 52 and
            -1.0 <= r['ema20_dist'] <= 0.5 and
            r['funding_now'] <= -0.010 and
            r['funding_change_1d'] <= -0.010)

def xrp_c10_short(r):
    return (48 <= r['rsi'] <= 60 and
            0 <= r['ema20_dist'] <= 0.8 and
            1 <= r['weekday'] <= 5)

def xrp_c0_long(r):
    return r['rsi'] <= 42 and r['ema20_dist'] <= -0.5 and r['range_atr'] >= 1.3

STRATEGIES = {
    'XRPUSD_C1_LONG_oversold_bounce': {'sym': 'XRPUSD', 'side': 'LONG', 'check': xrp_c1_long},
    'ADAUSD_C9_LONG_funding_squeeze':  {'sym': 'ADAUSD', 'side': 'LONG', 'check': ada_c9_long},
    'XRPUSD_C10_SHORT_mild_overbought': {'sym': 'XRPUSD', 'side': 'SHORT', 'check': xrp_c10_short},
    'XRPUSD_C0_LONG_volatile_oversold': {'sym': 'XRPUSD', 'side': 'LONG', 'check': xrp_c0_long},
}

def run(bars, rows, side, check, start, end):
    trades = []
    i = start
    while i < end - LOOKAHEAD:
        r = rows[i]
        if r is None:
            i += 1; continue
        if check(r):
            entry = bars[i]['close']
            exit_p = bars[i + LOOKAHEAD]['close']
            raw = (exit_p - entry) / entry * 100
            if side == 'SHORT':
                raw = -raw
            net = raw - TRADING_COST_PCT
            trades.append({
                'time': bars[i]['time'].strftime('%Y-%m-%d %H:%M'),
                'side': side, 'entry': entry, 'exit': exit_p,
                'raw_pct': raw, 'net_pct': net, 'win': net > 0,
            })
            i += LOOKAHEAD
        else:
            i += 1
    return trades

def metrics(trades):
    if not trades:
        return {'n_trades': 0}
    n = len(trades)
    wins = sum(1 for t in trades if t['win'])
    total = sum(t['net_pct'] for t in trades)
    sum_w = sum(t['net_pct'] for t in trades if t['win'])
    sum_l = sum(abs(t['net_pct']) for t in trades if not t['win'])
    pf = sum_w / sum_l if sum_l else float('inf')
    eq = np.cumsum([t['net_pct'] for t in trades])
    max_dd = float((np.maximum.accumulate(eq) - eq).max()) if len(eq) else 0
    return {
        'n_trades': n,
        'win_rate': round(wins / n * 100, 1),
        'total_return_pct': round(total, 3),
        'profit_factor': round(pf, 2),
        'max_drawdown_pct': round(max_dd, 3),
        'avg_trade_pct': round(total / n, 3),
    }

def main():
    results = {}
    for name, cfg in STRATEGIES.items():
        sym = cfg['sym']
        path = os.path.join(OHLCV_DIR, f'{sym}.csv')
        bars = load_csv(path)
        rows = build_rows(bars, sym)
        split = int(len(bars) * TRAIN_FRAC)
        train_t = run(bars, rows, cfg['side'], cfg['check'], 0, split)
        test_t = run(bars, rows, cfg['side'], cfg['check'], split, len(bars))
        train_m = metrics(train_t)
        test_m = metrics(test_t)

        print(f'\n══════ {name} ══════')
        print(f'Split at {bars[split]["time"]} | trading cost: {TRADING_COST_PCT}% per trade')
        print(f'  TRAIN: {train_m["n_trades"]} trades | WR {train_m.get("win_rate","-")}% | '
              f'return {train_m.get("total_return_pct","-")}% | PF {train_m.get("profit_factor","-")}')
        print(f'  TEST:  {test_m["n_trades"]} trades | WR {test_m.get("win_rate","-")}% | '
              f'return {test_m.get("total_return_pct","-")}% | PF {test_m.get("profit_factor","-")}')

        results[name] = {
            'symbol': sym, 'side': cfg['side'],
            'train_metrics': train_m, 'test_metrics': test_m,
            'test_trades': test_t,
        }

    # Verdict
    print(f'\n══════ VERDICT ══════')
    for name, r in results.items():
        tm = r['test_metrics']
        if tm.get('n_trades', 0) == 0:
            status = '❌ NO TRIGGERS OOS'
        elif tm['win_rate'] > 52 and tm['total_return_pct'] > 0:
            status = '✅ HOLDS OOS'
        else:
            status = '❌ FAILS OOS'
        print(f'{name:45} {status} | WR {tm.get("win_rate","-")}% | '
              f'return {tm.get("total_return_pct","-")}%')

    with open(OUT, 'w') as f:
        json.dump({
            'analyzed_at': datetime.now().isoformat(),
            'trading_cost_pct_round_trip': TRADING_COST_PCT,
            'train_fraction': TRAIN_FRAC,
            'strategies': results,
        }, f, indent=2, default=str)
    print(f'\nSaved to {OUT}')

if __name__ == '__main__':
    main()
