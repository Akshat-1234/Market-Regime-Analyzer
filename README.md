# Market Regime Research Platform

A completed historical NIFTY 50 research workspace for inspecting preserved latent-state, model-discovery, strategy and forecasting results. **This is exploratory retrospective research, not investment advice or a validated trading model.** The historical baseline does not establish an incremental HMM Sharpe edge over trend, and the five-state discovery experiment does not establish five stable economic regimes. There is no untouched prospective holdout. The exact historical E7 specifications were not supplied and are not claimed as delivered evidence.

- [Methods, actual findings and unresolved evidence](docs/METHODOLOGY_AND_FINDINGS.md)
- [Nested discovery results](docs/TASK4_RESULTS.md), [frozen protocol](docs/TASK4_PROTOCOL.md) and [analysis contracts](docs/TASK4_ANALYSIS.md) (internal experiment identifier: Task 4)
- [Audit and decision log](docs/RESEARCH_DECISIONS.md)
- [Delivery progress](docs/PROGRESS.md)
- [Tests and validation](docs/TEST_AND_VALIDATION.md)
- Original notebooks, datasets, legacy code and outputs are preserved in [historical archives](historical/README.md), including the unchanged Arena project ZIP. New experiments remain under `research/`.

## Dashboard sections

1. **Overview** — separates historical baseline characterization, five-state discovery, historical strategy evaluation and forecasting evaluation; summarizes what the evidence does and does not support.
2. **Historical Baseline Regimes** — explores the separate three-state RVD baseline using return, 20-day volatility and 252-day drawdown. Local state ranks 0–2 are recalibrated across 15 annual refits and are not permanent economic identities. Includes the dated assignment timeline and empirical within-year transitions.
3. **Regime Discovery & Model Stability** — presents the separate five-state discovery experiment using close-only daily return and 20-day volatility across 14 outer folds. Covers model selection, selection margins, seed sensitivity, state occupancy, temporal alignment and reproducibility. K=5 selection is not evidence of five economically meaningful or stable regimes.
4. **Historical Strategy Evaluation** — compares four saved account-equity curves and all nine baseline strategy rows, execution timing, costs and exploratory paired Sharpe-difference intervals. No discovery-model allocation or backtest is implied.
5. **Predictive Evaluation & Validation** — presents the separate retrospective forecasting study, all eight simultaneous MSE-improvement intervals, feature definitions, causal timing, provenance, source artifacts and limitations.

Baseline and discovery requests fail independently. The interface displays only saved observations and verified artifacts; chart sampling is disclosed, and no observations are interpolated or substituted.

## Setup and dashboard

Python 3.11 and Node 20.19+ (or 22.12+) are recommended. From the repository root:

```bash
python -m venv .venv
. .venv/bin/activate                # Windows PowerShell: .venv\Scripts\Activate.ps1
python -m pip install -r requirements-research.txt
cd frontend && npm ci && npm run build && cd ..
python -m uvicorn backend.research_api:app --host 0.0.0.0 --port 8000
```

Open the app at `http://localhost:8000`. The API serves the built frontend and the browser uses same-origin `/api` URLs. For frontend development, run `cd frontend && npm run dev -- --host 0.0.0.0` in another terminal and open port 5173; Vite proxies `/api` to port 8000. This local read-only API has no authentication; do not expose it publicly.

The explicit production backend launch commands are:

**Unix / macOS**

```bash
.venv/bin/python -m uvicorn backend.research_api:app --host 0.0.0.0 --port 8000
```

**Windows PowerShell**

```powershell
.venv\Scripts\python.exe -m uvicorn backend.research_api:app --host 0.0.0.0 --port 8000
```

The dashboard fails closed if displayed artifacts, data, signals or analysis source do not match their recorded hashes. Reports and explicitly listed source artifacts are downloadable; there is no project-ZIP control or endpoint. The legacy backend and frontend are preserved in the historical archive and are not the current application.

## Existing experiments and reproduction records

The supplied file is `research/data/nifty_index.csv`; its SHA-256 is recorded in the experiments. The archived source is copied unchanged to `research/legacy` so the preserved work can be inspected or independently reproduced. These commands are reproduction instructions, not part of dashboard startup. Use a **new**, empty output path; no historical results should be overwritten.

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

Numerical libraries and optimization may produce small differences across platforms; exact versions, inputs and source snapshots are saved. `model_grid.py` represents 360 seed fits. `characterize.py` describes saved OOS probabilities and refuses to overwrite output. The dashboard does not silently substitute a newly generated run:

- `baseline_20261104` and `characterization_20261104` contain the historical three-state RVD baseline and its characterization.
- `model_grid_20261104` and `forecast_20261104` contain separate exploratory model-grid and predictive evaluations.
- `task4_v1_0_0_recovery1` and `task4_v1_0_0_analysis` contain the separately frozen five-state discovery experiment and derived analysis. The dashboard verifies both inventories before serving compact records; it does not rerun the research.

## Testing

Run the existing software checks from the repository root after setup:

```bash
python -m pytest -q tests
cd frontend && npm run build
```

See [the validation report](docs/TEST_AND_VALIDATION.md) for the checks actually executed, exact results and remaining presentation limitations. Successful software tests do not establish stable economic regimes, forecasting value, allocation value, a trading edge, prospective validity or production readiness. Baseline source depends on hmmlearn's private emission-density API; the version is pinned.
