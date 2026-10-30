from datetime import datetime, timezone
import numpy as np
import pandas as pd
import pytest

from regime_backtester.attribution import CONTROL_NAMES, causal_control, _refresh_probabilities
from regime_backtester.config import load_config
from regime_backtester.data import synthetic_prices
from regime_backtester.execution import simulate
from regime_backtester.research_metrics import evaluate_window, recovery_details
from regime_backtester.risk_free import align_auction_yields
from regime_backtester.stress_testing import stress_analysis
from regime_backtester.validation import freeze_manifest, validate_prospective_extension


@pytest.mark.parametrize('kind', CONTROL_NAMES)
def test_controls_are_prefix_causal(kind):
    rng = np.random.default_rng(18)
    x = rng.uniform(.3, 1.0, 180)
    full = causal_control(x, kind, seed=46, block_length=20)
    prefix = causal_control(x[:97], kind, seed=46, block_length=20)
    changed = x.copy(); changed[97:] = 0.03
    mutated = causal_control(changed, kind, seed=46, block_length=20)
    np.testing.assert_allclose(full[:97], prefix)
    np.testing.assert_allclose(full[:97], mutated[:97])
    np.testing.assert_allclose(_refresh_probabilities(x)[:97], _refresh_probabilities(x[:97]))


def test_sortino_uses_all_days_and_recovery_is_censored():
    idx = pd.bdate_range('2020-01-01',periods=3)
    df = pd.DataFrame({'strategy_return':[.1,-.1,.1], 'target_exposure':1.,
                       'turnover':0.,'cost_fraction':0.},index=idx)
    got = evaluate_window(df, 0, 252)
    assert got['sortino'] == pytest.approx(np.sqrt(252) * np.mean([.1,-.1,.1]) / np.sqrt(.1**2/3))
    rec = recovery_details(np.array([-.2,.05]))
    assert rec['recovery_status'] == 'not_recovered_by_window_end'
    assert rec['sessions_to_recover'] is None


def test_cash_rate_is_lagged_and_staleness_rejected(tmp_path):
    p=tmp_path/'r.csv'
    pd.DataFrame({'auction_date':['2020-01-01','2020-01-08'], 'cutoff_yield_percent':[4,8]}).to_csv(p,index=False)
    dates=pd.to_datetime(['2020-01-07','2020-01-08','2020-01-09'])
    rates,aligned=align_auction_yields(p,dates,max_age_days=14)
    np.testing.assert_allclose(rates,[.04,.04,.08])
    assert (aligned.auction_date < aligned.Date).all()
    with pytest.raises(ValueError,match='older'):
        align_auction_yields(p,pd.to_datetime(['2020-03-01']),max_age_days=14)


def test_dynamic_cash_uses_execution_date_not_future_date():
    idx=pd.bdate_range('2020-01-01',periods=4)
    s=pd.Series([0,0,0,0],index=idx)
    market=pd.Series([np.nan,0,0,0],index=idx)
    rates=pd.Series([.01,.02,.03,.99],index=idx)
    run=simulate(s,market,initial_capital=1000,annual_risk_free_rate=0,trading_days_per_year=252,
                 transaction_cost_bps=0,execution_delay_sessions=0,risk_free_annual_by_date=rates)
    np.testing.assert_allclose(run.strategy_return,[(1+x)**(1/252)-1 for x in [.01,.02,.03]],atol=1e-12)


def test_stress_boundaries_use_common_calendar():
    idx=pd.bdate_range('2012-12-20','2014-01-15')
    f=pd.DataFrame({'strategy_return':.001,'target_exposure':1.,'turnover':0.,'cost_fraction':0.},index=idx)
    result=stress_analysis({'Buy & Hold':f,'Trend 50':f.copy()},load_config())
    rows=result[result.period=='2013']
    assert len(rows)==2 and rows.actual_start.min()>=pd.Timestamp('2013-01-01')
    assert rows.actual_end.max()<=pd.Timestamp('2013-12-31')
    assert rows.return_difference_vs_buy_hold.eq(0).all()


def test_freeze_and_extension_do_not_treat_prefreeze_as_prospective():
    c=load_config(); orig=synthetic_prices(12)
    now=datetime(2008,1,25,9,0,tzinfo=timezone.utc)
    m=freeze_manifest(c,'datahash',str(orig.index[-1].date()),'sourcehash',now)
    assert m['evaluation_decision_date_strictly_after']=='2008-01-25'
    with pytest.raises(ValueError,match='pending'):
        validate_prospective_extension(orig,orig,m)
    extended=synthetic_prices(25)
    # same seed, but random price arrays depend on n; overwrite the original prefix
    extended.loc[orig.index,orig.columns]=orig
    validate_prospective_extension(orig,extended,m)
    extended.iloc[0,extended.columns.get_loc('Close')] *= 1.1
    with pytest.raises(ValueError,match='revises'):
        validate_prospective_extension(orig,extended,m)


@pytest.mark.parametrize('kind', CONTROL_NAMES)
@pytest.mark.parametrize('history', [None, 2, 63])
def test_control_windows_never_use_future_or_current_exposure(kind, history):
    values=np.linspace(.25,.95,121)
    original=causal_control(values,kind,seed=64,history_window=history)
    changed=values.copy();changed[80:]=.01
    mutated=causal_control(changed,kind,seed=64,history_window=history)
    # After initialization, day t may use only the exposure history through t-1.
    np.testing.assert_allclose(original[:81],mutated[:81])
    np.testing.assert_allclose(original[:80],causal_control(values[:80],kind,seed=64,history_window=history))


def test_recorded_freeze_matches_latest_core_source_and_requires_future_data():
    import json
    from pathlib import Path
    from regime_backtester.experiment_tracking import core_source_sha256
    from regime_backtester.holdout import prospective_evaluation
    root=Path(__file__).resolve().parents[1]
    latest=root/'runs'/'run_20261030_081436_12ea5b'
    if not (latest/'holdout_freeze.json').exists(): pytest.skip('Reference freeze not present')
    freeze=json.loads((latest/'holdout_freeze.json').read_text())
    assert freeze['source_code_sha256']==core_source_sha256()
    with pytest.raises(ValueError,match='pending'):
        prospective_evaluation(str(latest/'holdout_freeze.json'),str(root/'data/raw/nifty_index.csv'),str(root/'data/raw/nifty_index.csv'))


def test_selected_control_diagnostics_are_reported_not_assumed():
    from pathlib import Path
    root=Path(__file__).resolve().parents[1]
    latest=root/'runs'/'run_20261030_081436_12ea5b'
    if not (latest/'attribution_simulations.csv').exists(): pytest.skip('Reference simulations not present')
    sims=pd.read_csv(latest/'attribution_simulations.csv')
    matched=sims[sims.control==CONTROL_NAMES[2]]
    assert len(matched)==200
    assert matched.hmm_exposure_ks_distance.notna().all()
    assert 0 < matched.hmm_exposure_ks_distance.median() < .15  # approximate, not exact
    assert matched.turnover_per_year.notna().all()
