"""Generate research reports from actual experiment tables."""
from __future__ import annotations
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


def table(frame: pd.DataFrame, cols: list[str], limit: int | None = None) -> str:
    if frame.empty or any(c not in frame.columns for c in cols):
        return 'No observations or artifacts available for this section.'
    f = frame[cols].head(limit) if limit else frame[cols]
    def fmt(v):
        if pd.isna(v): return '—'
        if isinstance(v,(float,np.floating)): return f'{v:.4f}'
        return str(v).replace('|','\\|')
    return '\n'.join(['| '+' | '.join(cols)+' |', '| '+' | '.join(['---']*len(cols))+' |'] +
                     ['| '+' | '.join(fmt(x) for x in row)+' |' for row in f.itertuples(index=False,name=None)])


def write_research_reports(out: Path, result, attrib, folds, aggregate, stress, quality, model, holdout, cash, run_id: str, control_history: int | None = 63) -> None:
    reportdir=out/'reports'; reportdir.mkdir(exist_ok=True)
    m=result.metadata;b=result.config['backtest'];sims=attrib.simulations
    header=(f'Run: `{run_id}` · source data: {m["data_start"]}–{m["data_end"]} · '
            f'OOS returns: {m["first_return_date"]}–{m["last_return_date"]} · '
            f'{b["transaction_cost_bps"]:g} bps one-way · cash {b["annual_risk_free_rate"]:.1%} · '
            f'extra execution delay {b["execution_delay_sessions"]} session(s).\n\n')
    summary=attrib.metrics
    performance=table(result.performance.reset_index(),['strategy','cagr','sharpe','max_drawdown','calmar','mean_exposure','turnover_per_year'])
    boot=table(attrib.bootstrap,['control','observed_sharpe_difference','lower','upper','fraction_le_zero'])
    real=summary[summary.control=='Trend + real HMM'].iloc[0]
    trend=summary[summary.control=='Trend alone'].iloc[0]
    report=(f'# HMM incremental-value attribution\n\n{header}'
            f'Real HMM + Trend Sharpe {real.sharpe:.3f} vs Trend {trend.sharpe:.3f}; '
            f'maximum drawdown {real.max_drawdown:.1%} vs {trend.max_drawdown:.1%}. '
            'These are descriptive estimates, not proof of a true improvement.\n\n'
            '## Controls\n\n'+table(summary,['control','n_simulations','cagr','sharpe','sharpe_p05','sharpe_p95','max_drawdown','mean_exposure','turnover_per_year','median_hmm_exposure_ks','fraction_real_sharpe_above_control'])+
            '\n\nControl p05/p95 are empirical simulation quantiles, **not** confidence intervals on market performance or p-values. '
            'The fraction real exceeds control is a descriptive fraction, not a formal significance test.\n\n'
            f'All controls only sample HMM exposures observed before each decision, using a {str(control_history) + "-session rolling" if control_history else "full-history"} lookback. '
            'The rolling default was selected after inspecting preliminary full-history match diagnostics, not pre-registered; '
            'the previous full-history run is preserved for sensitivity. This adds selection risk. The first '
            'point initializes from the current real HMM; subsequent shuffled draws are prior-only resampling '
            'with replacement, block draws copy already completed historical blocks, and the matched random '
            'control uses a past-only redraw/hold rule. Therefore the distributions match only approximately. '
            'Exposure KS, percentiles and turnover differences are recorded per simulation. '
            'Shuffled paths can have substantially greater turnover; results include actual costs and a separately '
            'labelled approximate common-fee-schedule Sharpe diagnostic. The latter is a counterfactual, not a tradable backtest.\n\n'
            '## Paired bootstrap vs trend and the mean of simulated controls\n\n'+boot+
            '\n\nEach control reference here is the daily equal-weight mean return across its simulations; '
            'it is not a confidence interval against a single random control. Bootstrap fractions are not p-values. '
            'Intervals spanning zero do not prove equivalence. Block bootstrap assumes local stationarity and does '
            'not correct for the previous search across many configurations. Economic magnitude must be interpreted '
            'alongside turnover, exposure and costs.\n\n'
            '## Market-period comparison\n\n'+table(attrib.periods,['period','control','real_sharpe','trend_sharpe','control_sharpe_median','fraction_real_above_control'])+
            '\n\nShort stress windows have noisy annualized ratios. [Simulation CSV](../attribution_simulations.csv) · '
            '[Distribution chart](../figures/attribution_sharpe.png).\n')
    (reportdir/'hmm_attribution.md').write_text(report,encoding='utf-8')
    (reportdir/'walk_forward.md').write_text('# Walk-forward validation\n\n'+header+
      'Annual refits train strictly before the first signal. Fold membership follows decision dates; '
      'return dates can extend across a calendar boundary because of execution delay. Fold drawdown '
      'is rebased within each fold, without artificial liquidation. Aggregate metrics below are recalculated '
      'from the complete OOS daily return series, **not** averages of fold ratios.\n\n'+
      table(aggregate,['strategy','observations','cagr','sharpe','sortino','max_drawdown','mean_exposure','turnover_per_year'])+
      '\n\nFull fold dates, costs and metrics: [fold_metrics.csv](../fold_metrics.csv).\n',encoding='utf-8')
    (reportdir/'stress_periods.md').write_text('# Stress-period analysis\n\n'+header+
      'Windows are fixed calendar years: 2013, 2015–2016, 2020 including COVID crash and recovery, and 2022. '
      'Returns are sliced from the original continuous portfolio (no extra entry or terminal sale). '
      'Recovery is the number of sessions from the window-local peak through recovery; if none occurs by the '
      'window end it is right-censored. Periods were not selected using this run’s winners.\n\n'+
      table(stress[stress.strategy.isin(['Buy & Hold',f"Trend {b['trend_window']}",'HMM + Trend'])] if 'strategy' in stress else stress,
            ['period','strategy','total_return','cagr','sharpe','max_drawdown','recovery_status','mean_exposure','turnover_per_year','return_difference_vs_buy_hold'])+
      '\n\nFull strategy table: [stress_periods.csv](../stress_periods.csv).\n',encoding='utf-8')
    (reportdir/'data_quality.md').write_text('# Data quality and features\n\n'+header+
      f'Duplicate dates: {quality["summary"]["raw_duplicate_dates"]}; invalid OHLC relationships: '
      f'{quality["summary"]["invalid_ohlc_rows"]}; absolute close-return >5%: '
      f'{quality["summary"]["extreme_return_days"]} sessions; zero-return days: '
      f'{quality["summary"]["zero_return_days"]}. Weekdays lacking a row: '
      f'{quality["summary"]["weekday_candidates_without_rows"]}; these include exchange holidays and are '
      'not certified missing trading sessions.\n\n'
      'Unusual Open/previous-Close gaps and high return correlations, if present below, warrant vendor verification, not '
      'automatic deletion. The default HMM uses Close-derived features only. The 16-feature PCA and '
      'correlation diagnostics are fitted on observations before the first OOS signal, and are not '
      'used to tune the default model.\n\n'+
      table(quality['annual'].head(5),['year','observations','overnight_gap_vol_daily','intraday_vol_daily','close_intraday_return_correlation','near_previous_close_within_1bp'])+
      '\n\n[All quality data](../data_quality_annual.csv) · [Flags](../data_quality_flags.csv) · '
      '[Weekday candidates](../data_quality_weekday_candidates.csv) · [PCA](../pca_variance.csv).\n',encoding='utf-8')
    (reportdir/'model_diagnostics.md').write_text('# HMM fit and state diagnostics\n\n'+header+
      'Failed seeds are recorded in fits.csv; a fold with no acceptable fit aborts the run. '
      'No look-ahead fallback or forced occupancy balancing is used. State labels are volatility ranks '
      'within a fitted model, not stable identities across models or years. Identical exposure pairs '
      'are compared within each fit at tolerance 1e-6.\n\n'+
      table(model['model_diagnostics'],['model','signal_days','unique_daily_exposures_1e6','fraction_near_full_exposure','mean_exposure','rejected_seed_fits'])+
      '\n\n[State pair allocation details](../state_allocation_diagnostics.csv) · [Occupancy](../model_occupancy.csv).\n',encoding='utf-8')
    (reportdir/'strategy_comparison.md').write_text('# Strategy comparison\n\n'+header+performance+
      '\n\nFull data: [performance.csv](../performance.csv). Costs include entries and daily fractional rebalancing; '
      'index price returns omit dividends and a real investable proxy would differ.\n',encoding='utf-8')
    retrospective_label = (f"**Retrospective** {holdout['start'].min()} through {holdout['end'].max()} has already been examined, so it is NOT an untouched holdout. "
                           if not holdout.empty and {'start','end'}.issubset(holdout) else
                           'The retrospective 2023+ slice has no observations in this input. ')
    (reportdir/'holdout.md').write_text('# Holdout status\n\n'+header+
      retrospective_label+
      'A prospective freeze was created only after this historical research. No post-freeze data are supplied; '
      'prospective evaluation is pending. Freeze manifest: [holdout_freeze.json](../holdout_freeze.json). '
      'Only decisions strictly after the freeze date and dataset boundary can qualify. Annual refits may use '
      'earlier data if the refit rule and parameters remain frozen.\n\n'+
      table(holdout,['strategy','observations','cagr','sharpe','max_drawdown','turnover_per_year'])+'\n',encoding='utf-8')
    (reportdir/'overall.md').write_text('# Overall research report\n\n'+header+
      'Research question: does HMM information add meaningful value beyond simpler controls? This study '
      'does not assume that it does. The existing HMM + Trend is a 50/50 blend, not a multiplicative gate.\n\n'+performance+
      '\n\nSee [attribution](hmm_attribution.md), [walk-forward](walk_forward.md), '
      '[stress periods](stress_periods.md), [holdout](holdout.md), [quality](data_quality.md), '
      '[model diagnostics](model_diagnostics.md) and [strategy comparison](strategy_comparison.md). '
      'Prior extensive strategy selection and examined test dates make the historical analysis exploratory. '
      'No real-time data, dividends, taxes, impact or live trading are implemented.\n',encoding='utf-8')
    fig, axes=plt.subplots(1,3,figsize=(13,3.8),sharey=True)
    for ax,(name,g) in zip(axes,sims.groupby('control',sort=False)):
        ax.hist(g.sharpe, bins=22, color='#4885b8',alpha=.8)
        ax.axvline(real.sharpe,color='#f7a840',label='Real HMM + Trend',linewidth=2)
        ax.axvline(trend.sharpe,color='#26a69a',label='Trend',linewidth=1.5,linestyle='--')
        ax.set_title(name,fontsize=9); ax.set_xlabel('Net Sharpe'); ax.grid(alpha=.2)
    axes[0].set_ylabel('Simulations'); axes[0].legend(fontsize=7)
    fig.suptitle('Causal HMM-control distributions — simulations, not confidence intervals',fontsize=11)
    fig.tight_layout(); fig.savefig(out/'figures'/'attribution_sharpe.png',dpi=150,bbox_inches='tight');plt.close(fig)
