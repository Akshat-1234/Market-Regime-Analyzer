# PROFNITT QUANT CLUB
## Market Regime Research & Strategy Analytics Platform

A local, historical research platform for asking a specific question: **does HMM regime information add economically and statistically meaningful value beyond simpler strategies?** It preserves the supplied NIFTY dataset and earlier baseline, runs causal walk-forward experiments, records reproducible artifacts, and serves them through a five-section dashboard. It is research software, not a live trading system or investment advice.

### Bottom line from the supplied data

The delayed 2012–2026 study does **not establish an incremental Sharpe edge**. HMM + Trend achieved Sharpe **0.287** versus **0.286** for Trend, with a paired 95% block-bootstrap difference interval of **−0.189 to +0.177**. The blend's realized maximum drawdown was **17.20%** versus **20.93%** for Trend. A lower historical drawdown is descriptive, not evidence that future drawdowns will be lower.

The main run uses **200 simulations for each of three controls**, plus 1,000 paired bootstrap samples. Its 63-session control lookback was selected after inspecting a preliminary full-history matching diagnostic; both runs are retained and the resulting selection risk is disclosed. The 2023–2026 slice has already been examined. A genuinely prospective holdout is **pending**, with eligible decisions strictly after **30 October 2026**.

**[Executive findings](reports/EXECUTIVE_SUMMARY.md)** · **[Research and methodology guide](docs/PLATFORM_GUIDE.md)** · **[Baseline audit](docs/BASELINE_AUDIT.md)** · **[Test report](docs/TEST_REPORT.md)**

---

## Independent research programme (Phases A–G)

A separate, full research programme was run on top of this platform to test the baseline claim properly: **can distinct, persistent latent regimes be discovered from unlabelled returns, and does regime information improve out-of-sample allocation beyond conventional indicators?** It is deliberately unflattering to the platform's headline result.

* **[Research report](docs/RESEARCH_REPORT.md)** — diagnosis, verified baseline, pre-registered design, five experiments, five-perspective council review, and the single most important next question.
* **[Verification report](docs/VERIFICATION.md)** — what was implemented, executed, partially executed and not executed, the defects found, and the claims this work does **not** support.
* **[Experiment register](research_outputs/study_20261030T111521Z/EXPERIMENT_REGISTER.csv)** — every experiment with its hypothesis, held-constant controls, metric, pre-declared failure criterion, result and decision.

What the programme found (all on the supplied NIFTY data, 2012–2026, delayed execution, 10 bps):

| Question | Answer |
| --- | --- |
| How many latent states? | **Four**, chosen by held-out predictive density — not by BIC, which keeps improving past six. Two states are clearly too few; the fourth is real for density but only 79 % of annual refits preserve its identity. |
| Is the shipped representation right? | **No.** `daily_return + volatility_20` beats the shipped three-feature model on held-out density (+0.485 nats/day), and *every* extra feature (downside vol, Parkinson, vol-of-vol, trend, the 7-feature set) makes it worse. |
| Do heavy tails or sticky durations help? | **No.** Gaussian-diagonal wins; Student-t estimates ν ≈ 74–100 (i.e. rejects its own tail), and sticky transitions lower held-out density. Geometric durations are nonetheless rejected (χ² = 26.5, p ≈ 7 × 10⁻⁵), so the duration structure is mis-specified but the proposed fix does not help. |
| Does regime information predict returns out of sample? | **No.** In-sample the regime block adds 1.2 pp of R² at the 20-day horizon (Wald p = 0.057); out-of-sample it adds nothing (OOS R² −0.005 to −0.027, all Diebold–Mariano p ≥ 0.13). |
| Does regime-conditioned allocation beat conventional strategies and matched controls? | **Not demonstrated, and one test is actively negative.** Regime vol-state Sharpe 0.260 vs Trend 50 0.286; against its own circularly shifted exposure path (identical marginal, identical turnover) the real path sits at the **4.5th percentile** — its timing is worse than random. Against a vol-matched observable control it sits at the 95th percentile, which is the only channel the model has. Family-wide reality check p = 0.12. |
| What is the most important next question? | Whether the positive forward return of the most stressed state (6.4 % over 20 sessions on 53 days, against 0.8 % for the calm state) is a real state-conditional premium or a small-sample artefact — because the entire negative result follows from the defensive mapping selling the highest-returning state. The pre-registered experiment is in report §10.8. |

Reproduce (≈25 minutes):

```bash
python -m regime_backtester.study --csv data/raw/nifty_index.csv \
  --start 2012-01-01 --output research_outputs --simulations 200 --seed 1701
```

Each run writes a timestamped directory (`manifest.json`, `audit/`, `discovery/`, `features/`, `emissions/`, `predictive/`, `allocation/`, `EXPERIMENT_REGISTER.csv`). The verified baseline CLI is unchanged.

---

## Start the dashboard

Prerequisites: Python **3.10+** (the included runs used 3.13.16), Node.js **20.19+**, npm, and a modern browser. Run all commands from the extracted project root. The supplied data and two completed research runs are already included; no download or rerun is needed to view them.

### macOS / Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dashboard,dev]"
cd frontend && npm ci && cd ..
python run_dashboard.py
```

### Windows PowerShell

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dashboard,dev]"
Set-Location frontend
npm ci
Set-Location ..
python run_dashboard.py
```

If PowerShell blocks activation, use `Set-ExecutionPolicy -Scope Process Bypass` for that window, or call `.\.venv\Scripts\python.exe` directly. The launcher starts:

- Dashboard: **http://localhost:5173**
- API and interactive docs: **http://localhost:8000/docs**

Stop both with Ctrl+C. To check installation without starting servers, use `python run_dashboard.py --check`. If the default ports are occupied, use `python run_dashboard.py --backend-port 8001 --frontend-port 5174`; the frontend proxy is adjusted automatically. The servers bind to all interfaces for local preview; **there is no authentication, so do not expose them to the public internet**.

Alternatively, in two terminals:

```bash
python -m uvicorn backend.app:app --host 0.0.0.0 --port 8000
# another terminal, from project root:
cd frontend && npm run dev
```

The browser calls the relative `/api` path, proxied by Vite; it never calls a browser-side localhost backend from a remote preview. The UI reads actual run artifacts. Its primary sections are **Overview, Regime Explorer, Strategy Compare, Validation, and Data Quality**. Date and strategy controls recalculate from saved daily returns; fixed full-run attribution and stress tables are explicitly labeled. CSV/report downloads and the run selector are functional. `New run` starts real computation using the bundled data and creates a new run directory.

## Generate another full research run

```bash
python -m regime_backtester.research_run --csv data/raw/nifty_index.csv \
  --start 2012-01-01 --execution-delay 1 --simulations 200 \
  --bootstrap-samples 1000 --seed 1701 --block-length 20 --control-history 63
```

For PowerShell, enter the same command on one line (or use backticks instead of backslashes). Each run gets a unique `runs/run_.../` directory with input and core-source snapshots, hashes, configuration, versions, seeds, logs, statuses, figures and reports; existing runs are not overwritten. `--control-history 0` uses all prior exposures rather than a 63-session rolling history. See [run inventory](docs/RUNS_AND_PROVENANCE.md) before comparing runs.

The old engine and strategies are retained. `python run.py --help` provides the legacy engine, including its original same-close mode; the dashboard's research command defaults to the delayed case. Explicit legacy `--output` paths must be new/empty. The original documentation is preserved as [docs/ORIGINAL_BACKTESTER_README.md](docs/ORIGINAL_BACKTESTER_README.md).

## Verify

```bash
python -m pytest -q      # 63 passed, 3 skipped; see docs/VERIFICATION.md for the skips
cd frontend
npm test
npm run build
npx playwright install chromium   # on Linux, system browser libraries may also be needed
npm run test:e2e                 # starts servers if not already running
```

An additional, slower real job-launch smoke is `python tests/manual_job_e2e.py`. The reference tests use the two included run IDs and supplied data. See [test report](docs/TEST_REPORT.md) for what was actually executed, warnings and platform limitations.

## Important assumptions

- Source: user-supplied NIFTY index prices, 17 September 2007–22 October 2026; 3,632 delayed OOS return observations from 5 January 2012. Source is not independently verified or a total-return investment product.
- A close-at-t signal is executed at the **next session's close** and earns the **following** close-to-close return. This is not next-open execution. Same-close mode is optimistic and separately preserved.
- 10 bps one-way proportional trading cost; 6.5% fixed annual cash baseline. RBI 91-day auction yields are a lagged, imperfect sensitivity proxy, not a replacement baseline. No dividends, taxes, market impact or financing frictions.
- Four HMM variants; expanding annual refits; causal filtered probabilities; 50/50 arithmetic HMM + Trend blend—not an HMM × Trend gate. States are local training-volatility ranks, not permanent economic identities.
- Controls sample only past HMM exposures, except the first initialization. Matching is approximate. Empirical simulation quantiles/fractions are **not p-values**; bootstrap intervals are paired against a daily mean control portfolio and do not correct for prior model search.
- PCA is descriptive and trained only before the first OOS signal; it is not silently added to the default HMM. Weekday gaps include holidays. Some Open prices warrant vendor verification.

## Project map

```text
backend/                 FastAPI artifact API and run launcher
frontend/                React/TypeScript/Vite/Tailwind research interface
src/regime_backtester/   Original engine plus attribution, validation and reports;
                         research extensions: emhmm, discovery, features (research block),
                         significance, predictive, allocation, study
research_outputs/        Timestamped independent research studies (see docs/RESEARCH_REPORT.md)
config/                  Frozen/default and optional PCA configurations
data/raw/                User-supplied NIFTY CSV
data/reference/          RBI-derived 91-day auction-yield proxy and attribution
results/                 Preserved original delayed and same-close results
runs/                    Two complete, immutable new research runs
reports/                 Executive findings
docs/                    Audit, methods, tests, research report, verification, provenance
tests/                   Research, API, integration and browser tests
run_dashboard.py         Cross-platform two-server launcher
```

The prior, unavailable 14-model source/configuration cannot be reconstructed exactly. Independent third-party daily data are not redistributed. No licence has been specified for the reconstructed code; choose one before public redistribution.
