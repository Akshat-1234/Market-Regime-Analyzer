"""Optional real API-launched research smoke; run explicitly, not as a fast pytest test."""
from __future__ import annotations
import argparse
import os
from pathlib import Path
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--runs-dir',help='retain smoke artifacts here; otherwise use a temporary directory')
    args=parser.parse_args()
    temp=None
    if args.runs_dir: out=Path(args.runs_dir).resolve();out.mkdir(parents=True,exist_ok=True)
    else: temp=tempfile.TemporaryDirectory(prefix='regime-job-smoke-');out=Path(temp.name)
    os.environ['REGIME_RUNS_DIR']=str(out)
    from fastapi.testclient import TestClient
    import backend.app as api
    client=TestClient(api.app)
    response=client.post('/api/job',json={'start':'2026-01-01','execution_delay':1,'simulations':2,
        'bootstrap_samples':20,'seed':123,'block_length':20,'control_history':63})
    assert response.status_code==202,response.text
    assert client.get('/api/job').json()['status']=='running'
    code=api._job['process'].wait(timeout=180)
    job=client.get('/api/job').json()
    assert code==0 and job['status']=='completed',job
    runs=client.get('/api/runs').json()['runs']; run=next(r for r in runs if r['status']=='completed')
    overview=client.get(f"/api/runs/{run['run_id']}/overview")
    attr=client.get(f"/api/runs/{run['run_id']}/attribution")
    assert overview.status_code==200,overview.text
    assert attr.status_code==200 and len(attr.json()['simulations'])==6,attr.text
    print(f"PASS: real API-launched job {run['run_id']}; {len(attr.json()['simulations'])} control paths; outputs: {out}")
    if temp: temp.cleanup()

if __name__=='__main__':main()
