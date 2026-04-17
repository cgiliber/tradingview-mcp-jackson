#!/usr/bin/env python3
"""
NVDA 1H Candlestick Chart — index-based, no gaps.
"""
import csv, os
from datetime import datetime, timedelta
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from matplotlib.collections import PatchCollection

CSV = os.path.join(os.path.dirname(__file__), '..', 'data', 'nvda-1h-ohlcv.csv')
OUT = os.path.join(os.path.dirname(__file__), '..', 'charts', 'nvda-1h-chart.png')

# Load
bars = []
with open(CSV) as f:
    for r in csv.DictReader(f):
        bars.append({
            't': datetime.utcfromtimestamp(int(r['timestamp'])),
            'o': float(r['open']), 'h': float(r['high']),
            'l': float(r['low']),  'c': float(r['close']),
            'v': int(float(r['volume'])),
        })
cutoff = bars[-1]['t'] - timedelta(days=30)
bars = [b for b in bars if b['t'] >= cutoff]
N = len(bars)

# Pure integer x: 0, 1, 2, ... N-1
x = list(range(N))
W = 0.8

fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(22, 10), height_ratios=[3, 1],
                                gridspec_kw={'hspace': 0.03})
BG = '#1e1e2e'
fig.patch.set_facecolor(BG)
ax1.set_facecolor(BG)
ax2.set_facecolor(BG)

GREEN, RED = '#26a69a', '#ef5350'

# Draw candles at integer positions
for i in range(N):
    o, h, l, c = bars[i]['o'], bars[i]['h'], bars[i]['l'], bars[i]['c']
    col = GREEN if c >= o else RED
    # wick
    ax1.plot([i, i], [l, h], color=col, linewidth=0.7, solid_capstyle='butt')
    # body
    blo = min(o, c)
    bh = abs(c - o) or 0.01
    r = Rectangle((i - W/2, blo), W, bh, facecolor=col, edgecolor='none',
                   antialiased=False)
    ax1.add_patch(r)
    # volume
    ax2.bar(i, bars[i]['v'], width=W, color=col, alpha=0.7, edgecolor='none')

# X labels: every 20th bar
label_idx = list(range(0, N, 20))
if (N - 1) not in label_idx:
    label_idx.append(N - 1)
ax2.set_xticks(label_idx)
ax2.set_xticklabels([bars[i]['t'].strftime('%b %d') for i in label_idx],
                    rotation=45, ha='right')
ax1.set_xticks([])  # no x labels on price chart

# Lock x range
ax1.set_xlim(-1, N)
ax2.set_xlim(-1, N)
ax1.autoscale_view(scalex=False, scaley=True)

# Style
for ax in (ax1, ax2):
    ax.tick_params(colors='#cdd6f4', labelsize=8)
    for s in ['top', 'right']:
        ax.spines[s].set_visible(False)
    for s in ['bottom', 'left']:
        ax.spines[s].set_color('#585b70')
    ax.grid(True, alpha=0.15, color='#585b70')

ax1.set_ylabel('Price ($)', color='#cdd6f4', fontsize=10)
ax2.set_ylabel('Volume', color='#cdd6f4', fontsize=10)
ax1.set_title('NVDA 1H — Last 30 Days', color='#cdd6f4', fontsize=14,
              fontweight='bold', pad=12)

# Last price
ax1.annotate(f"${bars[-1]['c']:.2f}", xy=(N-1, bars[-1]['c']),
             xytext=(10, 0), textcoords='offset points',
             color='#cdd6f4', fontsize=9, fontweight='bold',
             arrowprops=dict(arrowstyle='->', color='#cdd6f4', lw=0.8))

os.makedirs(os.path.dirname(OUT), exist_ok=True)
fig.savefig(OUT, dpi=150, bbox_inches='tight', facecolor=BG)
plt.close(fig)
print(f'Saved {OUT} — {N} bars')
