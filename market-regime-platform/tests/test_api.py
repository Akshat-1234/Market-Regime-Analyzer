"""Artifact-backed API tests use the completed, supplied-data research run."""
import math
from pathlib import Path

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from backend.app import app, RUNS_DIR


@pytest.fixture(scope="module")
def client():
    return TestClient(app)


@pytest.fixture(scope="module")
def run_id(client):
    rows = client.get('/api/runs').json()['runs']
    completed = [x for x in rows if x['status'] == 'completed' and x['has_research_artifacts']]
    # The documented reference run (081436) retains only figures/inputs/logs/reports/
    # source, so it carries no research artifacts.  Fall back to any completed run
    # that does, rather than skipping the whole artifact API surface.
    ref = next((x['run_id'] for x in completed if x['run_id'] == 'run_20261030_081436_12ea5b'), None)
    if ref is None and completed:
        ref = completed[0]['run_id']
    if ref is None:
        pytest.skip('Bundled reference run unavailable; generate or restore it for artifact integration tests')
    return ref


def test_health_and_completed_runs(client, run_id):
    assert client.get('/').json()['service'] == 'PROFNITT research API'
    assert client.get('/api/health').json()['mode'] == 'historical artifacts only'
    assert run_id is not None, 'Generate a research run first'
    overview=client.get(f'/api/runs/{run_id}/overview')
    assert overview.status_code == 200
    body=overview.json()
    assert body['metadata']['data_end']=='2026-10-22'
    assert body['holdout']['evaluation_decision_date_strictly_after']>='2026-10-30'
    assert body['holdout']['status'].startswith('PENDING')


def test_full_and_filtered_series_recompute_from_daily_returns(client, run_id):
    prefix=f'/api/runs/{run_id}'
    response=client.get(prefix+'/series',params={'strategies':'Trend 50,HMM + Trend','max_points':80})
    assert response.status_code==200
    body=response.json()
    assert body['observations']==3632 and len(body['equity'])==80
    perf={r['strategy']:r for r in client.get(prefix+'/overview').json()['performance']}
    for row in body['stats']:
        assert row['sharpe']==pytest.approx(perf[row['strategy']]['sharpe'],abs=1e-10)
        assert row['cagr']==pytest.approx(perf[row['strategy']]['cagr'],abs=1e-10)
        assert row['max_drawdown']==pytest.approx(perf[row['strategy']]['max_drawdown'],abs=1e-10)
    filtered=client.get(prefix+'/series',params={'start':'2020-01-01','end':'2020-12-31','strategies':'Trend 50'}).json()
    assert filtered['observations']<body['observations']
    actual=pd.read_csv(RUNS_DIR/run_id/'daily_returns.csv')
    actual=actual.loc[actual.Date.between('2020-01-01','2020-12-31'),'Trend 50']
    assert filtered['stats'][0]['total_return']==pytest.approx((1+actual).prod()-1,abs=1e-10)


def test_invalid_filters_and_unknown_exports(client,run_id):
    base=f'/api/runs/{run_id}'
    assert client.get(base+'/series',params={'start':'2021-01-01','end':'2020-01-01'}).status_code==422
    assert client.get(base+'/series',params={'start':'wrong'}).status_code==422
    assert client.get(base+'/series',params={'strategies':'fabricated'}).status_code==422
    assert client.get(base+'/regime',params={'model':'fabricated'}).status_code==422
    assert client.get(base+'/export/not_an_artifact').status_code==404
    assert client.get('/api/runs/run_missing/overview').status_code==404
    assert client.get(base+'/export/performance').headers['content-type'].startswith('text/csv')


def test_regime_occupancy_and_real_artifacts(client,run_id):
    base=f'/api/runs/{run_id}'
    body=client.get(base+'/regime',params={'model':'rvd_3','start':'2020-01-01','end':'2020-12-31'}).json()
    assert 200 < body['observations'] < 260
    assert sum(x['days'] for x in body['occupancy'])==body['observations']
    assert sum(x['occupancy'] for x in body['occupancy'])==pytest.approx(1)
    assert all('close' in x and 'p0' in x for x in body['points'])
    attr=client.get(base+'/attribution').json()
    assert len(attr['simulations']) == 600
    assert len(attr['bootstrap']) == 4
    valid=client.get(base+'/validation').json()
    assert len(valid['folds'])==135 and len(valid['stress'])==36
    assert len(client.get(base+'/quality').json()['pca'])==16


def test_job_validation_without_starting_background_work(client):
    assert client.get('/api/job').status_code==200
    for body in ({'simulations':1},{'control_history':1},{'execution_delay':4},{'start':'nonsense'}):
        assert client.post('/api/job',json=body).status_code==422


def test_compare_run_histories_reports_method_differences(client):
    rows=client.get('/api/runs').json()['runs']
    names=['run_20261030_081436_12ea5b','run_20261030_080824_12346d']
    runs=[r for n in names for r in rows if r['run_id']==n and r['status']=='completed' and r['has_research_artifacts']]
    if len(runs)<2: pytest.skip('Comparison requires the two reference runs')
    ids=','.join(r['run_id'] for r in runs)
    response=client.get('/api/compare-runs',params={'run_ids':ids})
    assert response.status_code==200
    body=response.json()
    assert len(body['runs'])==2
    assert body['runs'][0]['real_sharpe']==pytest.approx(body['runs'][1]['real_sharpe'],abs=1e-12)
    assert not body['strictly_comparable']
    assert any('lookbacks differ' in w for w in body['warnings'])
    assert client.get('/api/compare-runs',params={'run_ids':runs[0]['run_id']}).status_code==422
