#!/usr/bin/env python3
"""
Out-of-sample backtest of the forex mean-reversion rule.

Train period: first 70% of data (used to derive the rule)
Test period: last 30% (out-of-sample — the real test)

Rule (rule-based, no K-Means needed at runtime):
LONG entry:
  - RSI(14) <= 50
  - close <= EMA20 (within 0.1% below)
  - bar range <= 1.0 × ATR(14)
  - hour UTC in [18, 22]

SHORT entry:
  - RSI(14) >= 55
  - close >= EMA20 (within 0.2% above)
  - bar range >= 1.0 × ATR(14)
  - hour UTC in [9, 16]

Exit: 5 bars later (close).
Spread costs: 0.5 pip applied per round-trip.
"""
import sys, os, csv, json
sys.path.insert(0, '/Users/mariashchekanenko/claude-trading-tv/scripts')
import numpy as np
from datetime import datetime
from statistical_validation_v2 import load_csv, precompute_indicators

OHLCV_DIR = '/Users/mariashchekanenko/claude-trading-tv/data/ohlcv'
OUT = '/Users/mariashchekanenko/claude-trading-tv/data/backtest-meanrev.json'

LOOKAHEAD = 5
TRAIN_FRAC = 0.70

# Spread costs in pips per round-trip
SPREAD_PIPS = {
    'EURGBP': 0.7,
    'EURJPY': 1.5,
    'USDCHF': 0.7,
}
# Pip size per pair
PIP_SIZE = {
    'EURGBP': 0.0001,
    'EURJPY': 0.01,   # JPY pairs use 2 decimals
    'USDCHF': 0.0001,
}

def long_signal(row):
    return (
        row['rsi'] <= 50 and
        row['ema20_dist'] <= 0.001 and  # at or below EMA20
        row['ema20_dist'] >= -0.20 and  # not too far below
        row['range_atr'] <= 1.0 and
        18 <= row['hour'] <= 22
    )

def short_signal(row):
    return (
        row['rsi'] >= 55 and
        row['ema20_dist'] >= -0.001 and
        row['ema20_dist'] <= 0.20 and
        row['range_atr'] >= 1.0 and
        9 <= row['hour'] <= 16
    )

def build_signal_rows(bars):
    """For each bar, build a feature row used for signal evaluation."""
    ind = precompute_indicators(bars)
    rows = []
    for i in range(len(bars)):
        rsi = ind['rsi'][i]
        e20 = ind['ema20'][i]
        atr = ind['atr'][i]
        if np.isnan(rsi) or np.isnan(e20) or np.isnan(atr) or e20 == 0 or atr == 0:
            rows.append(None)
            continue
        rows.append({
            'rsi': rsi,
            'ema20_dist': (bars[i]['close'] - e20) / e20 * 100,
            'range_atr': (bars[i]['high'] - bars[i]['low']) / atr,
            'hour': bars[i]['time'].hour,
        })
    return rows

def run_backtest(bars, signal_rows, sym, start_idx, end_idx):
    """Walk through bars[start_idx:end_idx], collect trades."""
    trades = []
    pip = PIP_SIZE[sym]
    spread_cost_pct = SPREAD_PIPS[sym] * pip / np.mean([b['close'] for b in bars[start_idx:end_idx]]) * 100

    i = start_idx
    while i < end_idx - LOOKAHEAD:
        row = signal_rows[i]
        if row is None:
            i += 1
            continue

        side = None
        if long_signal(row):
            side = 'LONG'
        elif short_signal(row):
            side = 'SHORT'

        if side:
            entry = bars[i]['close']
            exit_p = bars[i + LOOKAHEAD]['close']
            raw_pct = (exit_p - entry) / entry * 100
            if side == 'SHORT':
                raw_pct = -raw_pct
            net_pct = raw_pct - spread_cost_pct  # round-trip spread

            trades.append({
                'time': bars[i]['time'].strftime('%Y-%m-%d %H:%M'),
                'side': side,
                'entry': entry,
                'exit': exit_p,
                'raw_pct': raw_pct,
                'net_pct': net_pct,
                'win': net_pct > 0,
            })
            i += LOOKAHEAD  # skip overlap
        else:
            i += 1

    return trades, spread_cost_pct

def metrics(trades):
    if not trades:
        return {'n_trades': 0}
    n = len(trades)
    wins = sum(1 for t in trades if t['win'])
    win_rate = wins / n * 100
    avg_win = np.mean([t['net_pct'] for t in trades if t['win']]) if wins else 0
    losses = [t['net_pct'] for t in trades if not t['win']]
    avg_loss = np.mean(losses) if losses else 0
    total_pct = sum(t['net_pct'] for t in trades)

    # Profit factor = sum(wins) / |sum(losses)|
    sum_wins = sum(t['net_pct'] for t in trades if t['win'])
    sum_losses = sum(abs(t['net_pct']) for t in trades if not t['win'])
    pf = sum_wins / sum_losses if sum_losses else float('inf')

    # Equity curve & max drawdown
    eq = np.cumsum([t['net_pct'] for t in trades])
    peak = np.maximum.accumulate(eq)
    dd = peak - eq
    max_dd = float(dd.max()) if len(dd) else 0

    # Sharpe-ish (per trade, not annualized)
    rets = np.array([t['net_pct'] for t in trades])
    sharpe_per_trade = rets.mean() / (rets.std() + 1e-9)

    return {
        'n_trades': n,
        'win_rate': round(win_rate, 1),
        'avg_win_pct': round(avg_win, 4),
        'avg_loss_pct': round(avg_loss, 4),
        'total_return_pct': round(total_pct, 3),
        'profit_factor': round(pf, 2),
        'max_drawdown_pct': round(max_dd, 3),
        'sharpe_per_trade': round(sharpe_per_trade, 3),
        'long_trades': sum(1 for t in trades if t['side'] == 'LONG'),
        'short_trades': sum(1 for t in trades if t['side'] == 'SHORT'),
    }

def backtest_symbol(sym):
    print(f'\n══════════ {sym} ══════════')
    path = os.path.join(OHLCV_DIR, f'{sym}.csv')
    bars = load_csv(path)
    if len(bars) < 200:
        return None

    rows = build_signal_rows(bars)
    split_idx = int(len(bars) * TRAIN_FRAC)
    print(f'Total bars: {len(bars)}, split at {split_idx} ({bars[split_idx]["time"]})')

    train_trades, spread = run_backtest(bars, rows, sym, 0, split_idx)
    test_trades, _ = run_backtest(bars, rows, sym, split_idx, len(bars))

    train_m = metrics(train_trades)
    test_m = metrics(test_trades)

    print(f'Spread cost per trade: {spread:.4f}%')
    print(f'\n  TRAIN (first 70%): {train_m["n_trades"]} trades')
    if train_m['n_trades']:
        print(f'    WR: {train_m["win_rate"]}%, Total: {train_m["total_return_pct"]}%, '
              f'PF: {train_m["profit_factor"]}, MaxDD: {train_m["max_drawdown_pct"]}%')

    print(f'\n  TEST (last 30%, OUT-OF-SAMPLE): {test_m["n_trades"]} trades')
    if test_m['n_trades']:
        print(f'    WR: {test_m["win_rate"]}%, Total: {test_m["total_return_pct"]}%, '
              f'PF: {test_m["profit_factor"]}, MaxDD: {test_m["max_drawdown_pct"]}%')
        print(f'    Long: {test_m["long_trades"]}, Short: {test_m["short_trades"]}')

    return {
        'symbol': sym,
        'spread_cost_pct': float(spread),
        'split_index': split_idx,
        'split_date': str(bars[split_idx]['time']),
        'train_metrics': train_m,
        'test_metrics': test_m,
        'test_trades': test_trades,
    }

def main():
    results = {}
    for sym in ['EURGBP', 'EURJPY', 'USDCHF']:
        r = backtest_symbol(sym)
        if r:
            results[sym] = r

    # Combined (out-of-sample only)
    print(f'\n══════════ COMBINED OUT-OF-SAMPLE ══════════')
    all_trades = []
    for sym, r in results.items():
        all_trades.extend(r['test_trades'])
    combined = metrics(all_trades)
    print(f'Total trades: {combined["n_trades"]}')
    if combined['n_trades']:
        print(f'WR: {combined["win_rate"]}%, Total return: {combined["total_return_pct"]}%')
        print(f'Profit factor: {combined["profit_factor"]}')
        print(f'Max drawdown: {combined["max_drawdown_pct"]}%')
        print(f'Avg win: {combined["avg_win_pct"]}%, Avg loss: {combined["avg_loss_pct"]}%')
        print(f'Sharpe (per trade): {combined["sharpe_per_trade"]}')

    out = {
        'analyzed_at': datetime.now().isoformat(),
        'rule': 'mean-reversion forex (RSI + EMA20 + ATR + hour)',
        'train_fraction': TRAIN_FRAC,
        'lookahead_bars': LOOKAHEAD,
        'symbols': results,
        'combined_test': combined,
    }
    with open(OUT, 'w') as f:
        json.dump(out, f, indent=2, default=str)
    print(f'\nResults saved to {OUT}')

if __name__ == '__main__':
    main()
