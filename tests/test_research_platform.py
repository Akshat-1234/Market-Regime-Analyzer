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


def test_task4_api_serves_verified_results_and_rejects_tampering(tmp_path, monkeypatch):
    import backend.research_api as api
    import shutil
    client = TestClient(app)
    response = client.get('/api/task4/discovery')
    assert response.status_code == 200
    data = response.json()
    assert data['summary']['inner_candidate_attempts'] == 1512
    assert data['summary']['selected_outer_refits'] == 14
    assert data['summary']['total_retained_attempts'] == 1526
    assert data['summary']['selected_state_count_frequency'] == {'5': 14}
    assert data['occupancy']['fold_state_observations'] == 70
    assert data['occupancy']['zero_hard_assignments'] == 26
    assert data['occupancy']['years_with_empty_state'] == 13
    assert len(data['occupancy']['rows']) == 70
    assert data['stability']['alignment_counts'] == {'accepted': 41, 'ambiguous': 16, 'new_unmatched': 8}
    assert data['stability']['candidate_changes'] == 8
    assert data['stability']['folds'][-1]['alignment_status_counts']['ambiguous'] == 5
    assert data['reproducibility']['core_artifacts_matched'] == 98
    assert data['reproducibility']['global_fold_objects_matched'] == 42
    assert data['reproducibility']['initial_failure']['candidate_attempt_records_lost_in_memory'] is True
    assert client.get('/api/artifacts/task4-occupancy').status_code == 200
    assert client.get('/api/artifacts/task4-candidate-rankings').status_code == 200
    assert client.get('/api/artifacts/task4-seed-sensitivity').status_code == 200
    original_analysis = api.TASK4_ANALYSIS
    copied_analysis = tmp_path/'task4-analysis'
    shutil.copytree(original_analysis, copied_analysis)
    with (copied_analysis/'candidate_rankings.csv').open('a') as handle:
        handle.write(' ')
    monkeypatch.setattr(api, 'TASK4_ANALYSIS', copied_analysis)
    rejected_analysis = client.get('/api/task4/discovery')
    assert rejected_analysis.status_code == 503
    assert 'candidate_rankings.csv' in rejected_analysis.json()['detail']
    monkeypatch.setattr(api, 'TASK4_ANALYSIS', original_analysis)
    copied = tmp_path/'task4-run'
    shutil.copytree(api.TASK4_RUN, copied)
    with (copied/'aggregate_results.json').open('a') as handle:
        handle.write(' ')
    monkeypatch.setattr(api, 'TASK4_RUN', copied)
    rejected = client.get('/api/task4/discovery')
    assert rejected.status_code == 503
    assert 'hash mismatch' in rejected.json()['detail']


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
    for route in ('/', '/regimes', '/task4', '/strategies', '/validation'):
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


def test_equity_api_samples_only_saved_rows():
    data = TestClient(app).get('/api/research').json()
    saved = pd.read_csv(RUN/'equity_curves.csv')
    indices = sorted(set(range(0, len(saved), 10)) | {len(saved)-1})
    expected = saved.iloc[indices].reset_index(drop=True)
    actual = pd.DataFrame(data['curves'])
    sampling = data['curve_sampling']
    assert sampling == {
        'stride': 10, 'final_observation_included': True,
        'saved_rows': 3632, 'displayed_rows': 365,
        'start_date': '2012-01-05', 'end_date': '2026-10-22',
        'initial_capital_assumption': 1000, 'value_column_unit': 'account equity'}
    assert actual['Date'].tolist() == expected['Date'].tolist()
    for column in ('Buy & Hold', 'Trend 50', 'HMM Ensemble', 'HMM + Trend'):
        np.testing.assert_allclose(actual[column], expected[column], rtol=0, atol=1e-12)


def test_task4_selection_diagnostics_match_verified_rankings():
    data = TestClient(app).get('/api/task4/discovery').json()
    diagnostics = data['selection_diagnostics']
    rankings = pd.read_csv(ROOT/'research/experiments/task4_v1_0_0_analysis/candidate_rankings.csv')
    expected_margins = []
    for fold_id, rows in rankings.groupby('fold_id', sort=True):
        ordered = rows.sort_values('rank').iloc[:2]
        best, runner_up = ordered.iloc[0], ordered.iloc[1]
        gap = best.mean_inner_raw_log_density_per_observation - runner_up.mean_inner_raw_log_density_per_observation
        expected_margins.append((fold_id, best.candidate_id, runner_up.candidate_id, gap))
    assert len(diagnostics['margins']) == len(expected_margins) == 14
    for actual, expected in zip(diagnostics['margins'], expected_margins):
        fold_id, best, runner_up, gap = expected
        assert actual['fold_id'] == fold_id
        assert actual['best_candidate_id'] == best
        assert actual['runner_up_candidate_id'] == runner_up
        assert actual['score_gap'] == pytest.approx(gap)
        assert actual['near_tie'] == (gap < 0.005)
    assert diagnostics['near_tie_folds'] == sum(gap < 0.005 for *_, gap in expected_margins) == 11
    assert len(diagnostics['seed_sensitivity']) == 42
    assert data['summary']['selected_seed_frequency'] == {'2': 3, '42': 7, '7': 4}
    assert data['summary']['accepted_attempts'] == data['summary']['converged_attempts'] == 1526
    assert data['summary']['rejected_attempts'] == 0
    assert data['summary']['failed_attempts'] == data['summary']['nonconverged_attempts'] == 0


def test_task4_occupancy_and_alignment_preserve_saved_semantics():
    data = TestClient(app).get('/api/task4/discovery').json()
    saved = pd.read_csv(ROOT/'research/experiments/task4_v1_0_0_analysis/state_occupancy.csv')
    outer = saved[saved['sample'] == 'outer_test'].reset_index(drop=True)
    actual = pd.DataFrame(data['occupancy']['rows'])
    assert len(actual) == len(outer) == 70
    for column in ('fold_id', 'sample', 'local_state_id', 'rare'):
        assert actual[column].tolist() == outer[column].tolist()
    assert actual['aligned_state_id'].fillna('').tolist() == outer['aligned_state_id'].fillna('').tolist()
    for column in ('hard_count', 'hard_fraction', 'posterior_weight', 'effective_sample_size'):
        np.testing.assert_allclose(actual[column], outer[column], rtol=0, atol=1e-12)
    assert (outer['hard_count'] == 0).sum() == 26
    assert outer['rare'].sum() == 58
    folds = data['stability']['folds']
    assert len(folds) == 14
    assert folds[0]['reference_fold_id'] is None
    assert folds[0]['alignment_status_counts'] == {'initial_unaligned': 5}
    subsequent_counts = {}
    for row in folds[1:]:
        for status, count in row['alignment_status_counts'].items():
            subsequent_counts[status] = subsequent_counts.get(status, 0) + count
    assert subsequent_counts == {'accepted': 41, 'ambiguous': 16, 'new_unmatched': 8}
    assert sum(subsequent_counts.values()) == 13 * 5


def test_baseline_and_task4_failures_are_independent(monkeypatch):
    from fastapi import HTTPException
    import backend.research_api as api
    client = TestClient(app)
    monkeypatch.setattr(api, 'check', lambda: (_ for _ in ()).throw(HTTPException(503, 'forced baseline failure')))
    assert client.get('/api/research').status_code == 503
    task4_response = client.get('/api/task4/discovery')
    assert task4_response.status_code == 200
    assert task4_response.json()['summary']['total_retained_attempts'] == 1526
    monkeypatch.undo()
    monkeypatch.setattr(api, 'task4_check', lambda: (_ for _ in ()).throw(HTTPException(503, 'forced Task 4 failure')))
    assert client.get('/api/task4/discovery').status_code == 503
    baseline_response = client.get('/api/research')
    assert baseline_response.status_code == 200
    assert len(baseline_response.json()['performance']) == 9


def test_removed_project_download_route():
    client = TestClient(app)
    assert client.get('/api/download').status_code == 404
    assert '/api/download' not in {route.path for route in app.routes}
