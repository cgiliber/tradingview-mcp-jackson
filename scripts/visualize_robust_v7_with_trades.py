#!/usr/bin/env python3
"""
Same 6 examples per pattern as before, but each cell shows the actual trade
simulation: entry, exit, $ gained/lost, position size, trading costs.

Simulation assumptions:
- Position size: $10,000 per trade (standard)
- Trading cost: 0.05% round-trip for stocks ($5 per trade)
- Direction: LONG (buy at pattern close, sell 5 bars later)
- No stop loss — pure time-based exit (5 hours)
"""
import sys, os
sys.path.insert(0, '/Users/mariashchekanenko/claude-trading-tv/scripts')
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from statistical_validation_v2 import load_csv, kmeans, WINDOW, LOOKAHEAD
from multi_split_validation import extract_with_idx, K

WINNERS = [
    {'sym': 'BCS',   'cid': 2,  'label': 'BCS C2 LONG\nBarclays',      'cost_pct': 0.05},
    {'sym': 'HSBC',  'cid': 11, 'label': 'HSBC C11 LONG',              'cost_pct': 0.05},
    {'sym': 'DNBBY', 'cid': 2,  'label': 'DNBBY C2 LONG\nDNB Bank',    'cost_pct': 0.05},
    {'sym': 'BCS',   'cid': 4,  'label': 'BCS C4 LONG\nBarclays',      'cost_pct': 0.05},
]

POSITION_SIZE = 10000  # $10K per trade

def draw_with_trade_sim(ax, pattern_bars, after_bars, cost_pct):
    GREEN, RED = '#26a69a', '#ef5350'
    W = 0.7
    all_b = pattern_bars + after_bars
    for i, b in enumerate(all_b):
        o, h, l, c = b['open'], b['high'], b['low'], b['close']
        col = GREEN if c >= o else RED
        alpha = 1.0 if i < WINDOW else 0.45
        ax.plot([i, i], [l, h], color=col, linewidth=1.3, alpha=alpha)
        blo = min(o, c)
        bh = abs(c - o) or (h - l) * 0.001
        ax.add_patch(Rectangle((i - W/2, blo), W, bh, facecolor=col,
                               edgecolor='none', alpha=alpha))

    ax.axvline(x=WINDOW - 0.5, color='#f9e2af', linestyle='--', linewidth=1.2, alpha=0.8)
    entry = pattern_bars[-1]['close']
    exit_p = after_bars[-1]['close']

    # Draw entry & exit lines
    ax.axhline(y=entry, color='#89b4fa', linestyle=':', linewidth=1.2, alpha=0.8)
    ax.axhline(y=exit_p, color='#f9e2af' if exit_p > entry else '#fab387',
               linestyle=':', linewidth=1.2, alpha=0.8)

    ymax = max(b['high'] for b in all_b)
    ymin = min(b['low'] for b in all_b)
    ax.axvspan(WINDOW - 0.5, len(all_b) - 0.5, color='#585b70', alpha=0.12)

    # TRADE SIMULATION
    shares = POSITION_SIZE / entry
    move_pct = (exit_p - entry) / entry * 100
    gross_pnl = shares * (exit_p - entry)
    trading_cost_usd = POSITION_SIZE * (cost_pct / 100)
    net_pnl = gross_pnl - trading_cost_usd
    win = net_pnl > 0

    arrow_col = GREEN if win else RED
    ax.annotate('', xy=(len(all_b) - 1, exit_p), xytext=(WINDOW - 1, entry),
                arrowprops=dict(arrowstyle='->', color=arrow_col, lw=2.2, alpha=0.95))

    ax.autoscale_view()
    ax.set_xlim(-0.5, len(all_b) - 0.5)
    ax.set_facecolor('#1e1e2e')
    ax.tick_params(colors='#585b70', labelsize=7)
    for s in ax.spines.values():
        s.set_color('#585b70')
    ax.grid(True, alpha=0.1, color='#585b70')

    # Compact trade info box at top
    date_str = pattern_bars[0]['time'].strftime('%Y-%m-%d %H:%M')
    t_col = GREEN if win else RED
    info = (f'{date_str}\n'
            f'BUY ${entry:.2f} → SELL ${exit_p:.2f} ({move_pct:+.2f}%)\n'
            f'${POSITION_SIZE:,} pos → gross ${gross_pnl:+.2f} | '
            f'cost ${trading_cost_usd:.2f} → net ${net_pnl:+.2f}')
    ax.set_title(info, color=t_col, fontsize=8.5, fontweight='bold')

    # Small badge showing pattern/after zones
    ax.text(WINDOW/2 - 0.5, ymax, 'PATTERN', ha='center', va='top',
            color='#89b4fa', fontsize=7, fontweight='bold')
    ax.text(WINDOW + LOOKAHEAD/2 - 0.5, ymax, 'AFTER →', ha='center', va='top',
            color='#f9e2af', fontsize=7, fontweight='bold')

    return net_pnl, win

def main():
    fig, axes = plt.subplots(4, 6, figsize=(28, 18))
    fig.patch.set_facecolor('#1e1e2e')

    summary_by_row = []
    for row_idx, w in enumerate(WINNERS):
        sym, cid = w['sym'], w['cid']
        print(f'Processing {sym} C{cid}...')
        bars = load_csv(f'/Users/mariashchekanenko/claude-trading-tv/data/ohlcv/{sym}.csv')
        X, outs_pct, idxs, _ = extract_with_idx(bars)
        Xs = (X - X.mean(0)) / (X.std(0) + 1e-8)
        labels = kmeans(Xs, K)
        cluster_idxs = [idxs[i] for i in range(len(labels)) if labels[i] == cid]

        if len(cluster_idxs) >= 6:
            step = len(cluster_idxs) // 6
            examples = [cluster_idxs[i * step] for i in range(6)]
        else:
            examples = cluster_idxs

        pnls = []
        wins_count = 0
        for col, idx in enumerate(examples):
            ax = axes[row_idx][col]
            pattern = bars[idx:idx + WINDOW]
            after = bars[idx + WINDOW:idx + WINDOW + LOOKAHEAD]
            if len(after) < LOOKAHEAD:
                ax.set_visible(False); continue
            net_pnl, win = draw_with_trade_sim(ax, pattern, after, w['cost_pct'])
            pnls.append(net_pnl)
            if win:
                wins_count += 1

        # Row header with totals
        total_pnl = sum(pnls)
        wr = (wins_count / len(pnls)) * 100 if pnls else 0
        summary = f'{w["label"]}\n\n6 trades:\n{wins_count}W/{len(pnls)-wins_count}L\nNet: ${total_pnl:+.2f}\nWR: {wr:.0f}%'
        axes[row_idx][0].text(-0.32, 0.5, summary,
                              transform=axes[row_idx][0].transAxes,
                              ha='right', va='center',
                              color='#a6e3a1' if total_pnl > 0 else '#f38ba8',
                              fontsize=11, fontweight='bold')
        summary_by_row.append((w['label'].split('\n')[0], total_pnl, wins_count, len(pnls)))

    fig.suptitle(f'Multi-Split ROBUST Patterns — Trade Simulation (${POSITION_SIZE:,} position)\n'
                 f'Each cell: actual BUY@pattern_close → SELL@5bars_later, net $ after costs',
                 color='#cdd6f4', fontsize=15, fontweight='bold', y=0.998)
    plt.subplots_adjust(left=0.09, hspace=0.55, wspace=0.25, top=0.95)
    out = '/Users/mariashchekanenko/claude-trading-tv/charts/robust-v7-with-trades.png'
    fig.savefig(out, dpi=120, bbox_inches='tight', facecolor='#1e1e2e')
    plt.close(fig)

    print(f'\n═══ 6-trade sample summary ═══')
    for name, pnl, wins, total in summary_by_row:
        print(f'  {name:12} {wins}/{total} wins | net ${pnl:+8.2f}')
    overall = sum(p for _, p, _, _ in summary_by_row)
    print(f'  {"TOTAL":12} net ${overall:+8.2f} across all 24 sample trades')
    print(f'Saved {out}')

if __name__ == '__main__':
    main()
