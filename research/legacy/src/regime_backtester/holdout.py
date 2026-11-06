"""Frozen prospective evaluation for a verified extension of the original CSV."""
from __future__ import annotations
import argparse
from copy import deepcopy
import json
from pathlib import Path
import sys
import pandas as pd
import yaml
from .config import validate_config
from .data import load_price_csv
from .experiment_tracking import config_sha256, core_source_sha256, create_run
from .pipeline import run_pipeline
from .reporting import write_results
from .research_metrics import evaluate_window
from .validation import validate_prospective_extension

ROOT=Path(__file__).resolve().parents[2]


def prospective_evaluation(freeze_path: str, original_csv: str, extended_csv: str, runs_dir: str | None = None) -> Path:
    manifest=json.loads(Path(freeze_path).read_text(encoding='utf-8'))
    config=deepcopy(manifest['frozen_config'])
    if config_sha256(config) != manifest['frozen_config_sha256']:
        raise ValueError('Frozen config hash mismatch; do not tune after freeze')
    if core_source_sha256() != manifest['source_code_sha256']:
        raise ValueError('Research source differs from frozen source; restore frozen version before evaluation')
    original,source=load_price_csv(original_csv,config['data']['date_column'],config['data']['price_column'])
    if source['sha256'] != manifest['baseline_data_sha256']:
        raise ValueError('Original data hash differs from frozen dataset')
    extended,extended_source=load_price_csv(extended_csv,config['data']['date_column'],config['data']['price_column'])
    validate_prospective_extension(original,extended,manifest)
    out=create_run(Path(runs_dir) if runs_dir else ROOT/'runs')
    config['data']['csv']=extended_csv;config['output']['directory']=str(out)
    validate_config(config)
    (out/'holdout_freeze.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
    (out/'config.yaml').write_text(yaml.safe_dump(config,sort_keys=False),encoding='utf-8')
    status={'run_id':out.name,'kind':'prospective_holdout','status':'running','original_freeze':str(Path(freeze_path).resolve()),
            'extended_source':extended_source}
    def save_status(): (out/'run_status.json').write_text(json.dumps(status,indent=2)+'\n',encoding='utf-8')
    save_status()
    try:
        result=run_pipeline(extended,config,extended_source,print)
        write_results(result,out)
        boundary=pd.Timestamp(manifest['evaluation_decision_date_strictly_after'])
        b=config['backtest']; rows=[]
        for name,run in result.runs.items():
            # Decision itself must be after the freeze date, not just its return.
            sub=run.loc[pd.to_datetime(run.decision_date)>boundary]
            if len(sub)>1:
                rows.append({'strategy':name,'decision_start':sub.decision_date.iloc[0],
                             'return_start':sub.index[0], 'return_end':sub.index[-1],
                             **evaluate_window(sub,b['annual_risk_free_rate'],b['trading_days_per_year'])})
        pd.DataFrame(rows).to_csv(out/'holdout_prospective.csv',index=False)
        status['status']='completed' if rows else 'pending_insufficient_post_freeze_returns'
        status['warning']='Model design was frozen after historical exploration; this is not a proof of future outperformance.'
        save_status()
        return out
    except Exception as e:
        status['status']='failed';status['error']=str(e);save_status();raise


def main(argv=None):
    p=argparse.ArgumentParser(description='Evaluate a verified data extension after a recorded freeze')
    p.add_argument('--freeze',required=True);p.add_argument('--original',required=True);p.add_argument('--extended',required=True)
    p.add_argument('--runs-dir')
    a=p.parse_args(argv)
    try:
        print('Holdout run:',prospective_evaluation(a.freeze,a.original,a.extended,a.runs_dir));return 0
    except (ValueError,FileNotFoundError,RuntimeError) as exc:
        print('Holdout unavailable:',exc,file=sys.stderr);return 1
if __name__=='__main__':raise SystemExit(main())
