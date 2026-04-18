#!/usr/bin/env python3
"""
Statistical validation v4 — asset-class-specific market context features.

STOCK features added:
- SPY % change over 5 bars (market momentum)
- Sector ETF % change over 5 bars (XLK/XLE/XLF etc by mapping)
- VIX level
- VIX % change over 5 bars
- Stock return minus SPY return (relative strength)

CRYPTO features added:
- BTC % change over 5 bars
- ETH % change over 5 bars (for non-ETH)
- ETH/BTC ratio change (risk on/off)
- Weekend flag (1 if Sat/Sun)
- Hour + weekday (from v2)

Test universe kept SMALL to avoid Bonferroni inflation:
- Stocks: NVDA, AAPL, TSLA, MSFT, GOOGL, META, AMZN, NFLX, AMD, TSM
- Crypto: BTCUSD, ETHUSD, SOLUSD
"""
import sys, os, csv, json
sys.path.insert(0, '/Users/mariashchekanenko/claude-trading-tv/scripts')
import numpy as np
from datetime import datetime
from scipy.stats import binomtest
from statistical_validation_v2 import (
    load_csv, precompute_indicators, kmeans
)

OHLCV_DIR = '/Users/mariashchekanenko/claude-trading-tv/data/ohlcv'
OUT = '/Users/mariashchekanenko/claude-trading-tv/data/statistical-validation-v4.json'
WINDOW = 5
LOOKAHEAD = 5
MIN_N = 20
K = 15  # Smaller K with smaller asset pool

STOCK_UNIVERSE = ['NVDA', 'AAPL', 'TSLA', 'MSFT', 'GOOGL', 'META', 'AMZN', 'NFLX', 'AMD', 'TSM']
CRYPTO_UNIVERSE = ['BTCUSD', 'ETHUSD', 'SOLUSD']

# Stock → sector ETF
STOCK_SECTOR = {
    'NVDA': 'XLK', 'AAPL': 'XLK', 'TSLA': 'XLY', 'MSFT': 'XLK',
    'GOOGL': 'XLC', 'META': 'XLC', 'AMZN': 'XLY', 'NFLX': 'XLC',
    'AMD': 'XLK', 'TSM': 'XLK',
}

def load_context(name):
    """Load a context CSV and index by timestamp."""
    path = os.path.join(OHLCV_DIR, f'{name}.csv')
    if not os.path.exists(path):
        return None
    by_ts = {}
    with open(path) as f:
        for r in csv.DictReader(f):
            try:
                ts = int(r['timestamp'])
                by_ts[ts] = {
                    'open': float(r['open']), 'high': float(r['high']),
                    'low': float(r['low']), 'close': float(r['close']),
                }
            except (ValueError, KeyError):
                continue
    return by_ts

def stock_features(bars, sym, ctx_spy, ctx_vix, ctx_sector):
    """Extract window features for stocks."""
    ind = precompute_indicators(bars)
    feats, outs = [], []

    for i in range(len(bars) - WINDOW - LOOKAHEAD):
        window = bars[i:i + WINDOW]
        base_p = window[0]['open']
        if base_p == 0:
            continue

        vec = []
        # 20 OHLC %
        for b in window:
            vec.extend([(b['open']-base_p)/base_p*100, (b['high']-base_p)/base_p*100,
                        (b['low']-base_p)/base_p*100, (b['close']-base_p)/base_p*100])

        # 5 volume ratios
        for j in range(WINDOW):
            bi = i + j
            v = ind['vols'][bi]
            vm = ind['vol_ma20'][bi]
            vec.append(min(v/vm if vm else 1, 10))

        end = i + WINDOW - 1
        last_close = ind['closes'][end]

        rsi = ind['rsi'][end]
        if np.isnan(rsi): continue
        vec.append(rsi)
        e20 = ind['ema20'][end]
        if np.isnan(e20) or e20 == 0: continue
        vec.append((last_close - e20) / e20 * 100)
        e50 = ind['ema50'][end]
        if np.isnan(e50) or e50 == 0: continue
        vec.append((last_close - e50) / e50 * 100)
        atr = ind['atr'][end]
        if np.isnan(atr) or atr == 0: continue
        vec.append((ind['highs'][end] - ind['lows'][end]) / atr)
        t = ind['times'][end]
        vec.append(t.hour)
        vec.append(t.weekday())
        vec.append((e20 - e50) / e50 * 100)

        # Context features (computed from SPY / sector / VIX at window start and end)
        start_ts = int(window[0]['time'].timestamp())
        end_ts = int(bars[end]['time'].timestamp())
        spy_start = ctx_spy.get(start_ts)
        spy_end = ctx_spy.get(end_ts)
        if not spy_start or not spy_end:
            continue
        spy_ret = (spy_end['close'] - spy_start['close']) / spy_start['close'] * 100
        vec.append(spy_ret)

        # Sector
        sec_start = ctx_sector.get(start_ts) if ctx_sector else None
        sec_end = ctx_sector.get(end_ts) if ctx_sector else None
        if sec_start and sec_end:
            sec_ret = (sec_end['close'] - sec_start['close']) / sec_start['close'] * 100
            vec.append(sec_ret)
        else:
            vec.append(0)

        # VIX
        vix_start = ctx_vix.get(start_ts) if ctx_vix else None
        vix_end = ctx_vix.get(end_ts) if ctx_vix else None
        if vix_end:
            vec.append(vix_end['close'])
            if vix_start:
                vec.append((vix_end['close'] - vix_start['close']) / vix_start['close'] * 100)
            else:
                vec.append(0)
        else:
            vec.append(20); vec.append(0)  # neutral defaults

        # Relative strength: stock return - SPY return
        stock_ret = (window[-1]['close'] - window[0]['close']) / window[0]['close'] * 100
        vec.append(stock_ret - spy_ret)

        if any(np.isnan(vec)) or any(np.isinf(vec)):
            continue

        feats.append(vec)
        entry = bars[end]['close']
        exit_p = bars[end + LOOKAHEAD]['close']
        outs.append(1 if exit_p > entry else 0)

    return np.array(feats), np.array(outs)

def crypto_features(bars, sym, ctx_btc, ctx_eth):
    """Crypto features with BTC/ETH context."""
    ind = precompute_indicators(bars)
    feats, outs = [], []

    for i in range(len(bars) - WINDOW - LOOKAHEAD):
        window = bars[i:i + WINDOW]
        base_p = window[0]['open']
        if base_p == 0:
            continue

        vec = []
        # 20 OHLC %
        for b in window:
            vec.extend([(b['open']-base_p)/base_p*100, (b['high']-base_p)/base_p*100,
                        (b['low']-base_p)/base_p*100, (b['close']-base_p)/base_p*100])

        # 5 volume ratios
        for j in range(WINDOW):
            bi = i + j
            v = ind['vols'][bi]
            vm = ind['vol_ma20'][bi]
            vec.append(min(v/vm if vm else 1, 10))

        end = i + WINDOW - 1
        last_close = ind['closes'][end]

        rsi = ind['rsi'][end]
        if np.isnan(rsi): continue
        vec.append(rsi)
        e20 = ind['ema20'][end]
        if np.isnan(e20) or e20 == 0: continue
        vec.append((last_close - e20) / e20 * 100)
        e50 = ind['ema50'][end]
        if np.isnan(e50) or e50 == 0: continue
        vec.append((last_close - e50) / e50 * 100)
        atr = ind['atr'][end]
        if np.isnan(atr) or atr == 0: continue
        vec.append((ind['highs'][end] - ind['lows'][end]) / atr)
        t = ind['times'][end]
        vec.append(t.hour)
        vec.append(t.weekday())
        is_weekend = 1 if t.weekday() >= 5 else 0
        vec.append(is_weekend)
        vec.append((e20 - e50) / e50 * 100)

        # Context
        start_ts = int(window[0]['time'].timestamp())
        end_ts = int(bars[end]['time'].timestamp())

        btc_start = ctx_btc.get(start_ts)
        btc_end = ctx_btc.get(end_ts)
        if btc_start and btc_end and sym != 'BTCUSD':
            btc_ret = (btc_end['close'] - btc_start['close']) / btc_start['close'] * 100
        else:
            btc_ret = 0
        vec.append(btc_ret)

        eth_start = ctx_eth.get(start_ts) if ctx_eth else None
        eth_end = ctx_eth.get(end_ts) if ctx_eth else None
        if eth_start and eth_end:
            eth_ret = (eth_end['close'] - eth_start['close']) / eth_start['close'] * 100
        else:
            eth_ret = 0
        vec.append(eth_ret)

        # ETH/BTC ratio change
        if btc_end and eth_end and btc_start and eth_start:
            r_start = eth_start['close'] / btc_start['close']
            r_end = eth_end['close'] / btc_end['close']
            eth_btc_change = (r_end - r_start) / r_start * 100
        else:
            eth_btc_change = 0
        vec.append(eth_btc_change)

        # Relative strength: crypto return - BTC return
        crypto_ret = (window[-1]['close'] - window[0]['close']) / window[0]['close'] * 100
        vec.append(crypto_ret - btc_ret)

        if any(np.isnan(vec)) or any(np.isinf(vec)):
            continue

        feats.append(vec)
        entry = bars[end]['close']
        exit_p = bars[end + LOOKAHEAD]['close']
        outs.append(1 if exit_p > entry else 0)

    return np.array(feats), np.array(outs)

def analyze(name, universe, extract_fn, *ctx):
    patterns = []
    for sym in universe:
        path = os.path.join(OHLCV_DIR, f'{sym}.csv')
        bars = load_csv(path)
        if len(bars) < 200:
            continue
        X, outs = extract_fn(bars, sym, *ctx)
        if len(X) < 50:
            continue
        baseline = float(outs.mean())
        Xs = (X - X.mean(0)) / (X.std(0) + 1e-8)
        lab = kmeans(Xs, K)
        if lab is None:
            continue
        for cid in set(lab):
            m = lab == cid
            n = int(m.sum())
            if n < MIN_N:
                continue
            k_up = int(outs[m].sum())
            patterns.append({
                'asset': sym, 'class': name, 'method': f'kmeans_v4_{name}',
                'cluster': int(cid), 'n': n, 'k_up': k_up, 'baseline_p': baseline,
            })
        print(f'  {sym:8} {len(bars)}b | {len(X)} windows | clusters n>={MIN_N}: {sum(1 for p in patterns if p["asset"]==sym)}')
    return patterns

def main():
    # Load context data
    ctx_spy = load_context('SPY')
    ctx_vix = load_context('VIX')
    ctx_btc = load_context('BTCUSD')
    ctx_eth = load_context('ETHUSD')

    # Stocks
    print('\n═══ STOCKS ═══')
    stock_patterns = []
    for sym in STOCK_UNIVERSE:
        path = os.path.join(OHLCV_DIR, f'{sym}.csv')
        bars = load_csv(path)
        if len(bars) < 200:
            continue
        sector_etf = STOCK_SECTOR.get(sym)
        ctx_sec = load_context(sector_etf) if sector_etf else None
        X, outs = stock_features(bars, sym, ctx_spy, ctx_vix, ctx_sec)
        if len(X) < 50:
            print(f'  {sym:6} skipped ({len(X)} windows)')
            continue
        baseline = float(outs.mean())
        Xs = (X - X.mean(0)) / (X.std(0) + 1e-8)
        lab = kmeans(Xs, K)
        if lab is None:
            continue
        added = 0
        for cid in set(lab):
            m = lab == cid
            n = int(m.sum())
            if n < MIN_N: continue
            k_up = int(outs[m].sum())
            stock_patterns.append({
                'asset': sym, 'class': 'stocks', 'method': 'kmeans_v4_stocks',
                'cluster': int(cid), 'n': n, 'k_up': k_up, 'baseline_p': baseline,
            })
            added += 1
        print(f'  {sym:6} {len(bars)}b | {len(X)} windows | {added} clusters')

    # Crypto
    print('\n═══ CRYPTO ═══')
    crypto_patterns = []
    for sym in CRYPTO_UNIVERSE:
        path = os.path.join(OHLCV_DIR, f'{sym}.csv')
        bars = load_csv(path)
        if len(bars) < 200:
            continue
        X, outs = crypto_features(bars, sym, ctx_btc, ctx_eth)
        if len(X) < 50:
            continue
        baseline = float(outs.mean())
        Xs = (X - X.mean(0)) / (X.std(0) + 1e-8)
        lab = kmeans(Xs, K)
        if lab is None: continue
        added = 0
        for cid in set(lab):
            m = lab == cid
            n = int(m.sum())
            if n < MIN_N: continue
            k_up = int(outs[m].sum())
            crypto_patterns.append({
                'asset': sym, 'class': 'crypto', 'method': 'kmeans_v4_crypto',
                'cluster': int(cid), 'n': n, 'k_up': k_up, 'baseline_p': baseline,
            })
            added += 1
        print(f'  {sym:8} {len(bars)}b | {len(X)} windows | {added} clusters')

    all_patterns = stock_patterns + crypto_patterns
    total = len(all_patterns)
    threshold = 0.05 / total if total else 1
    print(f'\n═══ STATS ═══')
    print(f'Total patterns: {total} (stocks: {len(stock_patterns)}, crypto: {len(crypto_patterns)})')
    print(f'Bonferroni threshold: {threshold:.2e}')

    raw_sig = 0
    for p in all_patterns:
        result = binomtest(p['k_up'], p['n'], p['baseline_p'], alternative='two-sided')
        p['p_value'] = float(result.pvalue)
        p['win_rate'] = p['k_up'] / p['n'] * 100
        p['baseline_pct'] = p['baseline_p'] * 100
        p['effect_size'] = (p['k_up'] / p['n'] - p['baseline_p']) * 100
        p['direction'] = 'LONG' if p['effect_size'] > 0 else 'SHORT'
        p['survives_bonferroni'] = result.pvalue < threshold
        if result.pvalue < 0.05:
            raw_sig += 1

    survivors = [p for p in all_patterns if p['survives_bonferroni']]
    survivors.sort(key=lambda x: x['p_value'])

    print(f'Raw p<0.05 hits: {raw_sig}/{total}')
    print(f'Bonferroni survivors: {len(survivors)}')

    if survivors:
        print(f'\n{"Asset":>8} {"Class":>8} {"Clu":>4} {"N":>5} {"WR%":>5} '
              f'{"Base%":>6} {"Edge":>6} {"Dir":>5} {"p-value":>12}')
        print('-' * 90)
        for p in survivors:
            print(f'{p["asset"]:>8} {p["class"]:>8} {p["cluster"]:>4} {p["n"]:>5} '
                  f'{p["win_rate"]:>5.1f} {p["baseline_pct"]:>6.1f} '
                  f'{p["effect_size"]:>+6.1f} {p["direction"]:>5} '
                  f'{p["p_value"]:>12.2e}')
    else:
        print('\n❌ No stock/crypto patterns survive Bonferroni even with market context features.')
        # Show top 5 by p-value for diagnostic
        all_patterns.sort(key=lambda x: x['p_value'])
        print(f'\nTop 5 closest to significance:')
        for p in all_patterns[:5]:
            print(f'  {p["asset"]:>8} {p["class"]:>8} C{p["cluster"]} n={p["n"]} '
                  f'WR={p["win_rate"]:.1f}% edge={p["effect_size"]:+.1f}% p={p["p_value"]:.2e}')

    with open(OUT, 'w') as f:
        json.dump({
            'analyzed_at': datetime.now().isoformat(),
            'feature_set': 'v2 + market context (VIX, SPY, sector, BTC, ETH, rel strength)',
            'stock_universe': STOCK_UNIVERSE,
            'crypto_universe': CRYPTO_UNIVERSE,
            'total_patterns': total,
            'bonferroni_threshold': threshold,
            'survivors_count': len(survivors),
            'survivors': survivors,
            'all_patterns': all_patterns,
        }, f, indent=2, default=str)
    print(f'\nSaved to {OUT}')

if __name__ == '__main__':
    main()
