"""Characterize a saved, causal walk-forward run; no model fitting or decisions.

Volatility-ranked states are local to a refit; pooled statistics describe ranks,
not a single stable state. Forward outcomes are exploratory and overlap.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'research/legacy/src'))
from regime_backtester.features import build_features


def weighted_mean(x, w):
    a, b = np.asarray(x, float), np.asarray(w, float)
    ok = np.isfinite(a) & np.isfinite(b) & (b >= 0)
    return float(np.dot(a[ok], b[ok]) / b[ok].sum()) if b[ok].sum() else None


def weighted_quantile(x, w, q):
    x, w = np.asarray(x, float), np.asarray(w, float)
    mask = np.isfinite(x) & np.isfinite(w) & (w >= 0)
    x, w = x[mask], w[mask]
    if not len(x) or w.sum() <= 0:
        return None
    order = np.argsort(x)
    x, w = x[order], w[order]
    return float(x[min(np.searchsorted(np.cumsum(w), q * w.sum()), len(x) - 1)])


def describe(prices, signals):
    prices = prices.copy().set_index('Date').sort_index()
    prices.index = pd.to_datetime(prices.index)
    features = build_features(prices)
    # These diagnostic features are not necessarily HMM inputs.
    r = features.daily_return
    features['negative_day'] = (r < 0).astype(float).where(r.notna())
    features['positive_day'] = (r > 0).astype(float).where(r.notna())
    features['downside_vol20'] = np.sqrt(r.clip(upper=0).pow(2).rolling(20).mean() * 252)
    features['vol_of_vol20'] = features.volatility_20.rolling(20).std()
    features['vol_percentile'] = features.volatility_20.rank(pct=True)  # descriptive full-sample ranking
    features['drawdown_duration'] = (prices.Close < prices.Close.rolling(252).max()).astype(int)
    # Number of sessions since the most recent trailing-252-day high.
    groups = (features['drawdown_duration'] == 0).cumsum()
    features['drawdown_duration'] = features['drawdown_duration'].groupby(groups).cumsum()
    for h in (1, 5, 20, 60):
        features[f'forward_{h}'] = prices.Close.shift(-h) / prices.Close - 1
    s = signals.copy()
    s['decision_date'] = pd.to_datetime(s.decision_date)
    if s.decision_date.duplicated().any() or not s.decision_date.is_monotonic_increasing:
        raise ValueError('Signals must have unique, ordered decision dates')
    s = s.set_index('decision_date').join(features, how='left')
    probcols = [c for c in s if c.startswith('p_state_')]
    p = s[probcols].to_numpy(float)
    if not np.isfinite(p).all() or not np.allclose(p.sum(axis=1), 1):
        raise ValueError('Invalid filtered posterior probabilities')
    state = p.argmax(axis=1)
    entropy = -np.sum(np.where(p > 0, p * np.log(np.maximum(p, 1e-300)), 0), axis=1) / np.log(len(probcols))
    # Never link episodes or transition counts over annual refits.
    fold = s.index.year.to_numpy()
    durations = {i: [] for i in range(len(probcols))}
    counts = np.zeros((len(probcols), len(probcols)), dtype=int)
    begin = 0
    for j in range(1, len(s) + 1):
        if j == len(s) or fold[j] != fold[j-1] or state[j] != state[j-1]:
            durations[state[j-1]].append(j-begin)
            begin = j
        if j < len(s) and fold[j] == fold[j-1]:
            counts[state[j-1], state[j]] += 1
    summaries = []
    for i, col in enumerate(probcols):
        w = p[:, i]
        hard = state == i
        ret = weighted_mean(s.daily_return, w)
        vol = weighted_mean(s.volatility_20, w)
        n = int(hard.sum())
        direction = 'positive' if ret > 0.0002 else 'negative' if ret < -0.0002 else 'mixed'
        title = f'{direction.capitalize()} average return · volatility rank {i}'
        desc = (f'In this exploratory out-of-sample sample, posterior-weighted daily return was {ret:.3%} '
                f'and 20-session annualized volatility was {vol:.1%}. This is a local training-volatility rank, '
                'not a stable identity across refits; contemporaneous returns are not forecasts.')
        d = {'rank': i, 'title': title, 'description': desc, 'hard_observations': n,
             'hard_fraction': float(hard.mean()), 'posterior_weight': float(w.sum()),
             'rare_flag': bool(n < 100 or hard.mean() < .05),
             'mean_return': ret, 'median_return': weighted_quantile(s.daily_return, w, .5),
             'return_q05': weighted_quantile(s.daily_return, w, .05),
             'positive_day_frequency': weighted_mean(s.positive_day, w),
             'negative_day_frequency': weighted_mean(s.negative_day, w),
             'momentum_20': weighted_mean(s.return_20, w), 'momentum_60': weighted_mean(s.return_60, w),
             'ma_distance_200': weighted_mean(s.ma_distance_200, w),
             'sign_persistence_5': weighted_mean(s.sign_persistence, w),
             'volatility_20': vol, 'downside_volatility_20': weighted_mean(s.downside_vol20, w),
             'volatility_percentile_full_sample': weighted_mean(s.vol_percentile, w),
             'volatility_of_volatility': weighted_mean(s.vol_of_vol20, w),
             'drawdown_252': weighted_mean(s.drawdown_252, w),
             'drawdown_duration': weighted_mean(s.drawdown_duration, w),
             'daily_range': weighted_mean(s.high_low_range, w), 'overnight_gap': weighted_mean(s.overnight_gap, w),
             'mean_episode_length': float(np.mean(durations[i])) if durations[i] else None,
             'median_episode_length': float(np.median(durations[i])) if durations[i] else None,
             'episode_count': len(durations[i]),
             'mean_confidence_when_assigned': float(p[hard, i].mean()) if n else None,
             'mean_entropy_when_assigned': float(entropy[hard].mean()) if n else None,
             'ambiguous_fraction_when_assigned': float((p[hard].max(axis=1) < .6).mean()) if n else None,
             'forward': {str(h): {'mean_return': weighted_mean(s[f'forward_{h}'], w),
                                    'positive_probability': weighted_mean((s[f'forward_{h}'] > 0).astype(float).where(s[f'forward_{h}'].notna()), w),
                                    'observations': int(s[f'forward_{h}'].notna().sum())} for h in (1,5,20,60)}}
        summaries.append(d)
    trans = [(row / row.sum()).tolist() if row.sum() else [None] * len(row) for row in counts]
    timeline = [{'date': t.strftime('%Y-%m-%d'), 'rank': int(st), 'confidence': float(max(pr)), 'entropy': float(e)}
                for t, st, pr, e in zip(s.index, state, p, entropy)]
    return {'states': summaries, 'transition_counts': counts.tolist(), 'transition_probabilities': trans,
            'timeline': timeline, 'folds': int(len(np.unique(fold))), 'signals': len(s)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--run', type=Path, required=True)
    ap.add_argument('--output', type=Path, required=True)
    args = ap.parse_args()
    if args.output.exists():
        raise SystemExit('Refusing to overwrite an existing analysis')
    input_file, signal_file = args.run / 'inputs/prices.csv', args.run / 'signals.csv'
    result = describe(pd.read_csv(input_file), pd.read_csv(signal_file))
    result['provenance'] = {'run': args.run.name, 'data_sha256': hashlib.sha256(input_file.read_bytes()).hexdigest(),
                            'signals_sha256': hashlib.sha256(signal_file.read_bytes()).hexdigest(),
                            'analysis_source_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                            'inputs': ['daily_return', 'volatility_20', 'drawdown_252'],
                            'diagnostics': 'All other measures are post-fit; full-sample percentile and forward outcomes are descriptive only.',
                            'inference': 'Filtered OOS probabilities, yearly refits; rank alignment is a volatility heuristic, not state identity.',
                            'forward_warning': 'Overlapping forward returns; descriptive only, no confidence intervals or causal claims.'}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(result, indent=2, allow_nan=False)
    with args.output.open('x') as f:
        f.write(text + '\n')
    print(args.output)

if __name__ == '__main__':
    main()
