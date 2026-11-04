"""Exploratory walk-forward forecasting with matured training labels.

Signals are saved OOS filtered ranks, not full-sample decoded states. Forecasts
are at close t for the subsequent h-close return; not executable strategy P&L.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'research/legacy/src'))
from regime_backtester.features import build_features

HORIZONS=(1,5,20,60)
INDICATORS=['daily_return','volatility_20','return_20','return_60','drawdown_252']

def stationary_indices(n, mean_block, rng):
    """Circular stationary bootstrap, geometric block lengths."""
    ix=np.empty(n,dtype=int)
    ix[0]=rng.integers(n)
    for i in range(1,n):
        ix[i]=rng.integers(n) if rng.random()<1/mean_block else (ix[i-1]+1)%n
    return ix


def run(run_path:Path, output:Path, samples=1000, seed=1701, block=60):
    if output.exists(): raise ValueError('Output already exists')
    prices=pd.read_csv(run_path/'inputs/prices.csv',parse_dates=['Date']).set_index('Date')
    signals=pd.read_csv(run_path/'signals.csv',parse_dates=['decision_date']).set_index('decision_date')
    if not prices.index.is_monotonic_increasing or not prices.index.is_unique or not signals.index.is_unique:
        raise ValueError('Input dates must be unique and sorted')
    feat=build_features(prices)
    probs=signals[['p_state_0','p_state_1','p_state_2']]
    if not np.allclose(probs.sum(axis=1),1) or probs.isna().any().any(): raise ValueError('Invalid probabilities')
    data=feat[INDICATORS].join(probs,how='inner')
    p=data[['p_state_0','p_state_1','p_state_2']].to_numpy()
    data['entropy']=-np.sum(p*np.log(np.maximum(p,1e-300)),axis=1)/np.log(3)
    # Labels are indexed by the decision date and their actual end date is retained.
    dates=pd.Series(prices.index,index=prices.index)
    for h in HORIZONS:
        data[f'y{h}']=(prices.Close.shift(-h)/prices.Close-1).reindex(data.index)
        data[f'end{h}']=dates.shift(-h).reindex(data.index)
    data=data.dropna(subset=INDICATORS+['p_state_0','p_state_1','p_state_2'])
    groups={'indicators':INDICATORS,
            'plus_regimes':INDICATORS+['p_state_0','p_state_1'],
            'plus_regimes_entropy':INDICATORS+['p_state_0','p_state_1','entropy']}
    rows=[]
    for year in range(2014,2027):
        # All evaluated horizons use the exact same dates for synchronized inference.
        test=data[(data.index.year==year)&data['y60'].notna()]
        if test.empty: continue
        start=test.index[0]
        for h in HORIZONS:
            train=data[(data.index<start)&(data[f'end{h}']<start)&data[f'y{h}'].notna()]
            if len(train)<250: raise ValueError(f'Insufficient matured training labels for {year}/{h}')
            y=train[f'y{h}']; target=test[f'y{h}'].to_numpy()
            predictions={'historical_mean':np.full(len(test),y.mean())}
            for model,cols in groups.items():
                # Training-only scaling; fixed regularization, not tuned on OOS outcomes.
                estimator=make_pipeline(StandardScaler(),Ridge(alpha=10.0))
                estimator.fit(train[cols],y)
                predictions[model]=estimator.predict(test[cols])
            for i,date in enumerate(test.index):
                row={'date':date.strftime('%Y-%m-%d'),'year':year,'horizon':h,
                     'train_n':len(train),'train_last_label_end':train[f'end{h}'].max().strftime('%Y-%m-%d'),
                     'target':float(target[i])}
                row.update({k:float(v[i]) for k,v in predictions.items()})
                rows.append(row)
        print(f'completed forecast fold {year}',flush=True)
    predictions=pd.DataFrame(rows)
    metrics=[]
    for (h,year), fold in predictions.groupby(['horizon','year']):
        baseline=((fold.target-fold.historical_mean)**2).sum()
        for m in groups:
            e=fold.target-fold[m]
            metrics.append({'horizon':h,'year':int(year),'model':m,'n':len(fold),
                            'rmse':float(np.sqrt(np.mean(e**2))),
                            'oos_r2_vs_expanding_mean':float(1-(e**2).sum()/baseline) if baseline>0 else None})
    for h,fold in predictions.groupby('horizon'):
        baseline=((fold.target-fold.historical_mean)**2).sum()
        for m in groups:
            e=fold.target-fold[m]
            metrics.append({'horizon':h,'year':'all','model':m,'n':len(fold),
                            'rmse':float(np.sqrt(np.mean(e**2))),
                            'oos_r2_vs_expanding_mean':float(1-(e**2).sum()/baseline) if baseline>0 else None})
    # All columns share dates; one bootstrap path resamples each paired loss vector.
    common=[]; names=[]
    for h in HORIZONS:
        fold=predictions[predictions.horizon==h].sort_values('date')
        dates_h=fold.date.to_numpy()
        if common and not np.array_equal(dates_h,dates_common): raise ValueError('Inconsistent forecast dates')
        dates_common=dates_h
        control=(fold.target-fold.indicators)**2
        for m in ('plus_regimes','plus_regimes_entropy'):
            common.append((control-(fold.target-fold[m])**2).to_numpy())
            names.append((h,m))
    loss=np.column_stack(common)
    means=loss.mean(axis=0)
    rng=np.random.default_rng(seed)
    boots=np.array([loss[stationary_indices(len(loss),block,rng)].mean(axis=0) for _ in range(samples)])
    sd=boots.std(axis=0,ddof=1)
    if np.any(sd<=0): raise ValueError('Degenerate bootstrap')
    maxstats=np.max(np.abs((boots-means)/sd),axis=1)
    critical=float(np.quantile(maxstats,.95))
    intervals=[]
    for j,(h,m) in enumerate(names):
        intervals.append({'horizon':h,'model':m,'control':'indicators','mean_squared_error_improvement':float(means[j]),
                          'simultaneous_95_lower':float(means[j]-critical*sd[j]),
                          'simultaneous_95_upper':float(means[j]+critical*sd[j])})
    output.mkdir(parents=True,exist_ok=False)
    predictions.to_csv(output/'predictions.csv',index=False)
    pd.DataFrame(metrics).to_csv(output/'metrics.csv',index=False)
    pd.DataFrame(intervals).to_csv(output/'simultaneous_intervals.csv',index=False)
    config={'run':run_path.name,'data_sha256':hashlib.sha256((run_path/'inputs/prices.csv').read_bytes()).hexdigest(),
            'signals_sha256':hashlib.sha256((run_path/'signals.csv').read_bytes()).hexdigest(),
            'source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'period':'2014–2026; common dates with available 60-session outcome',
            'horizons':list(HORIZONS),'indicators':INDICATORS,'models':groups,'ridge_alpha':10,
            'training':'expanding previous OOS signals with target end strictly before test start',
            'baseline':'expanding training mean, same fold and horizon',
            'inference':'synchronized circular stationary bootstrap, centered max absolute standardized statistic, simultaneous intervals across 8 comparisons; expected block length 60, stationary approximation',
            'bootstrap_samples':samples,'seed':seed,'critical_value':critical,
            'caveat':'Retrospective exploratory analysis after previous research; not corrected for earlier specification search. Forecast after close is not executable P&L.'}
    (output/'config.json').write_text(json.dumps(config,indent=2)+'\n')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--run',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    args=p.parse_args();run(args.run,args.output)
