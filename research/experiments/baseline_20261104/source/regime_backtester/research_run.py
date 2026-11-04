"""Run a new immutable research experiment with provenance and artifacts.

Usage: python -m regime_backtester.research_run --csv data/raw/nifty_index.csv
"""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import json
import logging
from pathlib import Path
import sys
import traceback
import uuid
import yaml

from .config import load_config
from .data import load_price_csv
from .pipeline import run_pipeline
from .reporting import write_results
from .attribution import run_attribution
from .diagnostics import data_diagnostics, model_diagnostics
from .risk_free import align_auction_yields, file_sha256
from .stress_testing import stress_analysis
from .validation import cash_sensitivity, fold_metrics, freeze_manifest, retrospective_holdout
from .research_reports import write_research_reports
from .experiment_tracking import create_run, snapshot_inputs_and_source

ROOT = Path(__file__).resolve().parents[2]


def run_research(csv: str, *, start: str = '2012-01-01', delay: int = 1, simulations: int = 200,
                 bootstrap_samples: int = 1000, seed: int = 1701, block_length: int = 20, control_history: int | None = 63,
                 config_path: str | None = None, runs_dir: Path | None = None) -> Path:
    if simulations < 2 or bootstrap_samples < 2 or block_length < 1 or (control_history is not None and control_history < 2):
        raise ValueError('Need simulations/bootstrap >= 2, positive block length, and control history >= 2 or 0 for full history')
    out = create_run(runs_dir or ROOT/'runs')
    (out/'logs').mkdir()
    logfile = out/'logs'/'research.log'
    logger = logging.getLogger(f'research-{out.name}'); logger.setLevel(logging.INFO); logger.propagate=False
    formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
    fh=logging.FileHandler(logfile, encoding='utf-8');fh.setFormatter(formatter);logger.addHandler(fh)
    sh=logging.StreamHandler(sys.stdout);sh.setFormatter(formatter);logger.addHandler(sh)
    status={'run_id':out.name,'status':'running','created_utc':datetime.now(timezone.utc).isoformat()}
    def write_status(): (out/'run_status.json').write_text(json.dumps(status,indent=2)+'\n',encoding='utf-8')
    write_status()
    try:
        cfg=load_config(config_path or ROOT/'config'/'default.yaml',
            {'data':{'csv':csv}, 'walkforward':{'start_date':start},
             'backtest':{'execution_delay_sessions':delay}, 'bootstrap':{'samples':bootstrap_samples},
             'output':{'directory':str(out)}})
        data,source=load_price_csv(csv,cfg['data']['date_column'],cfg['data']['price_column'])
        if cfg['walkforward']['end_date']:
            data=data.loc[:cfg['walkforward']['end_date']].copy()
        snapshot_inputs_and_source(out,csv,ROOT/'data/reference/rbi_tbill_91_yields.csv')
        (out/'config.yaml').write_text(yaml.safe_dump(cfg,sort_keys=False),encoding='utf-8')
        manifest={'input':source,'input_snapshot':'inputs/prices.csv','core_source_snapshot':'source/regime_backtester/', 'observations':len(data),'first_date':str(data.index[0].date()),
                  'last_date':str(data.index[-1].date()),'source_note':'User-supplied index prices, not a total-return trading instrument.'}
        (out/'data_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
        logger.info('Data loaded: %s rows, %s through %s; refitting annually',len(data),data.index[0].date(),data.index[-1].date())
        result=run_pipeline(data,cfg,source,logger.info)
        write_results(result,out)
        logger.info('Walk-forward complete; building folds, stress and holdout diagnostics')
        folds,aggregate=fold_metrics(result)
        folds.to_csv(out/'fold_metrics.csv',index=False);aggregate.to_csv(out/'fold_aggregate.csv',index=False)
        stress=stress_analysis(result.runs,cfg);stress.to_csv(out/'stress_periods.csv',index=False)
        retrospective=retrospective_holdout(result.runs,cfg);retrospective.to_csv(out/'holdout_retrospective.csv',index=False)
        freeze=freeze_manifest(cfg,source['sha256'],str(data.index[-1].date()),result.metadata['core_source_sha256'])
        (out/'holdout_freeze.json').write_text(json.dumps(freeze,indent=2)+'\n',encoding='utf-8')
        raw=__import__('pandas').read_csv(csv)
        if cfg['walkforward']['end_date']:
            raw=raw.loc[__import__('pandas').to_datetime(raw[cfg['data']['date_column']],errors='coerce') <= cfg['walkforward']['end_date']]
        if cfg['data']['date_column'] != 'Date':
            raw=raw.rename(columns={cfg['data']['date_column']:'Date'})
        quality=data_diagnostics(raw,data,result.walkforward.signals.index[0])
        (out/'data_quality_summary.json').write_text(json.dumps(quality['summary'],indent=2)+'\n',encoding='utf-8')
        quality_files={'annual':'data_quality_annual','flags':'data_quality_flags',
                       'weekday_candidates':'data_quality_weekday_candidates','pca_variance':'pca_variance',
                       'pca_loadings':'pca_loadings','feature_correlations':'feature_correlations',
                       'feature_distributions':'feature_distributions'}
        for key,name in quality_files.items():quality[key].to_csv(out/f'{name}.csv',index=False)
        model=model_diagnostics(result)
        for name,frame in model.items():frame.to_csv(out/f'{name}.csv',index=False)
        rates_path=ROOT/'data/reference/rbi_tbill_91_yields.csv'
        warnings=[]
        try:
            rates,alignment=align_auction_yields(rates_path,result.walkforward.signals.index,max_age_days=31)
            alignment.to_csv(out/'rbi_aligned_rates.csv',index=False)
            stale=int((alignment.age_days>14).sum())
            warnings.append(f'RBI proxy: {stale} signal dates have a yield older than 14 calendar days; maximum age {int(alignment.age_days.max())} days. Auction yields are not realized cash returns.')
            manifest['cash_rate_reference']={'path':str(rates_path),'sha256':file_sha256(rates_path),
                'source':'RBI (via Data Bank), compiled by Measure of India; vintage 2026-10-08',
                'url':'https://measure.thisindianlife.today/data/rates-tbill-91/',
                'strict_prior_auction':True,'max_age_allowed_days':31,'max_age_actual_days':int(alignment.age_days.max()),
                'dates_older_than_14_days':stale}
        except (FileNotFoundError,ValueError) as exc:
            rates=None;warnings.append(f'Historical cash-rate proxy unavailable: {exc}')
            logger.warning(warnings[-1])
        cash=cash_sensitivity(result,data,rates);cash.to_csv(out/'cash_sensitivity.csv',index=False)
        (out/'data_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
        logger.info('Running %s simulations per control, prior-only history %s; seed %s',simulations,control_history,seed)
        attr=run_attribution(result,data,simulations=simulations,seed=seed,block_length=block_length,history_window=control_history)
        attr.metrics.to_csv(out/'attribution.csv',index=False)
        attr.simulations.to_csv(out/'attribution_simulations.csv',index=False)
        attr.bootstrap.to_csv(out/'attribution_bootstrap.csv',index=False)
        attr.periods.to_csv(out/'attribution_periods.csv',index=False)
        attr.control_daily.to_csv(out/'attribution_control_daily_means.csv',index_label='Date')
        write_research_reports(out,result,attr,folds,aggregate,stress,quality,model,retrospective,cash,out.name,control_history)
        status.update({'status':'completed','completed_utc':datetime.now(timezone.utc).isoformat(),
                       'simulation_count_per_control':simulations,'attribution_seed':seed,
                       'attribution_block_length':block_length,'control_history_sessions':control_history,'bootstrap_samples':bootstrap_samples,
                       'warnings':warnings,'source_code_sha256':result.metadata['core_source_sha256'],
                       'data_sha256':source['sha256']})
        write_status()
        logger.info('Run completed: %s',out)
        return out
    except Exception as exc:
        status.update({'status':'failed','error':str(exc),'finished_utc':datetime.now(timezone.utc).isoformat()})
        write_status();logger.error('Research run failed\n%s',traceback.format_exc());raise
    finally:
        for handler in list(logger.handlers):
            handler.flush();handler.close();logger.removeHandler(handler)


def main(argv=None) -> int:
    p=argparse.ArgumentParser(description='Create an immutable HMM research run')
    p.add_argument('--csv',default=str(ROOT/'data/raw/nifty_index.csv'))
    p.add_argument('--start',default='2012-01-01')
    p.add_argument('--execution-delay',type=int,choices=[0,1],default=1)
    p.add_argument('--simulations',type=int,default=200)
    p.add_argument('--bootstrap-samples',type=int,default=1000)
    p.add_argument('--seed',type=int,default=1701)
    p.add_argument('--block-length',type=int,default=20)
    p.add_argument('--control-history',type=int,default=63,help='past-only control lookback in sessions; 0 uses all prior history')
    p.add_argument('--config')
    p.add_argument('--runs-dir',type=Path)
    args=p.parse_args(argv)
    try:
        run_research(args.csv,start=args.start,delay=args.execution_delay,simulations=args.simulations,
                     bootstrap_samples=args.bootstrap_samples,seed=args.seed,block_length=args.block_length,
                     control_history=args.control_history if args.control_history != 0 else None, config_path=args.config,runs_dir=args.runs_dir)
        return 0
    except (OSError,ValueError,RuntimeError) as exc:
        print(f'Research run failed: {exc}',file=sys.stderr);return 1

if __name__=='__main__': raise SystemExit(main())
