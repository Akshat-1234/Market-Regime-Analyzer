"""Exploratory joint feature/state/covariance walk-forward grid.

For likelihood, compare ONLY models with identical feature vectors and dates.
Selection by training likelihood occurs within each specification and fold;
seed and fold failures are recorded, not silently substituted.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import platform
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from hmmlearn.hmm import GaussianHMM
from scipy.optimize import linear_sum_assignment
from scipy.special import logsumexp
from sklearn.preprocessing import StandardScaler
from threadpoolctl import threadpool_limits

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'research/legacy/src'))
from regime_backtester.features import build_features
from regime_backtester.hmm import forward_filter

SPECS = {'rv': ['daily_return', 'volatility_20'],
         'rvd': ['daily_return', 'volatility_20', 'drawdown_252']}
SEEDS = [2, 42]


def score_conditional(model, train, test, scales):
    _, alpha = forward_filter(model, train)
    emit = model._compute_log_likelihood(test)
    with np.errstate(divide='ignore'):
        trans = np.log(model.transmat_)
    probs, logp = [], []
    for row in emit:
        a = logsumexp(alpha[:, None] + trans, axis=0) + row
        z = logsumexp(a)
        if not np.isfinite(z):
            raise ValueError('non-finite predictive density')
        alpha = a-z
        probs.append(np.exp(alpha))
        # Change of variables to the original input units.
        logp.append(z - np.log(scales).sum())
    return np.asarray(probs), float(np.mean(logp))


def run(data_path, output):
    if output.exists():
        raise ValueError('Output already exists; choose a new experiment identifier')
    raw = pd.read_csv(data_path, parse_dates=['Date']).set_index('Date')
    if not raw.index.is_unique or not raw.index.is_monotonic_increasing:
        raise ValueError('Input dates must be unique and sorted')
    features = build_features(raw).dropna(subset=SPECS['rvd'])
    fits, scores = [], []
    for year in range(2012, 2027):
        train = features.loc[features.index.year < year]
        test = features.loc[features.index.year == year]
        if len(train) < 500 or len(test) == 0:
            continue
        for name, cols in SPECS.items():
            scaler = StandardScaler().fit(train[cols])
            x, y = scaler.transform(train[cols]), scaler.transform(test[cols])
            for k in (2,3,4):
                for cov in ('diag','full'):
                    candidates = []
                    for seed in SEEDS:
                        row = dict(year=year, features=name, k=k, covariance=cov, seed=seed,
                                   train_start=str(train.index[0].date()), train_end=str(train.index[-1].date()),
                                   test_start=str(test.index[0].date()), test_end=str(test.index[-1].date()),
                                   train_n=len(train), test_n=len(test), status='rejected')
                        try:
                            model = GaussianHMM(n_components=k, covariance_type=cov, n_iter=200,
                                                tol=.05, min_covar=.001, random_state=seed)
                            with threadpool_limits(limits=1):
                                model.fit(x)
                                train_ll = model.score(x)
                            history = np.asarray(model.monitor_.history)
                            delta = history[-1]-history[-2] if len(history)>1 else np.nan
                            probs, _ = forward_filter(model, x)
                            occupancy = np.bincount(probs.argmax(axis=1), minlength=k)/len(x)
                            eigen = np.linalg.eigvalsh(model.covars_)
                            if not np.isfinite(train_ll) or not np.all(np.isfinite(eigen)) or np.min(eigen) <= 0:
                                raise ValueError('invalid likelihood or covariance')
                            if not np.isfinite(delta) or delta < -1e-6 or delta >= .05:
                                raise ValueError(f'no convergence at tolerance; delta={delta:.6g}')
                            if min(occupancy) < .02:
                                raise ValueError(f'train occupancy below 2%: {min(occupancy):.4f}')
                            row.update(status='accepted', train_log_likelihood=float(train_ll),
                                       iterations=int(model.monitor_.iter), min_train_occupancy=float(min(occupancy)))
                            candidates.append((train_ll, model, probs, seed))
                        except (ValueError, np.linalg.LinAlgError, FloatingPointError) as exc:
                            row['reason'] = str(exc)
                        fits.append(row)
                    row = dict(year=year, features=name, k=k, covariance=cov, test_n=len(test),
                               train_end=str(train.index[-1].date()), test_start=str(test.index[0].date()),
                               test_end=str(test.index[-1].date()), status='all seeds rejected')
                    if candidates:
                        selected = max(candidates, key=lambda z:z[0])
                        posterior, score = score_conditional(selected[1], x, y, scaler.scale_)
                        occ = np.bincount(posterior.argmax(axis=1), minlength=k)/len(posterior)
                        alignment = None
                        if len(candidates) > 1:
                            a = candidates[0][2].argmax(axis=1)
                            b = candidates[1][2].argmax(axis=1)
                            contingency = np.array([[( (a==i) & (b==j)).sum() for j in range(k)] for i in range(k)])
                            ia, ib = linear_sum_assignment(-contingency)
                            alignment = float(contingency[ia, ib].sum()/len(a))
                        row.update(status='accepted', seed=int(selected[3]), mean_log_density=score,
                                   min_test_occupancy=float(min(occ)), seed_train_label_agreement=alignment)
                    scores.append(row)
        print(f'completed fold {year}', flush=True)
    output.mkdir(parents=True, exist_ok=False)
    pd.DataFrame(fits).to_csv(output/'fits.csv',index=False)
    pd.DataFrame(scores).to_csv(output/'fold_scores.csv',index=False)
    meta = {'data_sha256':hashlib.sha256(data_path.read_bytes()).hexdigest(),
            'source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'features':SPECS, 'seeds':SEEDS, 'state_counts':[2,3,4], 'covariances':['diag','full'],
            'years':'2012–2026', 'training':'expanding, fit through last session before each year',
            'selection':'highest training likelihood among accepted seeds; test is conditional on train final filtered state',
            'caveats':'Exploratory retrospective grid; raw-space log densities are only comparable within an identical feature set. No untouched holdout.',
            'python':platform.python_version()}
    (output/'config.json').write_text(json.dumps(meta,indent=2)+'\n')

if __name__ == '__main__':
    p=argparse.ArgumentParser(); p.add_argument('--csv',type=Path,required=True); p.add_argument('--output',type=Path,required=True)
    a=p.parse_args(); run(a.csv,a.output)
