"""Run directories and frozen-configuration hashes; never overwrite by default."""
from __future__ import annotations
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import uuid
import shutil


def create_run(base_dir: Path) -> Path:
    base_dir.mkdir(parents=True, exist_ok=True)
    for _ in range(5):
        name='run_'+datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')+'_'+uuid.uuid4().hex[:6]
        path=base_dir/name
        try:
            path.mkdir(exist_ok=False)
            return path
        except FileExistsError:
            continue
    raise RuntimeError('Unable to reserve a unique run directory')


def frozen_config(config: dict) -> dict:
    x=deepcopy(config)
    x['data']['csv']='<data-input>'
    x['output']['directory']='<run-output>'
    return x


def config_sha256(config: dict) -> str:
    return hashlib.sha256(json.dumps(frozen_config(config),sort_keys=True,separators=(',',':')).encode()).hexdigest()


def core_source_sha256() -> str:
    h=hashlib.sha256()
    for p in sorted(Path(__file__).resolve().parent.glob('*.py')):
        h.update(p.name.encode('utf-8')+b'\0');h.update(p.read_bytes())
    return h.hexdigest()


def snapshot_inputs_and_source(out: Path, input_path: str | Path | None, reference_path: str | Path | None = None) -> None:
    """Save byte-identical input and core source snapshots for reproducibility."""
    inputs=out/'inputs'; inputs.mkdir(parents=True,exist_ok=True)
    if input_path is not None:
        shutil.copy2(input_path, inputs/'prices.csv')
    if reference_path is not None and Path(reference_path).is_file():
        shutil.copy2(reference_path, inputs/'rbi_tbill_91_yields.csv')
    dest=out/'source'/'regime_backtester';dest.mkdir(parents=True,exist_ok=True)
    for p in sorted(Path(__file__).resolve().parent.glob('*.py')):
        shutil.copy2(p,dest/p.name)
