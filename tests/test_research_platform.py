from pathlib import Path
import json
import sys

import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient
from hmmlearn.hmm import GaussianHMM

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'research/legacy/src'))
sys.path.insert(0, str(ROOT))
from regime_backtester.features import build_features
from regime_backtester.hmm import forward_filter
from regime_backtester.execution import simulate
from research.analysis.characterize import describe, weighted_mean, weighted_quantile
from research.analysis.model_grid import score_conditional
from backend.research_api import app

RUN = ROOT/'research/experiments/baseline_20261104'


def fitted():
    rng = np.random.default_rng(1)
    x = rng.normal(size=(150, 2))
    m = GaussianHMM(n_components=2, covariance_type='diag', n_iter=20, random_state=1).fit(x)
    return m, x


def test_filter_cannot_see_future():
    m, x = fitted()
    full, _ = forward_filter(m,x)
    truncated, _ = forward_filter(m,x[:80])
    changed = x.copy(); changed[80:] *= 10
    mutated, _ = forward_filter(m,changed)
    np.testing.assert_allclose(full[:80], truncated)
    np.testing.assert_allclose(full[:80], mutated[:80])
    np.testing.assert_allclose(full.sum(axis=1),1)


def test_conditional_score_matches_joint_difference():
    m, x = fitted()
    prob, score = score_conditional(m,x[:100],x[100:],np.array([2.,3.]))
    expected=(m.score(x)-m.score(x[:100]))/50-np.log(6)
    assert score == pytest.approx(expected)
    np.testing.assert_allclose(prob.sum(axis=1),1)


def test_feature_mutation_does_not_change_past():
    prices = pd.read_csv(RUN/'inputs/prices.csv',parse_dates=['Date']).set_index('Date')
    before = build_features(prices)
    changed=prices.copy(); changed.iloc[1000:,changed.columns.get_loc('Close')] *= 1.7
    after=build_features(changed)
    pd.testing.assert_frame_equal(before.iloc[:1000],after.iloc[:1000])


def test_delayed_execution_earns_return_after_next_close():
    dates=pd.date_range('2020-01-01',periods=5)
    signal=pd.Series([1.,0,0,0,0],index=dates)
    returns=pd.Series([0.,.5,.2,0,0],index=dates)
    result=simulate(signal,returns,initial_capital=1000,annual_risk_free_rate=0,
                    trading_days_per_year=252,transaction_cost_bps=0,execution_delay_sessions=1)
    first=result.iloc[0]
    assert first['decision_date'] == dates[0]
    assert first['execution_date'] == dates[1]
    assert result.index[0] == dates[2]
    assert first['strategy_return'] == pytest.approx(.2)


def test_weights_and_refit_boundaries():
    assert weighted_mean([1,3],[1,3]) == pytest.approx(2.5)
    assert weighted_quantile([1,3],[1,3],.5) == 3
    p=pd.read_csv(RUN/'inputs/prices.csv')
    signals=pd.read_csv(RUN/'signals.csv')
    result=describe(p, signals)
    n=sum(map(sum,result['transition_counts']))
    assert n == result['signals'] - result['folds']
    assert sum(s['hard_observations'] for s in result['states']) == result['signals']
    for row in result['transition_probabilities']:
        assert sum(row)==pytest.approx(1)


def test_real_api_and_source_artifacts():
    client=TestClient(app)
    r=client.get('/api/research')
    assert r.status_code==200
    data=r.json()
    assert data['metadata']['data_source']['sha256'] == data['analysis']['provenance']['data_sha256']
    assert data['metadata']['return_observations']==3632
    assert len(data['performance']) == 9
    assert client.get('/api/artifacts/signals').status_code == 200
    assert client.get('/api/artifacts/unknown').status_code == 404
    assert client.get('/api/artifacts/../../README.md').status_code == 404


def test_reproduced_performance_and_delay_consistent():
    perf=pd.read_csv(RUN/'performance.csv').set_index('strategy')
    assert perf.loc['Trend 50','sharpe'] == pytest.approx(.28588758063)
    assert perf.loc['HMM + Trend','sharpe'] == pytest.approx(.28728782744)
    rows=pd.read_csv(RUN/'daily_backtests.csv',parse_dates=['Date','decision_date','execution_date'])
    assert (rows.decision_date < rows.execution_date).all()
    assert (rows.execution_date < rows.Date).all()
    assert (rows.cost_fraction >= 0).all()


def test_forecast_label_maturity_and_common_dates():
    forecast = ROOT/'research/experiments/forecast_20261104'
    pred = pd.read_csv(forecast/'predictions.csv',parse_dates=['date','train_last_label_end'])
    assert (pred.train_last_label_end < pred.date).all()
    assert pred.groupby('horizon').date.nunique().nunique()==1
    for horizon in (1,5,20,60):
        assert pred[pred.horizon==horizon].date.tolist() == pred[pred.horizon==1].date.tolist()
    metrics = pd.read_csv(forecast/'metrics.csv')
    assert (metrics.loc[metrics.year == 'all','oos_r2_vs_expanding_mean'] < 0).all()
    intervals = pd.read_csv(forecast/'simultaneous_intervals.csv')
    assert len(intervals)==8
    assert (intervals.simultaneous_95_lower <= intervals.simultaneous_95_upper).all()


def test_api_rejects_changed_signal_file(tmp_path, monkeypatch):
    import backend.research_api as api
    import shutil
    copied=tmp_path/'run'; copied.mkdir()
    for name in ('metadata.json','signals.csv'):
        shutil.copy(RUN/name, copied/name)
    (copied/'inputs').mkdir()
    shutil.copy(RUN/'inputs/prices.csv',copied/'inputs/prices.csv')
    with (copied/'signals.csv').open('a') as f: f.write('corrupt')
    monkeypatch.setattr(api,'RUN',copied)
    assert TestClient(app).get('/api/research').status_code==503


def test_dashboard_same_origin_routes_and_missing_build(tmp_path, monkeypatch):
    import backend.research_api as api
    monkeypatch.setattr(api, 'FRONTEND_DIST', tmp_path)
    client = TestClient(app)
    assert client.get('/').status_code == 503
    (tmp_path/'index.html').write_text('<html>dashboard</html>')
    for route in ('/', '/regimes', '/strategies', '/validation'):
        response = client.get(route)
        assert response.status_code == 200
        assert response.headers['content-type'].startswith('text/html')
        assert 'dashboard' in response.text
    assert client.get('/api/not-a-route').status_code == 404
    assert client.get('/api/research').status_code == 200


def test_dashboard_build_assets_when_available():
    from backend.research_api import FRONTEND_DIST
    import re
    index = FRONTEND_DIST/'index.html'
    if not index.is_file():
        pytest.skip('Frontend has not been built')
    asset = re.search(r'src="(/assets/[^"]+\.js)"', index.read_text())
    assert asset is not None
    response = TestClient(app).get(asset.group(1))
    assert response.status_code == 200
    assert 'javascript' in response.headers['content-type']
