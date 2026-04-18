#!/usr/bin/env python3
"""
Full-period trade simulation for the 4 multi-split-robust patterns.
Shows equity curve, monthly P&L, and realistic cash-flow numbers.
Position size: $10,000 per trade.
"""
import sys, os, json
sys.path.insert(0, '/Users/mariashchekanenko/claude-trading-tv/scripts')
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from datetime import datetime
from collections import defaultdict

from statistical_validation_v2 import load_csv, kmeans, WINDOW, LOOKAHEAD
from multi_split_validation import extract_with_idx, K, extract_triggers, matches_trigger

POSITION_SIZE = 10000
COST_PCT = 0.05  # EU/US stocks round-trip
OUT_CHART = '/Users/mariashchekanenko/claude-trading-tv/charts/full-period-simulation.png'

STRATEGIES = [
    ('BCS',   2,  'Barclays C2'),
    ('HSBC',  11, 'HSBC C11'),
    ('DNBBY', 2,  'DNB Bank C2'),
    ('BCS',   4,  'Barclays C4'),
]

def simulate(sym, cid):
    """Walk through all data, trade every time the cluster pattern triggers."""
    bars = load_csv(f'/Users/mariashchekanenko/claude-trading-tv/data/ohlcv/{sym}.csv')
    X, outs_pct, idxs, _ = extract_with_idx(bars)
    Xs = (X - X.mean(0)) / (X.std(0) + 1e-8)
    labels = kmeans(Xs, K)

    # Extract cluster triggers
    cluster_mask = labels == cid
    triggers = extract_triggers(X[cluster_mask])

    trades = []
    last_trade_idx = -LOOKAHEAD - 1
    for pos in range(len(idxs)):
        idx = idxs[pos]
        if idx - last_trade_idx < LOOKAHEAD:
            continue
        if matches_trigger(X[pos], triggers):
            entry_bar = bars[idx + WINDOW - 1]
            exit_bar = bars[idx + WINDOW - 1 + LOOKAHEAD]
            entry = entry_bar['close']
            exit_p = exit_bar['close']
            move_pct = (exit_p - entry) / entry * 100
            gross = POSITION_SIZE * move_pct / 100
            cost = POSITION_SIZE * COST_PCT / 100
            net = gross - cost
            trades.append({
                'entry_time': entry_bar['time'],
                'exit_time': exit_bar['time'],
                'entry': entry, 'exit': exit_p,
                'move_pct': move_pct,
                'gross': gross, 'cost': cost, 'net': net,
                'win': net > 0,
            })
            last_trade_idx = idx
    return bars, trades

def monthly_breakdown(trades):
    monthly = defaultdict(lambda: {'trades': 0, 'wins': 0, 'net': 0.0})
    for t in trades:
        key = t['entry_time'].strftime('%Y-%m')
        monthly[key]['trades'] += 1
        monthly[key]['net'] += t['net']
        if t['win']:
            monthly[key]['wins'] += 1
    return dict(sorted(monthly.items()))

def main():
    fig, axes = plt.subplots(4, 2, figsize=(20, 18))
    fig.patch.set_facecolor('#1e1e2e')

    overall_summary = []

    for row_idx, (sym, cid, label) in enumerate(STRATEGIES):
        print(f'\n═══ {label} ═══')
        bars, trades = simulate(sym, cid)
        n = len(trades)
        if n == 0:
            print('  No trades'); continue

        wins = sum(1 for t in trades if t['win'])
        total_net = sum(t['net'] for t in trades)
        wr = wins / n * 100
        avg_trade = total_net / n

        # Date span
        start = trades[0]['entry_time']
        end = trades[-1]['entry_time']
        months = (end - start).days / 30.4375
        trades_per_month = n / months
        monthly_pnl = total_net / months

        print(f'  Total trades: {n} | WR: {wr:.1f}% | Net: ${total_net:+,.2f}')
        print(f'  Avg per trade: ${avg_trade:+.2f}')
        print(f'  Period: {start.date()} to {end.date()} ({months:.1f} months)')
        print(f'  Trades/month: {trades_per_month:.1f} | $/month: ${monthly_pnl:+.2f}')

        overall_summary.append({
            'strategy': label, 'trades': n, 'win_rate': wr,
            'total_net': total_net, 'monthly_pnl': monthly_pnl,
            'trades_per_month': trades_per_month,
        })

        # LEFT plot: equity curve
        ax = axes[row_idx][0]
        ax.set_facecolor('#1e1e2e')
        cum = np.cumsum([t['net'] for t in trades])
        times = [t['entry_time'] for t in trades]
        color = '#26a69a' if total_net > 0 else '#ef5350'
        ax.plot(times, cum, color=color, linewidth=1.8)
        ax.fill_between(times, 0, cum, color=color, alpha=0.2)
        ax.axhline(y=0, color='#585b70', linewidth=0.8)
        ax.set_title(f'{label} — Equity Curve ${POSITION_SIZE:,}/trade\n'
                     f'{n} trades | WR {wr:.1f}% | Net ${total_net:+,.0f} | '
                     f'${monthly_pnl:+.0f}/month',
                     color='#cdd6f4', fontsize=12, fontweight='bold')
        ax.set_ylabel('Cumulative $ P&L', color='#cdd6f4')
        ax.tick_params(colors='#cdd6f4', labelsize=8)
        for s in ax.spines.values():
            s.set_color('#585b70')
        ax.grid(True, alpha=0.2, color='#585b70')

        # RIGHT plot: monthly P&L bars
        ax = axes[row_idx][1]
        ax.set_facecolor('#1e1e2e')
        monthly = monthly_breakdown(trades)
        months_list = list(monthly.keys())
        pnls = [monthly[m]['net'] for m in months_list]
        colors_bars = ['#26a69a' if p > 0 else '#ef5350' for p in pnls]
        x_pos = np.arange(len(months_list))
        ax.bar(x_pos, pnls, color=colors_bars, edgecolor='none')
        ax.axhline(y=0, color='#585b70', linewidth=0.8)
        ax.axhline(y=100*30, color='#f9e2af', linestyle='--', alpha=0.5,
                   label='$3000/mo target')
        ax.set_xticks(x_pos[::3])
        ax.set_xticklabels([months_list[i] for i in range(0, len(months_list), 3)],
                           rotation=45, ha='right', fontsize=7)
        ax.set_title(f'{label} — Monthly P&L',
                     color='#cdd6f4', fontsize=12, fontweight='bold')
        ax.set_ylabel('$ per month', color='#cdd6f4')
        ax.tick_params(colors='#cdd6f4', labelsize=8)
        for s in ax.spines.values():
            s.set_color('#585b70')
        ax.grid(True, alpha=0.2, color='#585b70', axis='y')
        ax.legend(facecolor='#1e1e2e', edgecolor='#585b70', labelcolor='#cdd6f4', fontsize=8)

    fig.suptitle(f'Full-Period Trade Simulation — ${POSITION_SIZE:,} position per trade, '
                 f'{COST_PCT}% round-trip cost',
                 color='#cdd6f4', fontsize=16, fontweight='bold', y=0.998)
    plt.subplots_adjust(hspace=0.55, wspace=0.2, top=0.96)
    fig.savefig(OUT_CHART, dpi=120, bbox_inches='tight', facecolor='#1e1e2e')
    plt.close(fig)
    print(f'\nSaved {OUT_CHART}')

    # Portfolio totals
    print(f'\n═══ PORTFOLIO (all 4 running in parallel, ${POSITION_SIZE:,} per trade) ═══')
    total_monthly = sum(s['monthly_pnl'] for s in overall_summary)
    total_n = sum(s['trades'] for s in overall_summary)
    print(f'Combined trades per month: {sum(s["trades_per_month"] for s in overall_summary):.1f}')
    print(f'Combined monthly P&L: ${total_monthly:+,.2f}')
    print(f'Against $3,000/month target: {total_monthly/3000*100:.0f}%')
    print(f'\nPer-strategy breakdown:')
    for s in overall_summary:
        print(f'  {s["strategy"]:20} {s["trades"]:4} trades | '
              f'WR {s["win_rate"]:.0f}% | ${s["monthly_pnl"]:+7.2f}/month')

if __name__ == '__main__':
    main()
