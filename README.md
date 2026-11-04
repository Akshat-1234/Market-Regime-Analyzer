# Market Regime Research Platform

A historical NIFTY 50 latent-state research workspace. **Exploratory work in progress, not investment advice or a validated model.** The reproduced delayed baseline does not establish an incremental HMM Sharpe edge over trend. There is no untouched prospective holdout. The exact historical E7 specifications were not supplied, so E7 and several requested research phases remain incomplete.

- [Methods, actual findings and unresolved research](docs/METHODOLOGY_AND_FINDINGS.md)
- [Audit and decision log](docs/RESEARCH_DECISIONS.md)
- [Progress by phase](docs/PROGRESS.md)
- [Tests and validation](docs/TEST_AND_VALIDATION.md)
- Original notebooks, datasets, legacy code and outputs are preserved in [historical archives](historical/README.md), including the unchanged Arena project ZIP. New experiments remain under `research/`.

## Setup and dashboard

Python 3.11 and Node 20.19+ (or 22.12+) recommended. From the repository root:

```bash
python -m venv .venv
. .venv/bin/activate                # Windows: .venv\Scripts\activate
python -m pip install -r requirements-research.txt
cd frontend && npm ci && npm run build && cd ..
python -m uvicorn backend.research_api:app --host 0.0.0.0 --port 8000
```

Open the app at `http://localhost:8000`. The API serves the built frontend and the browser uses same-origin `/api` URLs. For frontend development, start `cd frontend && npm run dev -- --host 0.0.0.0` in another terminal and open port 5173; Vite proxies `/api` to port 8000. This local read-only API has no authentication; do not expose publicly. The dashboard fails closed if displayed artifacts, data, signals or analysis source do not match their recorded hashes. Reports and source artifacts are downloadable from the UI. The legacy backend and frontend are preserved in the historical archive and are not the current application.

## Reproduce

The supplied file is `research/data/nifty_index.csv`; its SHA-256 is recorded in the experiment. The archived source has been copied unchanged to `research/legacy` to make reproduction possible. Use a **new**, empty output path; no historical results are overwritten.

```bash
python research/legacy/run.py --config research/legacy/config/default.yaml \
  --csv research/data/nifty_index.csv --start 2012-01-01 --execution-delay 1 \
  --bootstrap-samples 1000 --output /tmp/nifty-reproduction
python research/analysis/characterize.py --run /tmp/nifty-reproduction \
  --output /tmp/nifty-characterization/analysis.json
python research/analysis/model_grid.py --csv research/data/nifty_index.csv \
  --output /tmp/nifty-grid
python research/analysis/forecast.py --run /tmp/nifty-reproduction \
  --output /tmp/nifty-forecast
```

Numerical libraries and optimization may produce small differences across platforms; the new baseline's exact versions, input and source snapshot are saved. `model_grid.py` runs 360 seed fits, typically several minutes. `characterize.py` verifies the probability sums and refuses to overwrite output. It describes saved OOS probabilities, not retraining. For unchanged supplied outputs, the four-section dashboard reads `research/experiments/baseline_20261104`, `characterization_20261104`, `model_grid_20261104`, and `forecast_20261104`; it does not silently swap to a newly generated run.

## Verification

```bash
python -m pytest -q tests
cd frontend && npm run build
```

See the validation report for what was actually run, skipped, and remains untested. Baseline source depends on hmmlearn's private emission-density API; the version is pinned. Do not infer production readiness from successful tests.
