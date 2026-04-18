#!/usr/bin/env python3
"""
Extract rule-based trigger conditions from each of the 7 validated clusters.
Generates per-strategy JSON trigger rules + human-readable STRATEGY.md.
"""
import sys, os, json
sys.path.insert(0, '/Users/mariashchekanenko/claude-trading-tv/scripts')
import numpy as np
from statistical_validation_v2 import load_csv, kmeans
from multi_split_validation import extract_with_idx, K as K_V7, extract_triggers

# For crypto v5 features
from statistical_validation_v5_crypto import extract_v5, K as K_V5

OUT_DIR = '/Users/mariashchekanenko/claude-trading-tv/strategies'

STRATEGIES = [
    # 6 new strategies (EURGBP already saved)
    {'id': 'crypto-oversold-xrpusd', 'asset': 'XRPUSD', 'cid': 1, 'direction': 'LONG',
     'feature_set': 'v5', 'K': K_V5,
     'title': 'XRPUSD Deep Oversold Bounce',
     'description': 'Buy XRPUSD when price is deeply oversold (RSI<40, >3% below EMA20/50). Mean-reversion bounce expected in 5 bars.',
     'validation': 'Bonferroni p=8.9e-7, out-of-sample holds (59% WR, +2.5% return)'},

    {'id': 'crypto-funding-adausd', 'asset': 'ADAUSD', 'cid': 9, 'direction': 'LONG',
     'feature_set': 'v5', 'K': K_V5,
     'title': 'ADAUSD Funding Squeeze',
     'description': 'Buy ADAUSD when shorts are crowded (funding < -0.01%) AND funding is decreasing further. Short squeeze setup.',
     'validation': 'Bonferroni p=5.5e-5, out-of-sample +7.7% return, 55.6% WR'},

    {'id': 'eu-stocks-barclays-c2', 'asset': 'BCS', 'cid': 2, 'direction': 'LONG',
     'feature_set': 'v2', 'K': K_V7,
     'title': 'Barclays (BCS) C2 LONG',
     'description': 'Long Barclays ADR on specific indicator pattern. UK bank, NYSE-traded ADR.',
     'validation': '5/5 multi-split tests passed, 249 trades, 60% WR, +$5920 on $10K/trade over 2y'},

    {'id': 'eu-stocks-hsbc-c11', 'asset': 'HSBC', 'cid': 11, 'direction': 'LONG',
     'feature_set': 'v2', 'K': K_V7,
     'title': 'HSBC Holdings C11 LONG',
     'description': 'Long HSBC ADR on specific indicator pattern. UK bank, NYSE-traded ADR.',
     'validation': '5/5 multi-split tests passed, 149 trades, 66% WR, +$3595 on $10K/trade over 2y'},

    {'id': 'eu-stocks-dnb-c2', 'asset': 'DNBBY', 'cid': 2, 'direction': 'LONG',
     'feature_set': 'v2', 'K': K_V7,
     'title': 'DNB Bank (DNBBY) C2 LONG',
     'description': 'Long DNBBY ADR. Norwegian bank, OTC-traded ADR — may have liquidity issues.',
     'validation': '5/5 multi-split tests passed, but lumpy equity curve. 94 trades, 61% WR.'},

    {'id': 'eu-stocks-barclays-c4', 'asset': 'BCS', 'cid': 4, 'direction': 'LONG',
     'feature_set': 'v2', 'K': K_V7,
     'title': 'Barclays (BCS) C4 LONG',
     'description': 'Alternative Barclays pattern. Weaker edge, may be lucky recent spike.',
     'validation': '5/5 multi-split tests passed, 163 trades, 56% WR. MARGINAL — trust cautiously.'},
]

def build_rules(triggers, direction, include_funding=False):
    """Convert P10/P90 trigger ranges into simple min/max rules."""
    rules = {
        'rsi_min': round(triggers['rsi']['p10'], 1),
        'rsi_max': round(triggers['rsi']['p90'], 1),
        'ema20_dist_min_pct': round(triggers['ema20_dist']['p10'], 2),
        'ema20_dist_max_pct': round(triggers['ema20_dist']['p90'], 2),
        'ema50_dist_min_pct': round(triggers['ema50_dist']['p10'], 2),
        'ema50_dist_max_pct': round(triggers['ema50_dist']['p90'], 2),
        'range_atr_min': round(triggers['range_atr']['p10'], 2),
        'range_atr_max': round(triggers['range_atr']['p90'], 2),
    }
    # Hour/weekday: keep as range but convert to int
    if 'hour' in triggers:
        rules['hour_min'] = int(triggers['hour']['p10'])
        rules['hour_max'] = int(triggers['hour']['p90'])
    if 'weekday' in triggers:
        rules['weekday_min'] = int(triggers['weekday']['p10'])
        rules['weekday_max'] = int(triggers['weekday']['p90'])
    return rules

def extract_for_v2(asset, cid):
    bars = load_csv(f'/Users/mariashchekanenko/claude-trading-tv/data/ohlcv/{asset}.csv')
    X, outs, idxs, _ = extract_with_idx(bars)
    Xs = (X - X.mean(0)) / (X.std(0) + 1e-8)
    labels = kmeans(Xs, K_V7)
    mask = labels == cid
    n = int(mask.sum())
    wr = float((outs[mask] > 0).mean() * 100)
    triggers = extract_triggers(X[mask])
    return triggers, n, wr, X, outs, mask

def extract_for_v5(asset, cid):
    bars = load_csv(f'/Users/mariashchekanenko/claude-trading-tv/data/ohlcv/{asset}.csv')
    X, outs = extract_v5(bars, asset)
    Xs = (X - X.mean(0)) / (X.std(0) + 1e-8)
    labels = kmeans(Xs, K_V5)
    mask = labels == cid
    n = int(mask.sum())
    wr = float((outs[mask] > 0).mean() * 100)
    # Map same indicator indices (25-31) as v2; funding at 33-36
    # Use extract_triggers (which works on v2 indices 25-31)
    triggers = extract_triggers(X[mask])
    # Add funding features
    funding_stats = {
        'funding_now_p10': round(float(np.percentile(X[mask][:, 33], 10)), 4),
        'funding_now_p50': round(float(np.percentile(X[mask][:, 33], 50)), 4),
        'funding_now_p90': round(float(np.percentile(X[mask][:, 33], 90)), 4),
        'funding_change_1d_p10': round(float(np.percentile(X[mask][:, 36], 10)), 4),
        'funding_change_1d_p50': round(float(np.percentile(X[mask][:, 36], 50)), 4),
        'funding_change_1d_p90': round(float(np.percentile(X[mask][:, 36], 90)), 4),
    }
    return triggers, funding_stats, n, wr

for s in STRATEGIES:
    print(f'\n━━━ {s["id"]} ━━━')
    strat_dir = os.path.join(OUT_DIR, s['id'])
    os.makedirs(strat_dir, exist_ok=True)

    if s['feature_set'] == 'v2':
        triggers, n, wr, _, _, _ = extract_for_v2(s['asset'], s['cid'])
        rules = build_rules(triggers, s['direction'])
        funding = None
    else:
        triggers, funding, n, wr = extract_for_v5(s['asset'], s['cid'])
        rules = build_rules(triggers, s['direction'])
        rules.update(funding)

    print(f'  N={n}, WR={wr:.1f}%')
    print(f'  Rules: RSI[{rules["rsi_min"]}-{rules["rsi_max"]}], '
          f'EMA20_dist[{rules["ema20_dist_min_pct"]}%-{rules["ema20_dist_max_pct"]}%]')

    # Save config.json
    config = {
        'id': s['id'],
        'title': s['title'],
        'description': s['description'],
        'validation': s['validation'],
        'asset': s['asset'],
        'direction': s['direction'],
        'timeframe': '1h',
        'feature_set': s['feature_set'],
        'cluster_id': s['cid'],
        'cluster_size': n,
        'in_sample_win_rate': round(wr, 1),
        'entry_trigger': rules,
        'exit_rule': {
            'type': 'time_based',
            'hold_bars': 5,
        },
        'risk': {
            'max_loss_per_trade_usd': 10,
            'default_position_size_usd': 10000,
        },
    }
    with open(os.path.join(strat_dir, 'config.json'), 'w') as f:
        json.dump(config, f, indent=2)
    print(f'  Saved {strat_dir}/config.json')
