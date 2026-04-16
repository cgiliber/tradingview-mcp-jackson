#!/usr/bin/env python3
"""
v8.5 TradingLab Strategy Backtester
Simulates: valid structure + supply/demand zones + R:R > 2.5:1
Runs across multiple assets and timeframes.
"""

import json
import sys

def find_valid_structure(bars):
    """
    Track valid highs and lows.
    A low is ONLY valid if the move from it broke the previous high.
    A high is ONLY valid if the move from it broke the previous low.
    Returns list of (index, trend, valid_low, valid_high) at each bar.
    """
    if len(bars) < 3:
        return []

    structure = []
    # Initialize
    swing_highs = []
    swing_lows = []
    valid_low = bars[0]['low']
    valid_high = bars[0]['high']
    trend = 'UNKNOWN'
    last_valid_low = valid_low
    last_valid_high = valid_high

    # Simple swing detection
    for i in range(1, len(bars)):
        h = bars[i]['high']
        l = bars[i]['low']

        # Check if we broke previous valid high → validates the low
        if h > last_valid_high:
            # Find the lowest low since last valid high
            min_low = min(b['low'] for b in bars[max(0, i-10):i+1])
            last_valid_low = min_low
            last_valid_high = h
            trend = 'UP'

        # Check if we broke previous valid low → validates the high
        if l < last_valid_low:
            max_high = max(b['high'] for b in bars[max(0, i-10):i+1])
            last_valid_high = max_high
            last_valid_low = l
            trend = 'DOWN'

        structure.append({
            'index': i,
            'trend': trend,
            'valid_low': last_valid_low,
            'valid_high': last_valid_high,
            'price': bars[i]['close'],
            'high': h,
            'low': l
        })

    return structure

def find_zones(bars, structure):
    """
    Find supply/demand zones.
    Demand: consolidation (small range candles) before sharp UP move in uptrend.
    Supply: consolidation before sharp DOWN move in downtrend.
    """
    zones = []
    if len(bars) < 5:
        return zones

    for i in range(3, len(bars)):
        # Calculate move size
        move = bars[i]['close'] - bars[i]['open']
        avg_range = sum(abs(b['close'] - b['open']) for b in bars[max(0,i-5):i]) / min(5, i)

        if avg_range == 0:
            continue

        # Sharp move = 2x average
        if abs(move) > avg_range * 2:
            # Check previous candle for consolidation
            prev = bars[i-1]
            prev_range = abs(prev['high'] - prev['low'])

            if move > 0:  # Sharp UP = demand zone
                zones.append({
                    'type': 'DEMAND',
                    'index': i-1,
                    'low': prev['low'],
                    'high': prev['high'],
                    'impulse_bar': i
                })
            else:  # Sharp DOWN = supply zone
                zones.append({
                    'type': 'SUPPLY',
                    'index': i-1,
                    'low': prev['low'],
                    'high': prev['high'],
                    'impulse_bar': i
                })

    return zones

def simulate_v85(bars, risk=10):
    """
    Full v8.5 simulation on a set of bars.
    Returns list of trades.
    """
    if len(bars) < 20:
        return []

    structure = find_valid_structure(bars)
    zones = find_zones(bars, structure)
    trades = []

    for zone in zones:
        zi = zone['impulse_bar']
        if zi >= len(structure):
            continue

        trend = structure[min(zi, len(structure)-1)]['trend']

        # Only trade demand in uptrend, supply in downtrend
        if zone['type'] == 'DEMAND' and trend != 'UP':
            continue
        if zone['type'] == 'SUPPLY' and trend != 'DOWN':
            continue

        # Look for price to re-enter zone after the impulse
        for j in range(zi + 1, min(zi + 30, len(bars))):
            price = bars[j]['close']

            if zone['type'] == 'DEMAND' and bars[j]['low'] <= zone['high']:
                # Price re-entered demand zone — LONG entry
                entry = zone['high']
                stop = zone['low'] - 0.01
                stop_dist = entry - stop
                if stop_dist <= 0:
                    continue

                # TP at recent high (highest since impulse)
                recent_high = max(b['high'] for b in bars[zi:j+1])
                tp = recent_high
                reward = tp - entry

                if stop_dist > 0 and reward / stop_dist >= 2.5:
                    # Check outcome
                    units = int(risk / stop_dist)
                    if units <= 0:
                        continue

                    result = 'OPEN'
                    exit_price = entry
                    for k in range(j+1, min(j+50, len(bars))):
                        if bars[k]['low'] <= stop:
                            result = 'LOSS'
                            exit_price = stop
                            break
                        if bars[k]['high'] >= tp:
                            result = 'WIN'
                            exit_price = tp
                            break

                    pnl = (exit_price - entry) * units
                    trades.append({
                        'type': 'LONG',
                        'entry': round(entry, 4),
                        'stop': round(stop, 4),
                        'tp': round(tp, 4),
                        'rr': round(reward/stop_dist, 2),
                        'result': result,
                        'pnl': round(pnl, 2),
                        'bar_index': j
                    })
                break

            elif zone['type'] == 'SUPPLY' and bars[j]['high'] >= zone['low']:
                # Price re-entered supply zone — SHORT entry
                entry = zone['low']
                stop = zone['high'] + 0.01
                stop_dist = stop - entry
                if stop_dist <= 0:
                    continue

                recent_low = min(b['low'] for b in bars[zi:j+1])
                tp = recent_low
                reward = entry - tp

                if stop_dist > 0 and reward / stop_dist >= 2.5:
                    units = int(risk / stop_dist)
                    if units <= 0:
                        continue

                    result = 'OPEN'
                    exit_price = entry
                    for k in range(j+1, min(j+50, len(bars))):
                        if bars[k]['high'] >= stop:
                            result = 'LOSS'
                            exit_price = stop
                            break
                        if bars[k]['low'] <= tp:
                            result = 'WIN'
                            exit_price = tp
                            break

                    pnl = (entry - exit_price) * units
                    trades.append({
                        'type': 'SHORT',
                        'entry': round(entry, 4),
                        'stop': round(stop, 4),
                        'tp': round(tp, 4),
                        'rr': round(reward/stop_dist, 2),
                        'result': result,
                        'pnl': round(pnl, 2),
                        'bar_index': j
                    })
                break

    return trades

# Read bars from stdin (JSON format)
if __name__ == '__main__':
    data = json.load(sys.stdin)
    bars = data.get('bars', [])
    symbol = data.get('symbol', 'UNKNOWN')
    timeframe = data.get('timeframe', '?')

    trades = simulate_v85(bars)

    wins = [t for t in trades if t['result'] == 'WIN']
    losses = [t for t in trades if t['result'] == 'LOSS']
    opens = [t for t in trades if t['result'] == 'OPEN']

    total_pnl = sum(t['pnl'] for t in trades)
    win_rate = len(wins) / len(trades) * 100 if trades else 0

    print(json.dumps({
        'symbol': symbol,
        'timeframe': timeframe,
        'total_trades': len(trades),
        'wins': len(wins),
        'losses': len(losses),
        'open': len(opens),
        'win_rate': round(win_rate, 1),
        'total_pnl': round(total_pnl, 2),
        'avg_pnl': round(total_pnl / len(trades), 2) if trades else 0,
        'trades': trades
    }))
