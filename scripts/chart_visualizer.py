#!/usr/bin/env python3
"""
NVDA 1H Candlestick Chart Visualizer
Reads CSV OHLCV data and generates a candlestick chart with volume bars.
Uses pure matplotlib (no mplfinance dependency).
"""

import csv
import os
from datetime import datetime, timedelta

import matplotlib
matplotlib.use('Agg')  # Non-interactive backend for PNG output
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.patches import Rectangle

# Paths
CSV_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'nvda-1h-ohlcv.csv')
OUTPUT_PATH = os.path.join(os.path.dirname(__file__), '..', 'charts', 'nvda-1h-chart.png')

def read_csv(path):
    bars = []
    with open(path, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            bars.append({
                'time': datetime.utcfromtimestamp(int(row['timestamp'])),
                'open': float(row['open']),
                'high': float(row['high']),
                'low': float(row['low']),
                'close': float(row['close']),
                'volume': int(float(row['volume'])),
            })
    return bars

def filter_last_30_days(bars):
    if not bars:
        return bars
    last_date = bars[-1]['time']
    cutoff = last_date - timedelta(days=30)
    return [b for b in bars if b['time'] >= cutoff]

def plot_candlestick(bars, output_path):
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(18, 10), height_ratios=[3, 1],
                                    sharex=True, gridspec_kw={'hspace': 0.05})

    fig.patch.set_facecolor('#1e1e2e')
    ax1.set_facecolor('#1e1e2e')
    ax2.set_facecolor('#1e1e2e')

    dates = [b['time'] for b in bars]
    # Width of one bar in date units (1 hour = 1/24 day, use 80% width)
    width = 0.8 / 24

    for i, bar in enumerate(bars):
        dt = bar['time']
        o, h, l, c = bar['open'], bar['high'], bar['low'], bar['close']
        color = '#26a69a' if c >= o else '#ef5350'  # green / red

        # Wick (high-low line)
        ax1.plot([dt, dt], [l, h], color=color, linewidth=0.6)

        # Body
        body_bottom = min(o, c)
        body_height = abs(c - o) or 0.01
        rect = Rectangle((mdates.date2num(dt) - width / 2, body_bottom),
                          width, body_height, facecolor=color, edgecolor=color, linewidth=0.5)
        ax1.add_patch(rect)

        # Volume bar
        vol_color = '#26a69a' if c >= o else '#ef5350'
        ax2.bar(dt, bar['volume'], width=width, color=vol_color, alpha=0.7)

    # Styling
    for ax in (ax1, ax2):
        ax.tick_params(colors='#cdd6f4', labelsize=8)
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['bottom'].set_color('#585b70')
        ax.spines['left'].set_color('#585b70')
        ax.grid(True, alpha=0.15, color='#585b70')

    ax1.set_ylabel('Price ($)', color='#cdd6f4', fontsize=10)
    ax2.set_ylabel('Volume', color='#cdd6f4', fontsize=10)

    ax2.xaxis.set_major_formatter(mdates.DateFormatter('%b %d'))
    ax2.xaxis.set_major_locator(mdates.WeekdayLocator(interval=1))
    plt.setp(ax2.xaxis.get_majorticklabels(), rotation=45, ha='right')

    ax1.set_title('NVDA 1H \u2014 Last 30 Days', color='#cdd6f4', fontsize=14, fontweight='bold', pad=12)

    # Price annotation for last bar
    last = bars[-1]
    ax1.annotate(f"${last['close']:.2f}", xy=(last['time'], last['close']),
                 xytext=(10, 0), textcoords='offset points',
                 color='#cdd6f4', fontsize=9, fontweight='bold',
                 arrowprops=dict(arrowstyle='->', color='#cdd6f4', lw=0.8))

    fig.tight_layout()
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    fig.savefig(output_path, dpi=150, bbox_inches='tight', facecolor=fig.get_facecolor())
    plt.close(fig)
    print(f'Chart saved to {output_path}')

def main():
    bars = read_csv(CSV_PATH)
    print(f'Total bars loaded: {len(bars)}')
    bars_30d = filter_last_30_days(bars)
    print(f'Bars in last 30 days: {len(bars_30d)}')
    if bars_30d:
        print(f'Date range: {bars_30d[0]["time"]} to {bars_30d[-1]["time"]}')
    plot_candlestick(bars_30d, OUTPUT_PATH)

if __name__ == '__main__':
    main()
