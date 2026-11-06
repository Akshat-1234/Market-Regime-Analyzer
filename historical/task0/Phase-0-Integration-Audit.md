# Phase 0 Integration Audit — Complete Supporting Package

> Combined Markdown version of every text document and inventory from the original ZIP, for upload to interfaces that do not accept ZIP files.

---


# SOURCE FILE: `phase0-integration-audit/README.md`

# Phase 0 — read-only integration audit

Prepared outside the active repository; no repository code or tracked files changed. The five proposed documents are in `docs/`; the full five-perspective Council review is `docs/COUNCIL_GATE_0.md`. Complete tracked inventories at the two verified tips are in `inventory/` (107 f10 files; 278 1c files). `PHASE_0_AUDIT.md` is a single combined copy for convenient review.

- f10: `9bb7f92d5785462462971d0479595c1d4166868c`
- 1c: `c46541e9ab8611330489a920c46cdb00342931d5`
- Merge base: `f1602c5c95c14e4bd7795433ca6ecfd3d98794d6`

This is an audit and proposal only, not a claim of new tests or completed integration. No historical experiment was rerun. Stop for Gate 0 approval and the separate-branch/session decision.


# SOURCE FILE: `phase0-integration-audit/PHASE_0_AUDIT.md`

# Phase 0: Read-only integration audit

The five proposed documents and simulated Council review follow. The complete inventories and command log are provided separately. No active repository files were changed.


---

# Proposed integration plan — Council Gate 0

**Status: proposal only.** No active repository files changed; no new experiments, tests or builds executed for this audit. Immutable references: f10 `9bb7f92d5785462462971d0479595c1d4166868c`, 1c `c46541e9ab8611330489a920c46cdb00342931d5`, merge base `f1602c5c95c14e4bd7795433ca6ecfd3d98794d6`. GitHub compare: 1c ahead by 2 and behind by 12 relative to f10. Inventories list 107 and 278 tracked files respectively. f10 checkout is shallow at 31902b7; remote API supplied older history. Both have the exact same older Arena ZIP (`bdf7b9136f8fd9b52dc6eedd34fd916c74f8baaaccc8815b3bd170dfc948d4b1`); the ZIP does not contain 1c's newer research code, reports or study outputs.

## Gate and branch restriction

The execution environment locks work to `arena/f10f6e2d-market-regime-analyzer` and prohibits creating or switching branches. The requested separate integration branch cannot be created in this session, even after approval. Options: (A) continue integration on the fixed branch while preserving the exact current f10 snapshot/commit and the untouched 1c branch; the f10 branch name would move, though its old commit remains reachable; or (B) the user starts a new Arena session configured with a separate integration branch. No branch will be created, renamed, or pushed by this audit. If retaining f10's branch pointer unchanged is essential, choose B. No wholesale merge.

## Sequence after an appropriate branch/session decision

1. **Foundation, preserve first.** Verify f10 archive hashes, save a manifest of original 1c commit, path-level inventories and immutable history; preserve 1c study directories including superseded studies and reports under `historical/1c/` or immutable source snapshot storage. Copy selectively, avoid accidental Git LFS/large data or duplicated active implementations. Never overwrite existing f10 `research/experiments/*`. Record exact source commits, source paths, content hashes, transformations and decisions. Keep source snapshots read-only.
2. **Dependencies and core.** Establish one `research/data/nifty_index.csv` input (current f10 attachment), with sha verification. Keep legacy f10 baseline engine/config intact for exact reproduction. Introduce 1c research modules behind a separate versioned package/adapter, not a mixed directory that may shadow the legacy engine. Unify immutable config/provenance schema without changing recorded configs. Initially route read-only artifact access; API may expose multiple schema versions.
3. **Methodology verification before model claims.** Add failing regression tests for target-maturity leakage, dimensionality-comparable scoring, global-selection leakage, label alignment, nonconvergence policy, matched controls, duration censoring and precise metric definitions. Resolve with a reviewed protocol, not a silent backport. Preserve historical results with defect labels. Do not assert the RV-vs-RVD delta supports a feature choice or that selected 1c OOS is independent until those findings are resolved.
4. **Dashboard.** Treat 1c TypeScript dashboard as candidate, not accepted by appearance. Its API consumes archived `runs/run_*` attribution-schema artifacts, not the newer `research_outputs/study_*`, and clean 1c checkout contains no `runs/` or raw input. Prototype an adapter for f10 baseline + 1c historical studies, carrying source/validity/status; independently run unit/build/browser checks. Keep f10 characterization as typed measured data. Disable 1c's write-capable job endpoint/button until execution, isolation, resource limits, provenance and access assumptions are accepted. Never present an older invalid hash freeze as valid prospective validation.
5. **Phase 2 only after Gate 1.** Reproduce both baseline and research studies from their exact source snapshots and locks in isolated workspaces; compare every artifact under declared tolerances, distinguishing exact historical reproduction from corrected reanalysis. If historical code contains defects, reproduce unchanged only in isolation, flag outputs, then run corrected code as a separate ID. Gate 2 blocks research claims for unexplained discrepancies.
6. **E7 only after approved clarification and Gate 2.** The 1c report section 10.8 supplies four candidates and a sign criterion, but does not resolve rank pooling for K=3/5, bootstrap units, sample weighting, and precise fit/config for all candidates. Record these gaps before using the data again. Do not change a criterion post hoc. Distinguish exploratory historical follow-up from a newly frozen truly prospective test.
7. **Finish product / release.** Complete five user-facing sections only after experiment contracts and UI are verified. No uploads/live trading. Final documentation, E2E and public security review remain later gates.

## Provisional decisions

- f10's direct experiment hash checks and characterization are retained as behavior, but its monolithic API, fixed paths, and standalone scripts are not the final abstraction.
- 1c custom EM is a candidate with explicit numerical/parity testing; no assumed superiority over `hmmlearn`. Fail-closed versus nonconverged fallback must be explicit.
- 1c's sequence K-on-RVD then features-at-fixed-K is not joint K-feature selection; per-fold causal selection must be designed before new OOS claims. Likelihoods of different-dimensional observations are not directly comparable.
- Maintain historical baseline result as retrospective: HMM + Trend vs Trend Sharpe difference +0.0014 with 95% interval approximately [-0.1887, 0.1774]. Do not imply superiority or prospective validation.

## First executable action after user decision

On the permitted branch, create only a component-provenance manifest and read-only characterization/forecast contract tests against preserved artifacts; pass untouched historical-hash checks and reproduce the existing f10 suite before touching code. This is conditional on a branch/session decision and explicit Gate 0 approval.


---

# Component migration map — proposed, not executed

Paths prefixed `1c:` are relative to `market-regime-platform/` at c46541e; `f10:` are relative to f10 root at 9bb7f92. Destinations below are provisional logical paths; historical copies remain immutable. Classifications apply to active components, not deletion of research records. Every selection is conditional on tests in `INTEGRATION_ACCEPTANCE_TESTS.md`.

| Component / classification | Source → proposed destination | Dependencies and interface | Conflict / verification |
|---|---|---|---|
| Repository structure — **Keep from f10** | `f10:historical/`, `research/`, `docs/` → same | Git commit, archive checksums | Original 1c code not inside the shared old Arena ZIP; archive exact 1c source and outputs separately. Verify all file hashes and both source SHAs. |
| NIFTY canonical dataset — **Keep from f10** | `f10:research/data/nifty_index.csv` → same | CSV Date/Open/High/Low/Close, SHA ea6d… | 1c `data/raw/` contains only README/.gitkeep; 1c root CSV is LF hash cf384… but parsed rows match. No silent line-ending canonicalization or vendor-quality claim. Check file SHA, rows, dates, OHLC and provenance/licence. |
| Original baseline — **Keep from f10** | `f10:research/legacy/{run.py,config/,src/regime_backtester/}` → `research/legacy/` | hmmlearn, pandas, scipy, sklearn, YAML | Keep byte-for-byte source and f10 `baseline_20261104/source` snapshot. Baseline timing/cost/signal comparison against both artifacts and historical output. |
| f10 experiments — **Keep from f10** | `f10:research/experiments/{baseline_20261104,characterization_20261104,forecast_20261104,model_grid_20261104}` → same | manifest, input/source/signal snapshots | Preserve old config/results and statuses. Existing code uses hard-coded IDs/paths; adapter should not modify artifacts. Verify manifest and as-of timestamp semantics. |
| Historical 1c studies — **Archive** | `1c:research_outputs/study_20261030T{102052,104848,111521}Z/` + `LATEST` → `historical/1c/studies/` | Each run manifest/register/CSV | Preserve superseded D3/D6 results with defect flags; no silent current-results promotion. Verify full manifest and report-to-artifact reconciliation. |
| Historical 1c reports — **Archive** | `1c:docs/{RESEARCH_REPORT,VERIFICATION,BASELINE_AUDIT,DATA,METHODOLOGY,RUNS_AND_PROVENANCE,TEST_REPORT,PLATFORM_GUIDE}.md`, `reports/` → `historical/1c/docs/` | Original paths, source SHA | Report may assert invalid density/forecast claims or absent files. Keep unmodified, add prominent overlay/cross-reference; do not edit originals. |
| Research feature engineering — **Combine** | `1c:src/regime_backtester/features.py`, `f10:research/legacy/src/regime_backtester/features.py` → versioned `research/engine/features.py` adapter | causal trailing OHLC features, pandas | Preserve baseline definitions and warm-up; keep diagnostic-only OHLC separate and vendor warning. Compare equal features, prefix mutation, missing rows. |
| Custom EM / inference — **Migrate from 1c** (conditional) | `1c:src/regime_backtester/emhmm.py` → `research/engine/emhmm.py` | numpy/scipy/sklearn KMeans; input ndarray, `HMMFit.filter`, output probabilities/log density/final alpha | Do not replace f10 baseline. Full/diag Gaussian and Student-t remain candidates. Test numerical parity to independent likelihood/filter, posterior normalization, input/seed/convergence/rejection, Student-t scale updates, and future mutation; document failed fits. |
| Discovery, seeds, state alignment — **Combine** | `1c:src/regime_backtester/discovery.py`, `f10:research/analysis/model_grid.py` → `research/engine/discovery.py` and `research/experiments/...` | `Spec`, `FoldFit`, scaling, filtered test probabilities, train-window state vols, Hungarian matching | 1c global post-hoc selection across future folds and two-stage K/feature selection; no comparable dimensional joint scores. f10 grid uses raw-space Jacobian but rightly avoids cross-dimensional ranking. Fix using a pre-agreed common predictive target and nested selection. Check double-reordered `FoldFit.occupancy` and convergence fallback. Do not overwrite saved grids. |
| Student-t/sticky emission experiments — **Migrate from 1c** only as historical reproducibility candidates | `1c:emhmm.py`, `study.py:study_emissions` → versioned engine + experiment runner | Student-t scale/dof, sticky transition prior | Preserve tests and `emissions/` outputs. Current Student-t update divides weighted covariance by sum(gamma*u); verify against a trusted reference before interpreting dof or comparative fit. Sticky != explicit duration model. |
| Characterization — **Combine** | `f10:research/analysis/characterize.py`, `1c:predictive.py` state summaries → `research/engine/characterization.py` | as-of filtered posteriors, features, fold identity, transition matrices | Replace hard-coded 3 columns/model-specific inputs with K-aware schemas; keep weighted descriptions, entropy, refit-censored durations, separate forward outcomes and OHLC caveats. Compare old output exactly before adding features; test permutations/censoring/rare flags. |
| Forward targets and forecasting — **Rewrite** (retain originals archived) | `f10:research/analysis/forecast.py`, `1c:src/regime_backtester/predictive.py` → `research/engine/predictive.py` | typed target with outcome end-date, purged expanding fits, Ridge/HAC, probability/observable inputs | 1c `expanding_oos` trains on `slice(0,begin)` without purging outcomes crossing the test boundary; f10 explicitly purges. Preserve original R² labels/baselines; test future price mutation, label maturity, window boundaries, date alignment. Fwd min-from-entry is not peak-to-trough maximum drawdown. |
| Backtest execution & strategies — **Keep from f10** with **Combine** interfaces | `f10:research/legacy/src/regime_backtester/{execution,strategies,metrics}.py`, `1c:src/regime_backtester/allocation.py` → versioned execution/strategy adapters | self-financing simulator; signal t, execution t+1 close, return t+2; fixed cash/cost | Compare exact cash accrual, turnover, benchmark dates and missing days. Keep arithmetic blend distinct from gates; test entry/exit and no lookahead. |
| Allocation and controls — **Migrate from 1c** with conditions | `1c:src/regime_backtester/{allocation,significance,attribution}.py` → `research/engine/{allocation,statistics,controls}.py` | HMM signals/exposures, prices, seeds, stationary bootstrap | Circular phase shift is retrospective null not causal strategy; Markov/vol controls not guaranteed matching. 1c `median_exposure_ks` uses `np.mean`. Verify return-vs-Sharpe statistic, long-run variance, causality, matching quality, bootstrap uncertainty and corrected family. Retain fixed 6.5% assumptions. |
| Orchestration & provenance — **Combine** | `1c:study.py`, `experiment_tracking.py`, `f10:research/experiments/artifact_manifest.json` and CLI scripts → `research/runner/`, `research/experiments/` | YAML input + immutable manifest, exact code/data/dependency hashes | 1c research `manifest.json` records dataset/config/versions but not full content-addressed source snapshot; LATEST is mutable pointer. Validate no collisions/overwrite, exact config, source snapshots, subprocess isolation and failure statuses. |
| Prospective freeze — **Archive / rewrite** | `1c:holdout.py`, archived `holdout_freeze.json` → historical snapshot plus new versioned checker | source/config/data checksum and genuinely future observations | Existing freeze hash differs from current source and observation ends 2026-10-22. Expose as invalid/pending, never mutate old freeze. Tests for source, prefix, date and revised-data refusal. |
| API — **Combine** | `1c:backend/app.py`, `f10:backend/research_api.py` → `backend/app.py`, `backend/contracts/` | FastAPI, typed JSON, read-only run/artifact IDs | 1c `/api/runs/...` expects runs/attribution; f10 `/api/research` is a fixed combined schema; 1c study files lack same artifacts. Versioned adapter; fail closed on missing provenance, missing files, NaN, path traversal. Job POST disabled initially. |
| 1c dashboard — **Migrate from 1c** (candidate, not approved final) | `1c:frontend/src/{App.tsx,pages,components,types,api}.tsx` → `frontend/` | TS, React, router, recharts, API contracts, npm lock | Five-page navigation and interactions are richer; current source only reads older `runs` not 1c research_outputs, tests were not run in 1c environment. UI assumes source fit rejection and some state counts; freeze display must validate hash. Unit/build/real-browser/screenshot/data trace tests. |
| f10 dashboard — **Keep from f10** until replacement passes tests | `f10:frontend/src/{App.jsx,main.jsx,research.css}` → retained during migration | `/api/research` and fixed artifacts | Do not run two conflicting active apps indefinitely. Preserve as fallback/history; only archive after feature parity and numeric traceability demonstrated. |
| f10 artifact API — **Keep from f10** as compatibility layer | `f10:backend/research_api.py` → temporary compatibility router | SHA manifest, static frontend, no auth | Ensure current `/api/research`, `/api/artifacts/*`, and port 8000 still work. Per-run integrity for all displayed/downloaded files; avoid catch-all masking API errors. |
| 1c root legacy duplicate app — **Archive** | `1c:backend/`, `1c:frontend/`, root notebooks/CSVs → source SHA/old archive | Git original, exact path inventory | This is not the newer 1c `market-regime-platform/frontend`. f10 already archived original 31902b7; confirm byte differences before treating as duplicate. |
| 1c synthetic and independent aggregate examples — **Archive** | `1c:examples/synthetic_run/`, `validation/independent_nifty/` → `historical/1c/` | metadata/source-kind | Clearly SYNTHETIC or aggregate-only; independent source lacks redistributed data/licence. Never combine into historical NIFTY results. |
| Tests / CI — **Combine** | `f10:tests/`, `1c:tests/`, `1c:frontend/tests`, `frontend/e2e`, `.github/workflows/tests.yml` → active `tests/`, `frontend/tests/`, CI | pytest, httpx, Vitest, Playwright, pinned Node/Python | 1c CI is Python-only and dataset/artifacts ignored. Include real fixtures, no missing-data false passes, browser proxy and CSV checks. 1c historical test counts not fresh. |
| Demo/unsafe scope — **Reject** | general OHLC upload, live brokerage, unfrozen new model families | N/A | User explicitly deferred; exclude until separate approved hypothesis and safety design. |


---

# Architecture proposal — conditional

## Intended active repository

```text
backend/                       FastAPI read-only artifact service, versioned contracts
frontend/                      one React/TS client after parity verification
research/
  data/nifty_index.csv         canonical user-supplied dataset (not a vendor guarantee)
  engine/                      causal features, typed model and inference adapters
  runner/                      immutable configurations and reproducible job CLI
  legacy/                      f10 historical baseline engine (unchanged)
  experiments/                 immutable run-specific artifacts and source snapshots
historical/                    exact source/outputs from both branches, manifests
config/                        validated, versioned experiment definitions
tests/                         research, API, integration, statistics, fixtures
frontend/tests/, frontend/e2e/  unit and browser tests
docs/                          decisions, risks, experiment register, validation history
```

This is not permission to move or rewrite files in Phase 0. Namespaces must prevent mixing the legacy `regime_backtester` with 1c's identically named package. Keep f10 baseline implementation immutable; a separate package `research_engine` and explicit adapters is safer than overwriting imports or silently altering historic source hashes.

## Contracts

- Data service: canonical hash `ea6d…`, input provenance, indexed strictly increasing dates, quality report and feature warmup. Date t uses only OHLC available by close t; Open diagnostics flagged. Alternate datasets require a separately approved hypothesis.
- Model input: typed `ModelSpec` (feature names/order, K, emission, covariance, scaler, fit algorithm, seeds, train range), `FoldSchedule`, and versioned fit diagnostics. Fit sees only training data. `filter(test, previous_alpha)` returns `P(S_t|X_≤t)`, per-step conditional log density in declared units, final alpha; label ordering is explicit and mapping stored. Never expose full-sample smoothed probabilities as decision signals. Characterization takes arbitrary K and a fold identity.
- Experiment contract: distinct immutable ID, source commit + script hash, data hash, config and command, dependency versions, UTC timestamp, train/signal/execution/evaluation boundaries, selected/rejected fits, benchmark, costs, cash, seed, statistical family and status. Atomically write new run directory; preserve prior immutable results; a manifest with per-file hashes identifies every UI number. A `LATEST` pointer can be mutable, not the results themselves. Comparisons across different schemas use adapters and retain original attribution; absent values are missing, not zero or synthetic.
- API contract: `GET /api/experiments`, `/api/experiments/{id}`, `/states`, `/timeline`, `/strategies`, `/forecasts`, `/validation`, `/data-quality`, `/artifacts/{allowlisted_name}`. Include experiment ID, artifact hash, units, period, timing, analysis mode and methodological validity status in every response. 404 for missing; 409/422 for mismatched schema; 503 for integrity failure. Plan a compatibility adapter for f10's `/api/research` and 1c's `/api/runs/*` until callers migrate. No browser localhost calls; same-origin API/static frontend for port 8000 or Vite reverse proxy. Public-facing auth is not assumed; local-only security posture and no automatic arbitrary jobs.
- UI contract: one owner/renderer per metric; semantic units, title, source link and whether training, OOS, retrospective or prospective. Do not interpret state IDs as fixed categories. Hide absent experiments and invalid statistical claims, not backfill from mocks. Five candidate views (overview, regime, strategy, validation/controls, data/provenance); responsive keyboard-accessible, no misleading hard-coded test counts.

## Method selection and missing information

Both implementations offer useful patterns, but neither is accepted wholesale. 1c forecast training labels and cross-dimensional scores need repair; f10 uses K=3-specific inputs and only a fixed baseline. For state/feature selection, measure a **common observable target** with properly nested selection inside each outer training window, or report each feature-specific density separately as incomparable. For controls, report observed matching diagnostics and do not call circular shifts implementable. For inference, select bootstrap statistic and family before evaluation; do not equate non-significance and equivalence. Output source labels must distinguish original result and corrected reanalysis.

## UI ownership and dependencies

1c's TS frontend is a candidate only after contract and browser testing. Keep f10 app available until equivalent data access and traceability are proven. Adopt a single vetted `pyproject.toml` + pinned lock for the active research environment and one Node lockfile compatible with chosen UI; retain historical environment metadata. Compare version conflicts (f10 Python 3.11/numpy 2.4.6/sklearn 1.9.1; 1c run Python 3.11/numpy 2.3.5/sklearn 1.6.1). No new dependencies merely for appearance. CI must cover backend, frontend, integration and supported browser, not report presumed results.


---

# Proposed acceptance tests and phase gates

No tests below have been executed for this read-only audit. Existing reports' counts are historical only. A new run must record command, git/source/data hashes, dependency versions, environment, stdout/exit code, fixture identity and skipped reason.

## Gate 1: migration and contracts
1. Hash every source file and retained historical output before/after selective copying; f10 and 1c original source snapshots and their experiment files remain byte-identical; immutable output paths reject overwrite.
2. Canonical CSV sha `ea6dfffb93e5eabd8b6a2f96cd40d6b3ec5c7f47f2f9e6c0cbd3ca9a5f2ac5e4`, 4,684 rows, 2007-09-17..2026-10-22. Confirm logical equality and distinct newline hash for 1c root file, and explicitly identify vendor uncertainty. Missing required data must fail clearly.
3. Same `ModelSpec` produces reproducible probabilities; finite nonnegative probabilities sum to one; filter equals prefix-only inference and Gaussian reference, is continuous across train/test and insensitive to future mutation. Verify hard/soft state identity alignment and occupancy permutation. Record convergence and reject/fallback policy.
4. Explicit as-of contracts: training/scaling use previous data; forward label's end date is no later than the permitted fit time; mutate future raw closes and never affect earlier fits, predictions, target training labels or positions. Include 1, 5, 20, 60 horizon, missing dates and annual/refit boundaries. Compare the 1c code's currently unpurged case against a test designed to fail it.
5. Hold raw feature dimensions constant in likelihood comparison; verify inverse-scaling Jacobian. Test that K/feature/family selection for an early outer fold is invariant to future folds. Do not rank cross-dimensional densities without a justified common target.
6. New API schema is typed, JSON-finite, consistent with run-specific manifest; unknown ID/path returns 404, corrupt/missing input fails closed, path traversal cannot escape allowlists; API job endpoint is disabled or isolated until separately verified.
7. Characterization for K=2/3/4/5, permuted labels, rare/empty states, entropy, weighted quantiles, censored run boundaries and confidence categories; chronological separate forward outcomes; verify every displayed metric source.
8. Next-close and first earned return are tested with hand-calculated price series and nonzero cost, accrued cash, position drift, entry/exit turnover; controls on identical benchmark period. Test same-close optimism explicitly separately.

## Gate 2: reproducibility and defects
- From clean setup reproduce the delayed historical baseline with source `c163aa…`, input `ea6d…`, seeds, costs, cash and exact commands. Compare all metrics, dates, signals and fold outputs; report tolerances and actual platform versions. Reproduction is not the same as confirmation.
- Reproduce 1c study `study_20261030T111521Z`, and retained superseded studies where practical, using their declared original source/config/versions. A rerun of defective historical code is quarantined as historical and not promoted to evidence. Compare discovery/fits/feature/emission/predictive/allocation/statistics/characterization, exact vs tolerance; identify differences and missing original assets explicitly. Fail on unexplained material discrepancies.
- Test realistic nonconvergence and singular/zero occupancy, multiple seeds, full covariance/Student-t parity, train log-likelihood selection and changing data scales.
- For inference independently validate stationary block boundaries, paired calendar alignment, confidence coverage via simulation, correct daily risk-free units, centered/HAC variance, and declared maximum statistic. Exposure, turnover and vol-matching diagnostics must be shown rather than assumed; circular-shift wrap is not causal. Correct for the declared family and label the result's null.
- Numerical assertion tests for 1c reported score semantics, R² denominators, `median` vs mean and forward drawdown definitions, duration censoring and invalid freeze hash.
- Fresh backend test command, frontend unit tests, `npm ci`, production build, real browser E2E across all five pages, app and relative `/api` proxy from a clean setup; capture screenshot, exact status/skip counts, no historical substitutions. Optional dependencies/browser not available = explicit blocker.

## Gate 3: E7 protocol (before any E7 execution)
Require an approved document specifying K=3 and K=5 grouping, observation-to-fold weighting, posterior/hard weighting, complete fitted-spec definitions/seeds/fit policy, label end timing, bootstrap index/calendar alignment and block resampling of overlapping outcomes, family/studentization and one-sided decision rule, majority/each-spec conditions, missing states, minimum sample sizes and prospective boundary. Verify these do not contradict original 1c §10.8. If clarification is substantive, do not claim it was originally preregistered. No threshold or group tuning after observing results. Confirm new prospective observations strictly post-freeze; otherwise label exploratory.

## Gate 4/5: product and packaging
- Source trace link/hash, documented data and model features, historical limitations, genuine uncertainty, no fabricated metrics; selected date recomputation and downloads verified against full unsampled source. UI clearly distinguishes empirical transitions from fitted matrix and different horizons.
- No arbitrary data uploads, broker hooks, unverified job-launch control or unapproved public service.
- Accessibility/keyboard and responsive/browser tests, broken-route checks, rebuild from clean dependencies, reproducibility instructions with actual artifact locations and license caveat. Final Council refuses unsupported resume claims or release when research blockers remain.


---

# Known issues and risks — read-only Phase 0

These findings are static-code/audit observations, not fresh numerical reruns. 1c paths are relative to `market-regime-platform/` at c46541e. Historical reports and outputs are preserved as historical claims; do not silently correct them. Severity indicates priority for future review.

1. **Critical — forward-label maturity leakage in 1c.** `src/regime_backtester/predictive.py:64-74` constructs y[t] using future prices through t+h; `:222-243` fits `y[:begin]` with no horizon-specific purge. For h>1, near-boundary training labels include observations after the refit. The existing `tests/test_research_discovery.py:178-202` mutates already-materialized labels after a cutoff and does not test raw future prices affecting pre-cutoff forward labels. Calendar illustration from f10's actual signal dates: refit 2014-01-17 includes a label at 2014-01-16 whose 20-session outcome ends 2014-02-13. Needs reproducible failing test and fresh corrected research; negative historical numbers remain historical, not accepted clean OOS.
2. **Critical — non-comparable feature likelihoods.** `discovery.py:314-342` fits separate StandardScalers and returns mean log density in scaled feature space; `study.py:341-371` ranks those values across different-dimensional `rv2`, `rvd3`, etc. They are densities on different spaces, without common target or Jacobian. The documented +0.485 nats/day is a saved arithmetic subtraction, not defensible proof RV is better. Even a Jacobian alone does not make different dimensions comparable.
3. **High — selection leak / nonjoint feature-K selection.** `study.py:280-326,734-783` selects K using averages of inner-validation scores across all 15 expanding folds on RVD, then picks features at that K and emissions globally, then evaluates one selected specification on all folds. Decisions from later folds can influence which model is retrospectively reported for earlier evaluation folds. This is not fully nested causal model selection, and K selected on RVD cannot establish global optimality for RV. K4 is provisional.
4. **High — E7 protocol located but ambiguous.** `docs/RESEARCH_REPORT.md:416-428` states four specs (K3 RVD, K4 RV, K5 RV, K3 volatility-only), rank 2–3 vs 0–1, 20-session returns, majority of 15 folds, stationary bootstrap mean block 20, and max-stat 95% lower bound >0. K3 lacks rank 3; K5 has an unmentioned rank 4. Exact grouping, training-vs-OOS estimator, fold weighting, sampling unit, joint bootstrap, sample sizes, exact one-feature spec/seed and acceptance of each spec are not fully specified. Report says write E7 into register *before* running; available registers contain E0–E6. Clarify with user before execution; no change after seeing results.
5. **High — invalid prospective freeze and missing evidence.** 1c verification D2: archived freeze core hash `11094a40…` differs from its current core hash `abe195ac…`; f10 reports `c163aa…`. Main archived run `run_20261030_081436_12ea5b` lacks tables/status/freeze. Actual 1c tracked checkout has no populated `runs/`, only `results/.gitkeep` and `data/raw/.gitkeep`. Its README's assertion that raw input and two completed runs are already present is false for the tracked tree; the separately tracked ZIP contains the input and preliminary run. No qualifying post-freeze data. Never describe 2023–2026 as untouched.
6. **High — strategy/control inference.** In `allocation.py:138-145`, `np.roll` circularly shifts the entire realized exposure path, so phase shifts can use future exposure at earlier calendar dates; treat as retrospective permutation diagnostic, not live causal control. Vol-matched control initializes its first 250 sessions with the actual regime exposures (`:109-125`). Markov and volatility controls have different exposure/turnover distributions in the saved summary. `study.py:601-605` stores the mean of KS distances under `median_exposure_ks`. In `significance.py:68-110`, the family statistic uses mean daily return differences, whereas report §9.3 describes a Sharpe advantage. Recentring, variance/studentization and dependence must be independently validated before a p-value is used as a claim.
7. **High — `FoldFit.occupancy` rank alignment.** `discovery.py:191-200` permutes posterior columns, computes occupancy in sorted order, then `:218` indexes occupancy by `order` again. That is a second permutation for nonidentity ordering. Downstream impact is not yet established; do not extrapolate all saved results are affected. Add explicit permutation regression and map call sites.
8. **High — model convergence / fallback.** 1c `discovery.py:147-175` can fall back to a nonconverged fit if no converged seed qualifies, while its older UI `frontend/src/pages/Validation.tsx` says unconverged fits are rejected. f10's archived baseline rejects. Do not mix their acceptance policies or treat fallback as a certified fit. Validate the custom EM and Student-t scale update against independent references.
9. **Medium — duration and forward-risk semantics.** 1c `study.py:425-449` pools hard ranks across annual refits without censoring episodes and compares a mixture of varying-state runs with one geometric distribution. This is not a defensible latent-state duration test without additional justification. `predictive.py:70-72` defines minimum future close relative to current close, not maximum peak-to-trough drawdown over the future path.
10. **Medium — statistical/history wording.** 1c `predictive_summary.json`'s -0.00534/-0.01651/-0.00468 are `oos_r2_vs_observable` for adding regime variables, not R² for indicator-only models. User's context table labels them indicator-only; preserve correct denominator. Data cross-section is a single historical price index, not total return; no causal claims or trading proof.
11. **Medium — artifact contracts, dashboard/CI mismatch.** 1c's `backend/app.py` lists `runs/run_*` and `/api/runs/{id}`, not `research_outputs/study_*`; dashboard therefore cannot display its newer results without adapters. Tracked checkout has no runs/data file, so no completed run can be selected; do not assume 1c dashboard works from fresh checkout. 1c `.github/workflows/tests.yml` tests only Python; historical 63/3 is reported, not freshly verified here. 1c has frontend Vitest and Playwright source but verification says frontend/build/E2E not executed in that environment. f10's current own tests/build were historically executed, not rerun here.
12. **Medium — provenance/security/dependencies.** 1c studies have config, data hash and versions but no complete source snapshot/hash in the manifest; f10 baseline has source snapshot and curated hashes, but fixed experiment paths and partial hardcoded schemas. 1c frontend has older React Router/Vite dependency ranges requiring fresh audit; 1c `POST /api/job` launches subprocesses on unauthenticated service; keep disabled pending isolation and safety evaluation. No public deployment without separate approval.

## Reproduction priorities

Validate exact historical versions and frozen source first. Reproduce unmodified historical results separately from a corrected implementation; retain superseded results and openly register defects. Do not invent a prospective holdout or rewrite history. Obtain user decision on the fixed branch constraint and E7 clarifications when the relevant gate is reached.


---

# Simulated Research Council — Gate 0

Five simulated viewpoints used to challenge the same read-only audit; these are not external reviewers or independent people/systems. This is not a vote on positive research findings.

## Individual reviews and peer challenges

### 1. Contrarian — are we fooling ourselves?
- **Assessment:** Integration would be unsafe if the 1c report's feature and predictive conclusions are treated as verified. Cross-dimensional scaled likelihood ranking, globally selected specification, unpurged forward targets and selective historical data reuse can turn nominally OOS results into misleading evidence. The negative results remain historical, not automatically valid either.
- **Strongest recommendation:** Preserve all outputs, label the 1c findings as disputed, and require failing target-maturity and nested-selection tests before migrating claims or rerunning a corrected version.
- **Biggest concern:** Reproducing a flawed historical output could be mistaken for proving correctness. A clean numerical match does not validate an inference.
- **Reject if:** The dashboard presents K4/RV, +0.485 nats/day, unpurged forecasts, or phase-shift controls as validated predictive/trading findings, or relabels the retrospective period as prospective.
- **Peer challenge:** The Expansionist's richer dashboard and model engine may produce a more impressive interface while masking unverified results; no UI migration should precede an artifact-to-claim audit.

### 2. First Principles Thinker — is the underlying logic sound?
- **Assessment:** HMM filtering, joint log densities, probabilistic identity, causal training-label maturity and investable controls answer different mathematical questions. A 2-D density and 3-D density are not comparable merely because both are log-likelihoods, and a fold's inner model selection isn't nested if one global model is selected using later folds. E7's rank contrasts are under-specified for K=3 and K=5.
- **Strongest recommendation:** Freeze a precise common-target outer/inner selection protocol and test the timestamp at which each target becomes observable; define R² denominators, statistic and null explicitly. Preserve the custom EM as a candidate, not unquestioned ground truth.
- **Biggest concern:** Even a corrected Jacobian will not make feature spaces of differing dimension comparable. A stationary bootstrap on 15 folds is not automatically a 20-session block bootstrap.
- **Reject if:** An undefined E7 grouping is interpreted as a preregistered fact, or cross-feature log densities are ranked without a shared outcome.
- **Peer challenge:** The Executor's wish to port a minimally viable runner quickly cannot override the need for a mathematically specified test before implementation.

### 3. Expansionist — where is the highest-value opportunity?
- **Assessment:** f10 offers a clean base and clear weighted state characterization; 1c contributes reusable custom inference, alignment, multi-seed diagnostics, controls and a richer typed UI. The highest-value integration is transparent cross-run provenance and a reproducible defect-and-correction trail, not a larger model zoo.
- **Strongest recommendation:** Prototype 1c's frontend against a versioned, read-only, provenance-aware adapter with f10's measurable state descriptions, but retain the working f10 UI until parity and browser tests pass.
- **Biggest concern:** A minimalist cleanup that archives everything valuable would leave the newer study inaccessible and fail the intended platform's research utility.
- **Reject if:** A one-off visual migration omits a source link, hides failed seeds, discards old study files, or adds unapproved uploads/live trading.
- **Peer challenge:** The Contrarian's warning should not become an indefinite freeze of all engineering; a read-only adapter plus explicit defect badges can improve inspectability without endorsing a finding.

### 4. Outsider — what would an independent reviewer see?
- **Assessment:** An interviewer would value the divergent histories and negative findings, but would question a README claiming files that a clean checkout does not contain, a dashboard showing no runs, inconsistent freeze validity, and a forecast table that mislabels incremental R². f10's archive is cleaner; 1c's additional study is currently not surfaced by its dashboard.
- **Strongest recommendation:** Make the artifact source, verified data hash, exact timing, valid/invalid/pending status, reproducible command and known limitations first-class in every UI/report; adopt 1c's frontend only when evidenced by a working build and browser test.
- **Biggest concern:** Technical sophistication without transparent provenance is weaker than a small defensible research system.
- **Reject if:** Source histories disappear or archived legacy reports are silently presented as fresh findings; a screenshot alone cannot establish functionality.
- **Peer challenge:** The Expansionist's "richer" UI is not proven stronger from an external review standpoint until it reads new-study artifacts, handles invalid freezes and works from a clean checkout.

### 5. Executor — can this be delivered correctly?
- **Assessment:** The branches are not linear, packages share a namespace, 1c's raw data and runs are ignored, old dependency environments differ, and the session cannot create the requested separate integration branch. Copying modules or running historical tests blindly will fail or contaminate attribution.
- **Strongest recommendation:** Obtain a branch/session decision first; if allowed to proceed in the session branch, preserve both source SHA manifests and implement a small artifact contract plus mutation tests before any reanalysis. Keep the job endpoint off until separately validated.
- **Biggest concern:** Separate-branch preservation cannot be achieved under the current session's fixed-branch rule, and original 1c study artifacts do not provide all fit-level state series.
- **Reject if:** An agent switches branches in this session, overwrites historical artifacts, claims skips as passes, or begins E7 before protocol clarification.
- **Peer challenge:** The First Principles Thinker's requirement for perfect statistical validation should be staged: first add traceability and tests with explicitly incomplete statuses, then a rigorous nested research design; do not block safe preservation work.

## Chairman Verdict

### 1. WHERE THE COUNCIL AGREES

Preserve both histories and all historical outcomes; keep the supplied dataset and exact hash; separate baseline reproduction from corrected research; do not equate state distinction with predictive or trading value; prohibit unapproved scope expansion and prospective claims; use real tests and provenance, not historical pass counts or mock dashboard metrics.

### 2. WHERE THE COUNCIL CLASHES

The Expansionist favors an early richer dashboard adapter; the Contrarian and Outsider require provenance and honest validity labels first. The First Principles Thinker prioritizes statistical resolution; the Executor advocates incremental preservation and tests while maintaining an explicit blocked status. The separate-branch rule conflicts with this session's fixed branch; user approval cannot override the session's restriction.

### 3. BLIND SPOTS CAUGHT

The 1c forward-target training boundary and cross-dimensional likelihood comparisons directly undermine two historic inferences. Global selection over all folds leaks later-fold information into earlier reported OOS periods. E7 is found but ambiguous for K3/K5; missing definitions cannot be manufactured. The newer UI is richer but is wired to different artifacts and a clean checkout has neither its expected data path nor completed run. F10's RVD K3 and 1c RV K4 are not the same model, and 1c R² is incremental vs observables rather than indicator-only R². The diagnostic control's KS "median" is computed as a mean; the reality-check implementation operates on daily return differences rather than Sharpe differences. These do not retroactively prove a different result.

### 4. THE RECOMMENDATION

**BLOCKED BY MISSING EVIDENCE / APPROVAL.** Approve the Phase 0 findings as an audit only, not the proposed model conclusions. First decide whether to proceed on the fixed f10 session branch with its pre-integration commit preserved or start a separate Arena session configured for an integration branch. Then, within the approved foundation phase, archive exact 1c commit/studies and write targeted failing tests before any major research migration. E7 execution remains independently blocked until a protocol clarification is approved at the later gate.

### 5. THE ONE THING TO DO FIRST

**Decide the integration-branch constraint.** Completion condition: the user explicitly chooses either (A) continue on the fixed session branch with f10's original commit preserved, or (B) return with a separate Arena session targeting a new integration branch. No active repository modifications before that approval.


# SOURCE FILE: `phase0-integration-audit/docs/COUNCIL_GATE_0.md`

# Simulated Research Council — Gate 0

Five simulated viewpoints used to challenge the same read-only audit; these are not external reviewers or independent people/systems. This is not a vote on positive research findings.

## Individual reviews and peer challenges

### 1. Contrarian — are we fooling ourselves?
- **Assessment:** Integration would be unsafe if the 1c report's feature and predictive conclusions are treated as verified. Cross-dimensional scaled likelihood ranking, globally selected specification, unpurged forward targets and selective historical data reuse can turn nominally OOS results into misleading evidence. The negative results remain historical, not automatically valid either.
- **Strongest recommendation:** Preserve all outputs, label the 1c findings as disputed, and require failing target-maturity and nested-selection tests before migrating claims or rerunning a corrected version.
- **Biggest concern:** Reproducing a flawed historical output could be mistaken for proving correctness. A clean numerical match does not validate an inference.
- **Reject if:** The dashboard presents K4/RV, +0.485 nats/day, unpurged forecasts, or phase-shift controls as validated predictive/trading findings, or relabels the retrospective period as prospective.
- **Peer challenge:** The Expansionist's richer dashboard and model engine may produce a more impressive interface while masking unverified results; no UI migration should precede an artifact-to-claim audit.

### 2. First Principles Thinker — is the underlying logic sound?
- **Assessment:** HMM filtering, joint log densities, probabilistic identity, causal training-label maturity and investable controls answer different mathematical questions. A 2-D density and 3-D density are not comparable merely because both are log-likelihoods, and a fold's inner model selection isn't nested if one global model is selected using later folds. E7's rank contrasts are under-specified for K=3 and K=5.
- **Strongest recommendation:** Freeze a precise common-target outer/inner selection protocol and test the timestamp at which each target becomes observable; define R² denominators, statistic and null explicitly. Preserve the custom EM as a candidate, not unquestioned ground truth.
- **Biggest concern:** Even a corrected Jacobian will not make feature spaces of differing dimension comparable. A stationary bootstrap on 15 folds is not automatically a 20-session block bootstrap.
- **Reject if:** An undefined E7 grouping is interpreted as a preregistered fact, or cross-feature log densities are ranked without a shared outcome.
- **Peer challenge:** The Executor's wish to port a minimally viable runner quickly cannot override the need for a mathematically specified test before implementation.

### 3. Expansionist — where is the highest-value opportunity?
- **Assessment:** f10 offers a clean base and clear weighted state characterization; 1c contributes reusable custom inference, alignment, multi-seed diagnostics, controls and a richer typed UI. The highest-value integration is transparent cross-run provenance and a reproducible defect-and-correction trail, not a larger model zoo.
- **Strongest recommendation:** Prototype 1c's frontend against a versioned, read-only, provenance-aware adapter with f10's measurable state descriptions, but retain the working f10 UI until parity and browser tests pass.
- **Biggest concern:** A minimalist cleanup that archives everything valuable would leave the newer study inaccessible and fail the intended platform's research utility.
- **Reject if:** A one-off visual migration omits a source link, hides failed seeds, discards old study files, or adds unapproved uploads/live trading.
- **Peer challenge:** The Contrarian's warning should not become an indefinite freeze of all engineering; a read-only adapter plus explicit defect badges can improve inspectability without endorsing a finding.

### 4. Outsider — what would an independent reviewer see?
- **Assessment:** An interviewer would value the divergent histories and negative findings, but would question a README claiming files that a clean checkout does not contain, a dashboard showing no runs, inconsistent freeze validity, and a forecast table that mislabels incremental R². f10's archive is cleaner; 1c's additional study is currently not surfaced by its dashboard.
- **Strongest recommendation:** Make the artifact source, verified data hash, exact timing, valid/invalid/pending status, reproducible command and known limitations first-class in every UI/report; adopt 1c's frontend only when evidenced by a working build and browser test.
- **Biggest concern:** Technical sophistication without transparent provenance is weaker than a small defensible research system.
- **Reject if:** Source histories disappear or archived legacy reports are silently presented as fresh findings; a screenshot alone cannot establish functionality.
- **Peer challenge:** The Expansionist's "richer" UI is not proven stronger from an external review standpoint until it reads new-study artifacts, handles invalid freezes and works from a clean checkout.

### 5. Executor — can this be delivered correctly?
- **Assessment:** The branches are not linear, packages share a namespace, 1c's raw data and runs are ignored, old dependency environments differ, and the session cannot create the requested separate integration branch. Copying modules or running historical tests blindly will fail or contaminate attribution.
- **Strongest recommendation:** Obtain a branch/session decision first; if allowed to proceed in the session branch, preserve both source SHA manifests and implement a small artifact contract plus mutation tests before any reanalysis. Keep the job endpoint off until separately validated.
- **Biggest concern:** Separate-branch preservation cannot be achieved under the current session's fixed-branch rule, and original 1c study artifacts do not provide all fit-level state series.
- **Reject if:** An agent switches branches in this session, overwrites historical artifacts, claims skips as passes, or begins E7 before protocol clarification.
- **Peer challenge:** The First Principles Thinker's requirement for perfect statistical validation should be staged: first add traceability and tests with explicitly incomplete statuses, then a rigorous nested research design; do not block safe preservation work.

## Chairman Verdict

### 1. WHERE THE COUNCIL AGREES

Preserve both histories and all historical outcomes; keep the supplied dataset and exact hash; separate baseline reproduction from corrected research; do not equate state distinction with predictive or trading value; prohibit unapproved scope expansion and prospective claims; use real tests and provenance, not historical pass counts or mock dashboard metrics.

### 2. WHERE THE COUNCIL CLASHES

The Expansionist favors an early richer dashboard adapter; the Contrarian and Outsider require provenance and honest validity labels first. The First Principles Thinker prioritizes statistical resolution; the Executor advocates incremental preservation and tests while maintaining an explicit blocked status. The separate-branch rule conflicts with this session's fixed branch; user approval cannot override the session's restriction.

### 3. BLIND SPOTS CAUGHT

The 1c forward-target training boundary and cross-dimensional likelihood comparisons directly undermine two historic inferences. Global selection over all folds leaks later-fold information into earlier reported OOS periods. E7 is found but ambiguous for K3/K5; missing definitions cannot be manufactured. The newer UI is richer but is wired to different artifacts and a clean checkout has neither its expected data path nor completed run. F10's RVD K3 and 1c RV K4 are not the same model, and 1c R² is incremental vs observables rather than indicator-only R². The diagnostic control's KS "median" is computed as a mean; the reality-check implementation operates on daily return differences rather than Sharpe differences. These do not retroactively prove a different result.

### 4. THE RECOMMENDATION

**BLOCKED BY MISSING EVIDENCE / APPROVAL.** Approve the Phase 0 findings as an audit only, not the proposed model conclusions. First decide whether to proceed on the fixed f10 session branch with its pre-integration commit preserved or start a separate Arena session configured for an integration branch. Then, within the approved foundation phase, archive exact 1c commit/studies and write targeted failing tests before any major research migration. E7 execution remains independently blocked until a protocol clarification is approved at the later gate.

### 5. THE ONE THING TO DO FIRST

**Decide the integration-branch constraint.** Completion condition: the user explicitly chooses either (A) continue on the fixed session branch with f10's original commit preserved, or (B) return with a separate Arena session targeting a new integration branch. No active repository modifications before that approval.


# SOURCE FILE: `phase0-integration-audit/docs/INTEGRATION_PLAN.md`

# Proposed integration plan — Council Gate 0

**Status: proposal only.** No active repository files changed; no new experiments, tests or builds executed for this audit. Immutable references: f10 `9bb7f92d5785462462971d0479595c1d4166868c`, 1c `c46541e9ab8611330489a920c46cdb00342931d5`, merge base `f1602c5c95c14e4bd7795433ca6ecfd3d98794d6`. GitHub compare: 1c ahead by 2 and behind by 12 relative to f10. Inventories list 107 and 278 tracked files respectively. f10 checkout is shallow at 31902b7; remote API supplied older history. Both have the exact same older Arena ZIP (`bdf7b9136f8fd9b52dc6eedd34fd916c74f8baaaccc8815b3bd170dfc948d4b1`); the ZIP does not contain 1c's newer research code, reports or study outputs.

## Gate and branch restriction

The execution environment locks work to `arena/f10f6e2d-market-regime-analyzer` and prohibits creating or switching branches. The requested separate integration branch cannot be created in this session, even after approval. Options: (A) continue integration on the fixed branch while preserving the exact current f10 snapshot/commit and the untouched 1c branch; the f10 branch name would move, though its old commit remains reachable; or (B) the user starts a new Arena session configured with a separate integration branch. No branch will be created, renamed, or pushed by this audit. If retaining f10's branch pointer unchanged is essential, choose B. No wholesale merge.

## Sequence after an appropriate branch/session decision

1. **Foundation, preserve first.** Verify f10 archive hashes, save a manifest of original 1c commit, path-level inventories and immutable history; preserve 1c study directories including superseded studies and reports under `historical/1c/` or immutable source snapshot storage. Copy selectively, avoid accidental Git LFS/large data or duplicated active implementations. Never overwrite existing f10 `research/experiments/*`. Record exact source commits, source paths, content hashes, transformations and decisions. Keep source snapshots read-only.
2. **Dependencies and core.** Establish one `research/data/nifty_index.csv` input (current f10 attachment), with sha verification. Keep legacy f10 baseline engine/config intact for exact reproduction. Introduce 1c research modules behind a separate versioned package/adapter, not a mixed directory that may shadow the legacy engine. Unify immutable config/provenance schema without changing recorded configs. Initially route read-only artifact access; API may expose multiple schema versions.
3. **Methodology verification before model claims.** Add failing regression tests for target-maturity leakage, dimensionality-comparable scoring, global-selection leakage, label alignment, nonconvergence policy, matched controls, duration censoring and precise metric definitions. Resolve with a reviewed protocol, not a silent backport. Preserve historical results with defect labels. Do not assert the RV-vs-RVD delta supports a feature choice or that selected 1c OOS is independent until those findings are resolved.
4. **Dashboard.** Treat 1c TypeScript dashboard as candidate, not accepted by appearance. Its API consumes archived `runs/run_*` attribution-schema artifacts, not the newer `research_outputs/study_*`, and clean 1c checkout contains no `runs/` or raw input. Prototype an adapter for f10 baseline + 1c historical studies, carrying source/validity/status; independently run unit/build/browser checks. Keep f10 characterization as typed measured data. Disable 1c's write-capable job endpoint/button until execution, isolation, resource limits, provenance and access assumptions are accepted. Never present an older invalid hash freeze as valid prospective validation.
5. **Phase 2 only after Gate 1.** Reproduce both baseline and research studies from their exact source snapshots and locks in isolated workspaces; compare every artifact under declared tolerances, distinguishing exact historical reproduction from corrected reanalysis. If historical code contains defects, reproduce unchanged only in isolation, flag outputs, then run corrected code as a separate ID. Gate 2 blocks research claims for unexplained discrepancies.
6. **E7 only after approved clarification and Gate 2.** The 1c report section 10.8 supplies four candidates and a sign criterion, but does not resolve rank pooling for K=3/5, bootstrap units, sample weighting, and precise fit/config for all candidates. Record these gaps before using the data again. Do not change a criterion post hoc. Distinguish exploratory historical follow-up from a newly frozen truly prospective test.
7. **Finish product / release.** Complete five user-facing sections only after experiment contracts and UI are verified. No uploads/live trading. Final documentation, E2E and public security review remain later gates.

## Provisional decisions

- f10's direct experiment hash checks and characterization are retained as behavior, but its monolithic API, fixed paths, and standalone scripts are not the final abstraction.
- 1c custom EM is a candidate with explicit numerical/parity testing; no assumed superiority over `hmmlearn`. Fail-closed versus nonconverged fallback must be explicit.
- 1c's sequence K-on-RVD then features-at-fixed-K is not joint K-feature selection; per-fold causal selection must be designed before new OOS claims. Likelihoods of different-dimensional observations are not directly comparable.
- Maintain historical baseline result as retrospective: HMM + Trend vs Trend Sharpe difference +0.0014 with 95% interval approximately [-0.1887, 0.1774]. Do not imply superiority or prospective validation.

## First executable action after user decision

On the permitted branch, create only a component-provenance manifest and read-only characterization/forecast contract tests against preserved artifacts; pass untouched historical-hash checks and reproduce the existing f10 suite before touching code. This is conditional on a branch/session decision and explicit Gate 0 approval.


# SOURCE FILE: `phase0-integration-audit/docs/ARCHITECTURE_PROPOSAL.md`

# Architecture proposal — conditional

## Intended active repository

```text
backend/                       FastAPI read-only artifact service, versioned contracts
frontend/                      one React/TS client after parity verification
research/
  data/nifty_index.csv         canonical user-supplied dataset (not a vendor guarantee)
  engine/                      causal features, typed model and inference adapters
  runner/                      immutable configurations and reproducible job CLI
  legacy/                      f10 historical baseline engine (unchanged)
  experiments/                 immutable run-specific artifacts and source snapshots
historical/                    exact source/outputs from both branches, manifests
config/                        validated, versioned experiment definitions
tests/                         research, API, integration, statistics, fixtures
frontend/tests/, frontend/e2e/  unit and browser tests
docs/                          decisions, risks, experiment register, validation history
```

This is not permission to move or rewrite files in Phase 0. Namespaces must prevent mixing the legacy `regime_backtester` with 1c's identically named package. Keep f10 baseline implementation immutable; a separate package `research_engine` and explicit adapters is safer than overwriting imports or silently altering historic source hashes.

## Contracts

- Data service: canonical hash `ea6d…`, input provenance, indexed strictly increasing dates, quality report and feature warmup. Date t uses only OHLC available by close t; Open diagnostics flagged. Alternate datasets require a separately approved hypothesis.
- Model input: typed `ModelSpec` (feature names/order, K, emission, covariance, scaler, fit algorithm, seeds, train range), `FoldSchedule`, and versioned fit diagnostics. Fit sees only training data. `filter(test, previous_alpha)` returns `P(S_t|X_≤t)`, per-step conditional log density in declared units, final alpha; label ordering is explicit and mapping stored. Never expose full-sample smoothed probabilities as decision signals. Characterization takes arbitrary K and a fold identity.
- Experiment contract: distinct immutable ID, source commit + script hash, data hash, config and command, dependency versions, UTC timestamp, train/signal/execution/evaluation boundaries, selected/rejected fits, benchmark, costs, cash, seed, statistical family and status. Atomically write new run directory; preserve prior immutable results; a manifest with per-file hashes identifies every UI number. A `LATEST` pointer can be mutable, not the results themselves. Comparisons across different schemas use adapters and retain original attribution; absent values are missing, not zero or synthetic.
- API contract: `GET /api/experiments`, `/api/experiments/{id}`, `/states`, `/timeline`, `/strategies`, `/forecasts`, `/validation`, `/data-quality`, `/artifacts/{allowlisted_name}`. Include experiment ID, artifact hash, units, period, timing, analysis mode and methodological validity status in every response. 404 for missing; 409/422 for mismatched schema; 503 for integrity failure. Plan a compatibility adapter for f10's `/api/research` and 1c's `/api/runs/*` until callers migrate. No browser localhost calls; same-origin API/static frontend for port 8000 or Vite reverse proxy. Public-facing auth is not assumed; local-only security posture and no automatic arbitrary jobs.
- UI contract: one owner/renderer per metric; semantic units, title, source link and whether training, OOS, retrospective or prospective. Do not interpret state IDs as fixed categories. Hide absent experiments and invalid statistical claims, not backfill from mocks. Five candidate views (overview, regime, strategy, validation/controls, data/provenance); responsive keyboard-accessible, no misleading hard-coded test counts.

## Method selection and missing information

Both implementations offer useful patterns, but neither is accepted wholesale. 1c forecast training labels and cross-dimensional scores need repair; f10 uses K=3-specific inputs and only a fixed baseline. For state/feature selection, measure a **common observable target** with properly nested selection inside each outer training window, or report each feature-specific density separately as incomparable. For controls, report observed matching diagnostics and do not call circular shifts implementable. For inference, select bootstrap statistic and family before evaluation; do not equate non-significance and equivalence. Output source labels must distinguish original result and corrected reanalysis.

## UI ownership and dependencies

1c's TS frontend is a candidate only after contract and browser testing. Keep f10 app available until equivalent data access and traceability are proven. Adopt a single vetted `pyproject.toml` + pinned lock for the active research environment and one Node lockfile compatible with chosen UI; retain historical environment metadata. Compare version conflicts (f10 Python 3.11/numpy 2.4.6/sklearn 1.9.1; 1c run Python 3.11/numpy 2.3.5/sklearn 1.6.1). No new dependencies merely for appearance. CI must cover backend, frontend, integration and supported browser, not report presumed results.


# SOURCE FILE: `phase0-integration-audit/docs/COMPONENT_MIGRATION_MAP.md`

# Component migration map — proposed, not executed

Paths prefixed `1c:` are relative to `market-regime-platform/` at c46541e; `f10:` are relative to f10 root at 9bb7f92. Destinations below are provisional logical paths; historical copies remain immutable. Classifications apply to active components, not deletion of research records. Every selection is conditional on tests in `INTEGRATION_ACCEPTANCE_TESTS.md`.

| Component / classification | Source → proposed destination | Dependencies and interface | Conflict / verification |
|---|---|---|---|
| Repository structure — **Keep from f10** | `f10:historical/`, `research/`, `docs/` → same | Git commit, archive checksums | Original 1c code not inside the shared old Arena ZIP; archive exact 1c source and outputs separately. Verify all file hashes and both source SHAs. |
| NIFTY canonical dataset — **Keep from f10** | `f10:research/data/nifty_index.csv` → same | CSV Date/Open/High/Low/Close, SHA ea6d… | 1c `data/raw/` contains only README/.gitkeep; 1c root CSV is LF hash cf384… but parsed rows match. No silent line-ending canonicalization or vendor-quality claim. Check file SHA, rows, dates, OHLC and provenance/licence. |
| Original baseline — **Keep from f10** | `f10:research/legacy/{run.py,config/,src/regime_backtester/}` → `research/legacy/` | hmmlearn, pandas, scipy, sklearn, YAML | Keep byte-for-byte source and f10 `baseline_20261104/source` snapshot. Baseline timing/cost/signal comparison against both artifacts and historical output. |
| f10 experiments — **Keep from f10** | `f10:research/experiments/{baseline_20261104,characterization_20261104,forecast_20261104,model_grid_20261104}` → same | manifest, input/source/signal snapshots | Preserve old config/results and statuses. Existing code uses hard-coded IDs/paths; adapter should not modify artifacts. Verify manifest and as-of timestamp semantics. |
| Historical 1c studies — **Archive** | `1c:research_outputs/study_20261030T{102052,104848,111521}Z/` + `LATEST` → `historical/1c/studies/` | Each run manifest/register/CSV | Preserve superseded D3/D6 results with defect flags; no silent current-results promotion. Verify full manifest and report-to-artifact reconciliation. |
| Historical 1c reports — **Archive** | `1c:docs/{RESEARCH_REPORT,VERIFICATION,BASELINE_AUDIT,DATA,METHODOLOGY,RUNS_AND_PROVENANCE,TEST_REPORT,PLATFORM_GUIDE}.md`, `reports/` → `historical/1c/docs/` | Original paths, source SHA | Report may assert invalid density/forecast claims or absent files. Keep unmodified, add prominent overlay/cross-reference; do not edit originals. |
| Research feature engineering — **Combine** | `1c:src/regime_backtester/features.py`, `f10:research/legacy/src/regime_backtester/features.py` → versioned `research/engine/features.py` adapter | causal trailing OHLC features, pandas | Preserve baseline definitions and warm-up; keep diagnostic-only OHLC separate and vendor warning. Compare equal features, prefix mutation, missing rows. |
| Custom EM / inference — **Migrate from 1c** (conditional) | `1c:src/regime_backtester/emhmm.py` → `research/engine/emhmm.py` | numpy/scipy/sklearn KMeans; input ndarray, `HMMFit.filter`, output probabilities/log density/final alpha | Do not replace f10 baseline. Full/diag Gaussian and Student-t remain candidates. Test numerical parity to independent likelihood/filter, posterior normalization, input/seed/convergence/rejection, Student-t scale updates, and future mutation; document failed fits. |
| Discovery, seeds, state alignment — **Combine** | `1c:src/regime_backtester/discovery.py`, `f10:research/analysis/model_grid.py` → `research/engine/discovery.py` and `research/experiments/...` | `Spec`, `FoldFit`, scaling, filtered test probabilities, train-window state vols, Hungarian matching | 1c global post-hoc selection across future folds and two-stage K/feature selection; no comparable dimensional joint scores. f10 grid uses raw-space Jacobian but rightly avoids cross-dimensional ranking. Fix using a pre-agreed common predictive target and nested selection. Check double-reordered `FoldFit.occupancy` and convergence fallback. Do not overwrite saved grids. |
| Student-t/sticky emission experiments — **Migrate from 1c** only as historical reproducibility candidates | `1c:emhmm.py`, `study.py:study_emissions` → versioned engine + experiment runner | Student-t scale/dof, sticky transition prior | Preserve tests and `emissions/` outputs. Current Student-t update divides weighted covariance by sum(gamma*u); verify against a trusted reference before interpreting dof or comparative fit. Sticky != explicit duration model. |
| Characterization — **Combine** | `f10:research/analysis/characterize.py`, `1c:predictive.py` state summaries → `research/engine/characterization.py` | as-of filtered posteriors, features, fold identity, transition matrices | Replace hard-coded 3 columns/model-specific inputs with K-aware schemas; keep weighted descriptions, entropy, refit-censored durations, separate forward outcomes and OHLC caveats. Compare old output exactly before adding features; test permutations/censoring/rare flags. |
| Forward targets and forecasting — **Rewrite** (retain originals archived) | `f10:research/analysis/forecast.py`, `1c:src/regime_backtester/predictive.py` → `research/engine/predictive.py` | typed target with outcome end-date, purged expanding fits, Ridge/HAC, probability/observable inputs | 1c `expanding_oos` trains on `slice(0,begin)` without purging outcomes crossing the test boundary; f10 explicitly purges. Preserve original R² labels/baselines; test future price mutation, label maturity, window boundaries, date alignment. Fwd min-from-entry is not peak-to-trough maximum drawdown. |
| Backtest execution & strategies — **Keep from f10** with **Combine** interfaces | `f10:research/legacy/src/regime_backtester/{execution,strategies,metrics}.py`, `1c:src/regime_backtester/allocation.py` → versioned execution/strategy adapters | self-financing simulator; signal t, execution t+1 close, return t+2; fixed cash/cost | Compare exact cash accrual, turnover, benchmark dates and missing days. Keep arithmetic blend distinct from gates; test entry/exit and no lookahead. |
| Allocation and controls — **Migrate from 1c** with conditions | `1c:src/regime_backtester/{allocation,significance,attribution}.py` → `research/engine/{allocation,statistics,controls}.py` | HMM signals/exposures, prices, seeds, stationary bootstrap | Circular phase shift is retrospective null not causal strategy; Markov/vol controls not guaranteed matching. 1c `median_exposure_ks` uses `np.mean`. Verify return-vs-Sharpe statistic, long-run variance, causality, matching quality, bootstrap uncertainty and corrected family. Retain fixed 6.5% assumptions. |
| Orchestration & provenance — **Combine** | `1c:study.py`, `experiment_tracking.py`, `f10:research/experiments/artifact_manifest.json` and CLI scripts → `research/runner/`, `research/experiments/` | YAML input + immutable manifest, exact code/data/dependency hashes | 1c research `manifest.json` records dataset/config/versions but not full content-addressed source snapshot; LATEST is mutable pointer. Validate no collisions/overwrite, exact config, source snapshots, subprocess isolation and failure statuses. |
| Prospective freeze — **Archive / rewrite** | `1c:holdout.py`, archived `holdout_freeze.json` → historical snapshot plus new versioned checker | source/config/data checksum and genuinely future observations | Existing freeze hash differs from current source and observation ends 2026-10-22. Expose as invalid/pending, never mutate old freeze. Tests for source, prefix, date and revised-data refusal. |
| API — **Combine** | `1c:backend/app.py`, `f10:backend/research_api.py` → `backend/app.py`, `backend/contracts/` | FastAPI, typed JSON, read-only run/artifact IDs | 1c `/api/runs/...` expects runs/attribution; f10 `/api/research` is a fixed combined schema; 1c study files lack same artifacts. Versioned adapter; fail closed on missing provenance, missing files, NaN, path traversal. Job POST disabled initially. |
| 1c dashboard — **Migrate from 1c** (candidate, not approved final) | `1c:frontend/src/{App.tsx,pages,components,types,api}.tsx` → `frontend/` | TS, React, router, recharts, API contracts, npm lock | Five-page navigation and interactions are richer; current source only reads older `runs` not 1c research_outputs, tests were not run in 1c environment. UI assumes source fit rejection and some state counts; freeze display must validate hash. Unit/build/real-browser/screenshot/data trace tests. |
| f10 dashboard — **Keep from f10** until replacement passes tests | `f10:frontend/src/{App.jsx,main.jsx,research.css}` → retained during migration | `/api/research` and fixed artifacts | Do not run two conflicting active apps indefinitely. Preserve as fallback/history; only archive after feature parity and numeric traceability demonstrated. |
| f10 artifact API — **Keep from f10** as compatibility layer | `f10:backend/research_api.py` → temporary compatibility router | SHA manifest, static frontend, no auth | Ensure current `/api/research`, `/api/artifacts/*`, and port 8000 still work. Per-run integrity for all displayed/downloaded files; avoid catch-all masking API errors. |
| 1c root legacy duplicate app — **Archive** | `1c:backend/`, `1c:frontend/`, root notebooks/CSVs → source SHA/old archive | Git original, exact path inventory | This is not the newer 1c `market-regime-platform/frontend`. f10 already archived original 31902b7; confirm byte differences before treating as duplicate. |
| 1c synthetic and independent aggregate examples — **Archive** | `1c:examples/synthetic_run/`, `validation/independent_nifty/` → `historical/1c/` | metadata/source-kind | Clearly SYNTHETIC or aggregate-only; independent source lacks redistributed data/licence. Never combine into historical NIFTY results. |
| Tests / CI — **Combine** | `f10:tests/`, `1c:tests/`, `1c:frontend/tests`, `frontend/e2e`, `.github/workflows/tests.yml` → active `tests/`, `frontend/tests/`, CI | pytest, httpx, Vitest, Playwright, pinned Node/Python | 1c CI is Python-only and dataset/artifacts ignored. Include real fixtures, no missing-data false passes, browser proxy and CSV checks. 1c historical test counts not fresh. |
| Demo/unsafe scope — **Reject** | general OHLC upload, live brokerage, unfrozen new model families | N/A | User explicitly deferred; exclude until separate approved hypothesis and safety design. |


# SOURCE FILE: `phase0-integration-audit/docs/INTEGRATION_ACCEPTANCE_TESTS.md`

# Proposed acceptance tests and phase gates

No tests below have been executed for this read-only audit. Existing reports' counts are historical only. A new run must record command, git/source/data hashes, dependency versions, environment, stdout/exit code, fixture identity and skipped reason.

## Gate 1: migration and contracts
1. Hash every source file and retained historical output before/after selective copying; f10 and 1c original source snapshots and their experiment files remain byte-identical; immutable output paths reject overwrite.
2. Canonical CSV sha `ea6dfffb93e5eabd8b6a2f96cd40d6b3ec5c7f47f2f9e6c0cbd3ca9a5f2ac5e4`, 4,684 rows, 2007-09-17..2026-10-22. Confirm logical equality and distinct newline hash for 1c root file, and explicitly identify vendor uncertainty. Missing required data must fail clearly.
3. Same `ModelSpec` produces reproducible probabilities; finite nonnegative probabilities sum to one; filter equals prefix-only inference and Gaussian reference, is continuous across train/test and insensitive to future mutation. Verify hard/soft state identity alignment and occupancy permutation. Record convergence and reject/fallback policy.
4. Explicit as-of contracts: training/scaling use previous data; forward label's end date is no later than the permitted fit time; mutate future raw closes and never affect earlier fits, predictions, target training labels or positions. Include 1, 5, 20, 60 horizon, missing dates and annual/refit boundaries. Compare the 1c code's currently unpurged case against a test designed to fail it.
5. Hold raw feature dimensions constant in likelihood comparison; verify inverse-scaling Jacobian. Test that K/feature/family selection for an early outer fold is invariant to future folds. Do not rank cross-dimensional densities without a justified common target.
6. New API schema is typed, JSON-finite, consistent with run-specific manifest; unknown ID/path returns 404, corrupt/missing input fails closed, path traversal cannot escape allowlists; API job endpoint is disabled or isolated until separately verified.
7. Characterization for K=2/3/4/5, permuted labels, rare/empty states, entropy, weighted quantiles, censored run boundaries and confidence categories; chronological separate forward outcomes; verify every displayed metric source.
8. Next-close and first earned return are tested with hand-calculated price series and nonzero cost, accrued cash, position drift, entry/exit turnover; controls on identical benchmark period. Test same-close optimism explicitly separately.

## Gate 2: reproducibility and defects
- From clean setup reproduce the delayed historical baseline with source `c163aa…`, input `ea6d…`, seeds, costs, cash and exact commands. Compare all metrics, dates, signals and fold outputs; report tolerances and actual platform versions. Reproduction is not the same as confirmation.
- Reproduce 1c study `study_20261030T111521Z`, and retained superseded studies where practical, using their declared original source/config/versions. A rerun of defective historical code is quarantined as historical and not promoted to evidence. Compare discovery/fits/feature/emission/predictive/allocation/statistics/characterization, exact vs tolerance; identify differences and missing original assets explicitly. Fail on unexplained material discrepancies.
- Test realistic nonconvergence and singular/zero occupancy, multiple seeds, full covariance/Student-t parity, train log-likelihood selection and changing data scales.
- For inference independently validate stationary block boundaries, paired calendar alignment, confidence coverage via simulation, correct daily risk-free units, centered/HAC variance, and declared maximum statistic. Exposure, turnover and vol-matching diagnostics must be shown rather than assumed; circular-shift wrap is not causal. Correct for the declared family and label the result's null.
- Numerical assertion tests for 1c reported score semantics, R² denominators, `median` vs mean and forward drawdown definitions, duration censoring and invalid freeze hash.
- Fresh backend test command, frontend unit tests, `npm ci`, production build, real browser E2E across all five pages, app and relative `/api` proxy from a clean setup; capture screenshot, exact status/skip counts, no historical substitutions. Optional dependencies/browser not available = explicit blocker.

## Gate 3: E7 protocol (before any E7 execution)
Require an approved document specifying K=3 and K=5 grouping, observation-to-fold weighting, posterior/hard weighting, complete fitted-spec definitions/seeds/fit policy, label end timing, bootstrap index/calendar alignment and block resampling of overlapping outcomes, family/studentization and one-sided decision rule, majority/each-spec conditions, missing states, minimum sample sizes and prospective boundary. Verify these do not contradict original 1c §10.8. If clarification is substantive, do not claim it was originally preregistered. No threshold or group tuning after observing results. Confirm new prospective observations strictly post-freeze; otherwise label exploratory.

## Gate 4/5: product and packaging
- Source trace link/hash, documented data and model features, historical limitations, genuine uncertainty, no fabricated metrics; selected date recomputation and downloads verified against full unsampled source. UI clearly distinguishes empirical transitions from fitted matrix and different horizons.
- No arbitrary data uploads, broker hooks, unverified job-launch control or unapproved public service.
- Accessibility/keyboard and responsive/browser tests, broken-route checks, rebuild from clean dependencies, reproducibility instructions with actual artifact locations and license caveat. Final Council refuses unsupported resume claims or release when research blockers remain.


# SOURCE FILE: `phase0-integration-audit/docs/KNOWN_ISSUES_AND_RISKS.md`

# Known issues and risks — read-only Phase 0

These findings are static-code/audit observations, not fresh numerical reruns. 1c paths are relative to `market-regime-platform/` at c46541e. Historical reports and outputs are preserved as historical claims; do not silently correct them. Severity indicates priority for future review.

1. **Critical — forward-label maturity leakage in 1c.** `src/regime_backtester/predictive.py:64-74` constructs y[t] using future prices through t+h; `:222-243` fits `y[:begin]` with no horizon-specific purge. For h>1, near-boundary training labels include observations after the refit. The existing `tests/test_research_discovery.py:178-202` mutates already-materialized labels after a cutoff and does not test raw future prices affecting pre-cutoff forward labels. Calendar illustration from f10's actual signal dates: refit 2014-01-17 includes a label at 2014-01-16 whose 20-session outcome ends 2014-02-13. Needs reproducible failing test and fresh corrected research; negative historical numbers remain historical, not accepted clean OOS.
2. **Critical — non-comparable feature likelihoods.** `discovery.py:314-342` fits separate StandardScalers and returns mean log density in scaled feature space; `study.py:341-371` ranks those values across different-dimensional `rv2`, `rvd3`, etc. They are densities on different spaces, without common target or Jacobian. The documented +0.485 nats/day is a saved arithmetic subtraction, not defensible proof RV is better. Even a Jacobian alone does not make different dimensions comparable.
3. **High — selection leak / nonjoint feature-K selection.** `study.py:280-326,734-783` selects K using averages of inner-validation scores across all 15 expanding folds on RVD, then picks features at that K and emissions globally, then evaluates one selected specification on all folds. Decisions from later folds can influence which model is retrospectively reported for earlier evaluation folds. This is not fully nested causal model selection, and K selected on RVD cannot establish global optimality for RV. K4 is provisional.
4. **High — E7 protocol located but ambiguous.** `docs/RESEARCH_REPORT.md:416-428` states four specs (K3 RVD, K4 RV, K5 RV, K3 volatility-only), rank 2–3 vs 0–1, 20-session returns, majority of 15 folds, stationary bootstrap mean block 20, and max-stat 95% lower bound >0. K3 lacks rank 3; K5 has an unmentioned rank 4. Exact grouping, training-vs-OOS estimator, fold weighting, sampling unit, joint bootstrap, sample sizes, exact one-feature spec/seed and acceptance of each spec are not fully specified. Report says write E7 into register *before* running; available registers contain E0–E6. Clarify with user before execution; no change after seeing results.
5. **High — invalid prospective freeze and missing evidence.** 1c verification D2: archived freeze core hash `11094a40…` differs from its current core hash `abe195ac…`; f10 reports `c163aa…`. Main archived run `run_20261030_081436_12ea5b` lacks tables/status/freeze. Actual 1c tracked checkout has no populated `runs/`, only `results/.gitkeep` and `data/raw/.gitkeep`. Its README's assertion that raw input and two completed runs are already present is false for the tracked tree; the separately tracked ZIP contains the input and preliminary run. No qualifying post-freeze data. Never describe 2023–2026 as untouched.
6. **High — strategy/control inference.** In `allocation.py:138-145`, `np.roll` circularly shifts the entire realized exposure path, so phase shifts can use future exposure at earlier calendar dates; treat as retrospective permutation diagnostic, not live causal control. Vol-matched control initializes its first 250 sessions with the actual regime exposures (`:109-125`). Markov and volatility controls have different exposure/turnover distributions in the saved summary. `study.py:601-605` stores the mean of KS distances under `median_exposure_ks`. In `significance.py:68-110`, the family statistic uses mean daily return differences, whereas report §9.3 describes a Sharpe advantage. Recentring, variance/studentization and dependence must be independently validated before a p-value is used as a claim.
7. **High — `FoldFit.occupancy` rank alignment.** `discovery.py:191-200` permutes posterior columns, computes occupancy in sorted order, then `:218` indexes occupancy by `order` again. That is a second permutation for nonidentity ordering. Downstream impact is not yet established; do not extrapolate all saved results are affected. Add explicit permutation regression and map call sites.
8. **High — model convergence / fallback.** 1c `discovery.py:147-175` can fall back to a nonconverged fit if no converged seed qualifies, while its older UI `frontend/src/pages/Validation.tsx` says unconverged fits are rejected. f10's archived baseline rejects. Do not mix their acceptance policies or treat fallback as a certified fit. Validate the custom EM and Student-t scale update against independent references.
9. **Medium — duration and forward-risk semantics.** 1c `study.py:425-449` pools hard ranks across annual refits without censoring episodes and compares a mixture of varying-state runs with one geometric distribution. This is not a defensible latent-state duration test without additional justification. `predictive.py:70-72` defines minimum future close relative to current close, not maximum peak-to-trough drawdown over the future path.
10. **Medium — statistical/history wording.** 1c `predictive_summary.json`'s -0.00534/-0.01651/-0.00468 are `oos_r2_vs_observable` for adding regime variables, not R² for indicator-only models. User's context table labels them indicator-only; preserve correct denominator. Data cross-section is a single historical price index, not total return; no causal claims or trading proof.
11. **Medium — artifact contracts, dashboard/CI mismatch.** 1c's `backend/app.py` lists `runs/run_*` and `/api/runs/{id}`, not `research_outputs/study_*`; dashboard therefore cannot display its newer results without adapters. Tracked checkout has no runs/data file, so no completed run can be selected; do not assume 1c dashboard works from fresh checkout. 1c `.github/workflows/tests.yml` tests only Python; historical 63/3 is reported, not freshly verified here. 1c has frontend Vitest and Playwright source but verification says frontend/build/E2E not executed in that environment. f10's current own tests/build were historically executed, not rerun here.
12. **Medium — provenance/security/dependencies.** 1c studies have config, data hash and versions but no complete source snapshot/hash in the manifest; f10 baseline has source snapshot and curated hashes, but fixed experiment paths and partial hardcoded schemas. 1c frontend has older React Router/Vite dependency ranges requiring fresh audit; 1c `POST /api/job` launches subprocesses on unauthenticated service; keep disabled pending isolation and safety evaluation. No public deployment without separate approval.

## Reproduction priorities

Validate exact historical versions and frozen source first. Reproduce unmodified historical results separately from a corrected implementation; retain superseded results and openly register defects. Do not invent a prospective holdout or rewrite history. Obtain user decision on the fixed branch constraint and E7 clarifications when the relevant gate is reached.


# SOURCE FILE: `phase0-integration-audit/COMMAND_AND_EVIDENCE_LOG.md`

# Phase 0 command and evidence log

All commands ran read-only against the active repository unless explicitly writing the external `/home/user/phase0-integration-audit` deliverables. The following are exact commands executed during the final verification portion; their exit codes were **0**. No test/build/experiment command was run in this phase. The earlier session's f10 result of `14 passed, 1 warning` and frontend build, and 1c's own report of `63 passed, 3 skipped`, are historical records, not fresh results.

```bash
# Remote tree counts: both trees are not truncated; 278 blobs and 107 blobs.
gh api 'repos/Akshat-1234/Market-Regime-Analyzer/git/trees/c46541e9ab8611330489a920c46cdb00342931d5?recursive=1' --jq '[.truncated, ([.tree[]|select(.type=="blob")]|length)] | @tsv'
gh api 'repos/Akshat-1234/Market-Regime-Analyzer/git/trees/9bb7f92d5785462462971d0479595c1d4166868c?recursive=1' --jq '[.truncated, ([.tree[]|select(.type=="blob")]|length)] | @tsv'

# Inventories, written outside repository.
cd /home/user/Market-Regime-Analyzer && git ls-files | LC_ALL=C sort > /home/user/phase0-integration-audit/inventory/f10-9bb7f92-files.txt
cd /tmp/mra-phase0-1c/Market-Regime-Analyzer-c46541e9ab8611330489a920c46cdb00342931d5 && find . -type f -printf '%P\n' | LC_ALL=C sort > /home/user/phase0-integration-audit/inventory/1c-c46541e-files.txt

# Remote commit ancestry, written outside repository (22 and 12 entries).
gh api 'repos/Akshat-1234/Market-Regime-Analyzer/commits?sha=9bb7f92d5785462462971d0479595c1d4166868c&per_page=100' --jq '.[] | [.sha, .commit.author.date, (.commit.message | split("\n")[0])] | @tsv' > /home/user/phase0-integration-audit/inventory/f10-commit-history.tsv
gh api 'repos/Akshat-1234/Market-Regime-Analyzer/commits?sha=c46541e9ab8611330489a920c46cdb00342931d5&per_page=100' --jq '.[] | [.sha, .commit.author.date, (.commit.message | split("\n")[0])] | @tsv' > /home/user/phase0-integration-audit/inventory/1c-commit-history.tsv

# Compare exact older project archive hashes; both bdf7b913...c948d4b1.
sha256sum historical/arena-market-regime-platform.zip /tmp/mra-phase0-1c/Market-Regime-Analyzer-c46541e9ab8611330489a920c46cdb00342931d5/market-regime-platform.zip

git status --short --branch
# ## arena/f10f6e2d-market-regime-analyzer (no modified/untracked lines)
```

The 1c codeload snapshot was fetched by its exact SHA into `/tmp` and inspected without switching Git branches; GitHub's compare API reported merge base `f1602c5c95c14e4bd7795433ca6ecfd3d98794d6`, 1c ahead by 2 and behind by 12. The commands above are the exact final checks, not a reconstruction of every prior inspection command.

Read-only standard-library inspection checked 4,684 parsed input rows, 2007-09-17 to 2026-10-22, and equality of the f10 and 1c root parsed CSVs. f10 uses CRLF (4,685 line endings), 1c root LF; f10 normalized to LF hashes to 1c's `cf384a63c9137ec9b7f73d398c7ec5fc55ccdcccf89a514b824ad5341f409e59`. The unnormalized f10 attachment, snapshot and archive raw file hash is `ea6dfffb93e5eabd8b6a2f96cd40d6b3ec5c7f47f2f9e6c0cbd3ca9a5f2ac5e4`. This proves a byte/parsed-data relationship, not the vendor's data accuracy.

Illustrative temporal boundary check on f10's actual signal calendar: 500th-index refit 2014-01-17, previous observation 2014-01-16, and 20-session forward outcome ending 2014-02-13. This is an illustration of the code pattern, not a numerical reproduction of 1c study forecasts.

## Stable source references

- [1c forward targets and forecasts](https://github.com/Akshat-1234/Market-Regime-Analyzer/blob/c46541e9ab8611330489a920c46cdb00342931d5/market-regime-platform/src/regime_backtester/predictive.py)
- [1c discovery and inner scoring](https://github.com/Akshat-1234/Market-Regime-Analyzer/blob/c46541e9ab8611330489a920c46cdb00342931d5/market-regime-platform/src/regime_backtester/discovery.py)
- [1c study selection and statistics](https://github.com/Akshat-1234/Market-Regime-Analyzer/blob/c46541e9ab8611330489a920c46cdb00342931d5/market-regime-platform/src/regime_backtester/study.py)
- [1c statistical test code](https://github.com/Akshat-1234/Market-Regime-Analyzer/blob/c46541e9ab8611330489a920c46cdb00342931d5/market-regime-platform/src/regime_backtester/significance.py)
- [1c report and proposed E7](https://github.com/Akshat-1234/Market-Regime-Analyzer/blob/c46541e9ab8611330489a920c46cdb00342931d5/market-regime-platform/docs/RESEARCH_REPORT.md)
- [1c verification report](https://github.com/Akshat-1234/Market-Regime-Analyzer/blob/c46541e9ab8611330489a920c46cdb00342931d5/market-regime-platform/docs/VERIFICATION.md)
- [f10 baseline and forecast analysis](https://github.com/Akshat-1234/Market-Regime-Analyzer/blob/9bb7f92d5785462462971d0479595c1d4166868c/research/analysis/forecast.py)
- [GitHub compare](https://github.com/Akshat-1234/Market-Regime-Analyzer/compare/9bb7f92d5785462462971d0479595c1d4166868c...c46541e9ab8611330489a920c46cdb00342931d5)


# SOURCE FILE: `phase0-integration-audit/inventory/f10-9bb7f92-files.txt`

```text
.gitignore
README.md
backend/research_api.py
docs/METHODOLOGY_AND_FINDINGS.md
docs/PROGRESS.md
docs/RESEARCH_DECISIONS.md
docs/TEST_AND_VALIDATION.md
frontend/.gitignore
frontend/README.md
frontend/index.html
frontend/package-lock.json
frontend/package.json
frontend/src/App.jsx
frontend/src/main.jsx
frontend/src/research.css
frontend/vite.config.js
historical/README.md
historical/arena-market-regime-platform.zip
historical/original-project-31902b7.sha256.json
historical/original-project-31902b7.zip
requirements-research.txt
research/analysis/characterize.py
research/analysis/forecast.py
research/analysis/model_grid.py
research/data/nifty_index.csv
research/experiments/artifact_manifest.json
research/experiments/baseline_20261104/bootstrap.csv
research/experiments/baseline_20261104/config.yaml
research/experiments/baseline_20261104/daily_backtests.csv
research/experiments/baseline_20261104/daily_returns.csv
research/experiments/baseline_20261104/data_manifest.json
research/experiments/baseline_20261104/data_quality.csv
research/experiments/baseline_20261104/empirical_transitions.csv
research/experiments/baseline_20261104/equity_curves.csv
research/experiments/baseline_20261104/figures/equity_drawdown.png
research/experiments/baseline_20261104/figures/regime_probabilities.png
research/experiments/baseline_20261104/fits.csv
research/experiments/baseline_20261104/inputs/prices.csv
research/experiments/baseline_20261104/metadata.json
research/experiments/baseline_20261104/performance.csv
research/experiments/baseline_20261104/regime_strategy_sharpe.csv
research/experiments/baseline_20261104/regime_summary.csv
research/experiments/baseline_20261104/report.md
research/experiments/baseline_20261104/run_config.yaml
research/experiments/baseline_20261104/run_status.json
research/experiments/baseline_20261104/signals.csv
research/experiments/baseline_20261104/source/regime_backtester/__init__.py
research/experiments/baseline_20261104/source/regime_backtester/__main__.py
research/experiments/baseline_20261104/source/regime_backtester/attribution.py
research/experiments/baseline_20261104/source/regime_backtester/cli.py
research/experiments/baseline_20261104/source/regime_backtester/config.py
research/experiments/baseline_20261104/source/regime_backtester/data.py
research/experiments/baseline_20261104/source/regime_backtester/diagnostics.py
research/experiments/baseline_20261104/source/regime_backtester/execution.py
research/experiments/baseline_20261104/source/regime_backtester/experiment_tracking.py
research/experiments/baseline_20261104/source/regime_backtester/features.py
research/experiments/baseline_20261104/source/regime_backtester/hmm.py
research/experiments/baseline_20261104/source/regime_backtester/holdout.py
research/experiments/baseline_20261104/source/regime_backtester/metrics.py
research/experiments/baseline_20261104/source/regime_backtester/pipeline.py
research/experiments/baseline_20261104/source/regime_backtester/reporting.py
research/experiments/baseline_20261104/source/regime_backtester/research_metrics.py
research/experiments/baseline_20261104/source/regime_backtester/research_reports.py
research/experiments/baseline_20261104/source/regime_backtester/research_run.py
research/experiments/baseline_20261104/source/regime_backtester/risk_free.py
research/experiments/baseline_20261104/source/regime_backtester/strategies.py
research/experiments/baseline_20261104/source/regime_backtester/stress_testing.py
research/experiments/baseline_20261104/source/regime_backtester/validation.py
research/experiments/baseline_20261104/source/regime_backtester/walkforward.py
research/experiments/baseline_20261104/train_state_calibration.csv
research/experiments/baseline_20261104/train_transition_matrices.csv
research/experiments/characterization_20261104/analysis.json
research/experiments/forecast_20261104/config.json
research/experiments/forecast_20261104/metrics.csv
research/experiments/forecast_20261104/predictions.csv
research/experiments/forecast_20261104/simultaneous_intervals.csv
research/experiments/model_grid_20261104/config.json
research/experiments/model_grid_20261104/fits.csv
research/experiments/model_grid_20261104/fold_scores.csv
research/legacy/config/default.yaml
research/legacy/config/pca_example.yaml
research/legacy/run.py
research/legacy/src/regime_backtester/__init__.py
research/legacy/src/regime_backtester/__main__.py
research/legacy/src/regime_backtester/attribution.py
research/legacy/src/regime_backtester/cli.py
research/legacy/src/regime_backtester/config.py
research/legacy/src/regime_backtester/data.py
research/legacy/src/regime_backtester/diagnostics.py
research/legacy/src/regime_backtester/execution.py
research/legacy/src/regime_backtester/experiment_tracking.py
research/legacy/src/regime_backtester/features.py
research/legacy/src/regime_backtester/hmm.py
research/legacy/src/regime_backtester/holdout.py
research/legacy/src/regime_backtester/metrics.py
research/legacy/src/regime_backtester/pipeline.py
research/legacy/src/regime_backtester/reporting.py
research/legacy/src/regime_backtester/research_metrics.py
research/legacy/src/regime_backtester/research_reports.py
research/legacy/src/regime_backtester/research_run.py
research/legacy/src/regime_backtester/risk_free.py
research/legacy/src/regime_backtester/strategies.py
research/legacy/src/regime_backtester/stress_testing.py
research/legacy/src/regime_backtester/validation.py
research/legacy/src/regime_backtester/walkforward.py
tests/test_historical_archive.py
tests/test_research_platform.py
```


# SOURCE FILE: `phase0-integration-audit/inventory/f10-commit-history.tsv`

```tsv
9bb7f92d5785462462971d0479595c1d4166868c	2026-11-04T19:30:30Z	cleanup: archive original research and remove unused legacy app
02af0256aa55db2170e6add71ceb9ceefbbe6e04	2026-11-04T19:25:27Z	fix: provide project download through preview
a3fc6a55211864232667f81f63068d97a44fbc3c	2026-11-04T19:22:28Z	fix: serve research dashboard on port 8000
d98ca5d4d7987e63ba442186d543987a9cbc18d0	2026-11-04T18:23:06Z	docs: report empirical findings and incomplete validation
62c5316064cfe7b48b391afbf17a68542aa59f7f	2026-11-04T18:23:06Z	tests: verify temporal integrity and artifact provenance
e60016789dac9d75faa8da6d1b77a5beef7c4844	2026-11-04T18:22:22Z	frontend: connect research dashboard to traceable experiments
3545b63b69b4aee688ff1cfbe3469b595b6a3d1e	2026-11-04T18:22:22Z	analysis: add filtered state diagnostics and walk-forward experiments
12758159cc5412282d733d794f8400e29d54a43b	2026-11-04T18:12:05Z	research: reproduce and preserve delayed historical baseline
0951197dee09f7357c2224cb59caef9dbb6173b1	2026-11-04T18:09:45Z	research: inventory prior work and document evidence gaps
31902b7cdec9409f805784d9634d3bfd5f25c03f	2026-10-31T06:36:08Z	Merge pull request #2 from Akshat-1234/add-quantlab
afd3eeb1527e39d7d89cee60d4ab141c446f022b	2026-10-31T06:35:22Z	New Changes
f1602c5c95c14e4bd7795433ca6ecfd3d98794d6	2026-10-30T09:52:29Z	Add files via upload
0aa9dae993c275cbca712e31a4990f34df449906	2026-10-29T18:13:01Z	updated one
f7d98f81baed62ed9f61524d73d480f59131d89e	2026-10-24T05:57:45Z	Feature timeline correction and strategy OS testing
640d43cdd644d8ec5ad8da28d27f19416ca0dcb4	2026-10-22T12:43:14Z	Merge pull request #1 from Akshat-1234/add-quantlab
41d62f3b28d97cf8018e1ed25a3b86c08d9cac84	2026-10-22T12:42:27Z	Merge Market Regime Analyzer with QuantLab
3678f1fc62abfcbcf5079129e3694add03c1f1ee	2026-10-22T12:33:30Z	Initial commit: Complete QuantLab project
8c9a9eadf8c569b799baaeb94d25d7d1db7aa753	2026-10-20T12:56:45Z	Backtester made
7869f86a230f0d0fdd8cccfc668bd52e1537805c	2026-10-17T18:38:34Z	Merge branch 'main' of https://github.com/Akshat-1234/Market-Regime-Analyzer
5797be61b3e6ca66f1a372560dec6f04bb592c0b	2026-10-17T18:38:30Z	Model and Strategy upload
842d86515041fae6ad3c2329db54187c26e4344f	2026-10-17T14:57:28Z	Delete Data_Exploration.ipynb
ee310846eab492b8ef4917e52229fc3a10e882a3	2026-10-17T13:33:08Z	INITIAL COMMIT
```


# SOURCE FILE: `phase0-integration-audit/inventory/1c-c46541e-files.txt`

```text
.gitignore
Backtester_evaluation.py
Feature_Selection.ipynb
README.md
Strategies.ipynb
Strategy_Backtest.ipynb
Strategy_Backtest_Ready.ipynb
backend/backtest.py
backend/main.py
backend/nifty_index.csv
backtest_20day_momentum.csv
backtest_5day_mean_reversion.csv
backtest_buy_and_hold.csv
backtest_hmm.csv
backtest_hmm_risk_rule.csv
backtest_mean_reversion_5d.csv
backtest_momentum_20d.csv
backtester.py
causal_test_regimes.csv
data.ipynb
feature_means.csv
feature_standard_deviations.csv
frontend/.env.example
frontend/.gitignore
frontend/README.md
frontend/index.html
frontend/package-lock.json
frontend/package.json
frontend/src/App.jsx
frontend/src/api/client.js
frontend/src/components/backtest/BacktestForm.jsx
frontend/src/components/backtest/DataStrip.jsx
frontend/src/components/backtest/EquityChart.jsx
frontend/src/components/backtest/EquityPanel.jsx
frontend/src/components/backtest/MetricsGrid.jsx
frontend/src/components/common/PageHeading.jsx
frontend/src/components/common/Panel.jsx
frontend/src/components/layout/Footer.jsx
frontend/src/components/layout/Sidebar.jsx
frontend/src/components/layout/Topbar.jsx
frontend/src/config.js
frontend/src/context/BacktestContext.jsx
frontend/src/main.jsx
frontend/src/pages/DataExplorer.jsx
frontend/src/pages/NotFound.jsx
frontend/src/pages/Performance.jsx
frontend/src/pages/StrategyLab.jsx
frontend/src/styles/components.css
frontend/src/styles/global.css
frontend/src/styles/layout.css
frontend/src/utils/format.js
frontend/src/utils/normalise.js
frontend/vite.config.js
hmm_model.joblib
market-regime-platform.zip
market-regime-platform/.github/workflows/tests.yml
market-regime-platform/.gitignore
market-regime-platform/MANIFEST.sha256
market-regime-platform/Makefile
market-regime-platform/NIFTY_RESULTS.md
market-regime-platform/README.md
market-regime-platform/backend/__init__.py
market-regime-platform/backend/app.py
market-regime-platform/config/default.yaml
market-regime-platform/config/pca_example.yaml
market-regime-platform/data/raw/.gitkeep
market-regime-platform/data/raw/README.md
market-regime-platform/data/reference/README.md
market-regime-platform/data/reference/rbi_tbill_91_yields.csv
market-regime-platform/data/sample/README.md
market-regime-platform/data/sample/synthetic_ohlc.csv
market-regime-platform/docs/BASELINE_AUDIT.md
market-regime-platform/docs/DATA.md
market-regime-platform/docs/METHODOLOGY.md
market-regime-platform/docs/ORIGINAL_BACKTESTER_README.md
market-regime-platform/docs/ORIGINAL_MAKEFILE.txt
market-regime-platform/docs/PLATFORM_GUIDE.md
market-regime-platform/docs/RESEARCH_REPORT.md
market-regime-platform/docs/RUNS_AND_PROVENANCE.md
market-regime-platform/docs/TEST_REPORT.md
market-regime-platform/docs/VERIFICATION.md
market-regime-platform/examples/synthetic_run/bootstrap.csv
market-regime-platform/examples/synthetic_run/daily_backtests.csv
market-regime-platform/examples/synthetic_run/daily_returns.csv
market-regime-platform/examples/synthetic_run/data_quality.csv
market-regime-platform/examples/synthetic_run/empirical_transitions.csv
market-regime-platform/examples/synthetic_run/equity_curves.csv
market-regime-platform/examples/synthetic_run/figures/equity_drawdown.png
market-regime-platform/examples/synthetic_run/figures/regime_probabilities.png
market-regime-platform/examples/synthetic_run/fits.csv
market-regime-platform/examples/synthetic_run/metadata.json
market-regime-platform/examples/synthetic_run/performance.csv
market-regime-platform/examples/synthetic_run/regime_strategy_sharpe.csv
market-regime-platform/examples/synthetic_run/regime_summary.csv
market-regime-platform/examples/synthetic_run/report.md
market-regime-platform/examples/synthetic_run/run_config.yaml
market-regime-platform/examples/synthetic_run/signals.csv
market-regime-platform/examples/synthetic_run/train_state_calibration.csv
market-regime-platform/examples/synthetic_run/train_transition_matrices.csv
market-regime-platform/frontend/e2e/platform.spec.ts
market-regime-platform/frontend/index.html
market-regime-platform/frontend/package-lock.json
market-regime-platform/frontend/package.json
market-regime-platform/frontend/playwright.config.ts
market-regime-platform/frontend/src/App.tsx
market-regime-platform/frontend/src/api.ts
market-regime-platform/frontend/src/components/Charts.tsx
market-regime-platform/frontend/src/components/Common.tsx
market-regime-platform/frontend/src/components/RunComparison.tsx
market-regime-platform/frontend/src/components/RunDialog.tsx
market-regime-platform/frontend/src/context.ts
market-regime-platform/frontend/src/main.tsx
market-regime-platform/frontend/src/pages/DataQuality.tsx
market-regime-platform/frontend/src/pages/Overview.tsx
market-regime-platform/frontend/src/pages/RegimeExplorer.tsx
market-regime-platform/frontend/src/pages/StrategyCompare.tsx
market-regime-platform/frontend/src/pages/Validation.tsx
market-regime-platform/frontend/src/styles.css
market-regime-platform/frontend/src/types.ts
market-regime-platform/frontend/src/utils.ts
market-regime-platform/frontend/tests/components.test.tsx
market-regime-platform/frontend/tests/setup.ts
market-regime-platform/frontend/tests/utils.test.ts
market-regime-platform/frontend/tsconfig.json
market-regime-platform/frontend/vite.config.ts
market-regime-platform/frontend/vitest.config.ts
market-regime-platform/pyproject.toml
market-regime-platform/reports/EXECUTIVE_SUMMARY.md
market-regime-platform/requirements-research-locked.txt
market-regime-platform/research_outputs/LATEST
market-regime-platform/research_outputs/study_20261030T102052Z/EXPERIMENT_REGISTER.csv
market-regime-platform/research_outputs/study_20261030T102052Z/allocation/matched_controls.csv
market-regime-platform/research_outputs/study_20261030T102052Z/allocation/matched_controls_summary.json
market-regime-platform/research_outputs/study_20261030T102052Z/allocation/paired_bootstrap.csv
market-regime-platform/research_outputs/study_20261030T102052Z/allocation/performance.csv
market-regime-platform/research_outputs/study_20261030T102052Z/allocation/reality_check.json
market-regime-platform/research_outputs/study_20261030T102052Z/allocation/reality_check_ranking.csv
market-regime-platform/research_outputs/study_20261030T102052Z/audit/baseline_probability_diagnostics.json
market-regime-platform/research_outputs/study_20261030T102052Z/audit/data_summary.json
market-regime-platform/research_outputs/study_20261030T102052Z/audit/execution_timing_sensitivity.csv
market-regime-platform/research_outputs/study_20261030T102052Z/audit/feature_correlations.csv
market-regime-platform/research_outputs/study_20261030T102052Z/audit/feature_redundancy_top_pairs.csv
market-regime-platform/research_outputs/study_20261030T102052Z/audit/feature_vif.csv
market-regime-platform/research_outputs/study_20261030T102052Z/discovery/seed_stability.csv
market-regime-platform/research_outputs/study_20261030T102052Z/discovery/selection.json
market-regime-platform/research_outputs/study_20261030T102052Z/discovery/state_alignment.csv
market-regime-platform/research_outputs/study_20261030T102052Z/discovery/state_count_folds.csv
market-regime-platform/research_outputs/study_20261030T102052Z/discovery/state_count_sweep.csv
market-regime-platform/research_outputs/study_20261030T102052Z/emissions/duration_diagnostics.csv
market-regime-platform/research_outputs/study_20261030T102052Z/emissions/emission_comparison.csv
market-regime-platform/research_outputs/study_20261030T102052Z/emissions/selection.json
market-regime-platform/research_outputs/study_20261030T102052Z/features/feature_ablation.csv
market-regime-platform/research_outputs/study_20261030T102052Z/features/selection.json
market-regime-platform/research_outputs/study_20261030T102052Z/manifest.json
market-regime-platform/research_outputs/study_20261030T102052Z/predictive/entropy_conditioning.csv
market-regime-platform/research_outputs/study_20261030T102052Z/predictive/expanding_oos.csv
market-regime-platform/research_outputs/study_20261030T102052Z/predictive/hac_regressions.csv
market-regime-platform/research_outputs/study_20261030T102052Z/predictive/predictive_summary.json
market-regime-platform/research_outputs/study_20261030T102052Z/predictive/state_forward_characteristics.csv
market-regime-platform/research_outputs/study_20261030T104848Z/EXPERIMENT_REGISTER.csv
market-regime-platform/research_outputs/study_20261030T104848Z/allocation/matched_controls.csv
market-regime-platform/research_outputs/study_20261030T104848Z/allocation/matched_controls_summary.json
market-regime-platform/research_outputs/study_20261030T104848Z/allocation/paired_bootstrap.csv
market-regime-platform/research_outputs/study_20261030T104848Z/allocation/performance.csv
market-regime-platform/research_outputs/study_20261030T104848Z/allocation/reality_check.json
market-regime-platform/research_outputs/study_20261030T104848Z/allocation/reality_check_ranking.csv
market-regime-platform/research_outputs/study_20261030T104848Z/audit/baseline_probability_diagnostics.json
market-regime-platform/research_outputs/study_20261030T104848Z/audit/data_summary.json
market-regime-platform/research_outputs/study_20261030T104848Z/audit/execution_timing_sensitivity.csv
market-regime-platform/research_outputs/study_20261030T104848Z/audit/feature_correlations.csv
market-regime-platform/research_outputs/study_20261030T104848Z/audit/feature_redundancy_top_pairs.csv
market-regime-platform/research_outputs/study_20261030T104848Z/audit/feature_vif.csv
market-regime-platform/research_outputs/study_20261030T104848Z/discovery/seed_stability.csv
market-regime-platform/research_outputs/study_20261030T104848Z/discovery/selection.json
market-regime-platform/research_outputs/study_20261030T104848Z/discovery/state_alignment.csv
market-regime-platform/research_outputs/study_20261030T104848Z/discovery/state_count_folds.csv
market-regime-platform/research_outputs/study_20261030T104848Z/discovery/state_count_sweep.csv
market-regime-platform/research_outputs/study_20261030T104848Z/emissions/duration_diagnostics.csv
market-regime-platform/research_outputs/study_20261030T104848Z/emissions/emission_comparison.csv
market-regime-platform/research_outputs/study_20261030T104848Z/emissions/selection.json
market-regime-platform/research_outputs/study_20261030T104848Z/features/feature_ablation.csv
market-regime-platform/research_outputs/study_20261030T104848Z/features/selection.json
market-regime-platform/research_outputs/study_20261030T104848Z/manifest.json
market-regime-platform/research_outputs/study_20261030T104848Z/predictive/entropy_conditioning.csv
market-regime-platform/research_outputs/study_20261030T104848Z/predictive/expanding_oos.csv
market-regime-platform/research_outputs/study_20261030T104848Z/predictive/hac_regressions.csv
market-regime-platform/research_outputs/study_20261030T104848Z/predictive/predictive_summary.json
market-regime-platform/research_outputs/study_20261030T104848Z/predictive/state_forward_characteristics.csv
market-regime-platform/research_outputs/study_20261030T111521Z/EXPERIMENT_REGISTER.csv
market-regime-platform/research_outputs/study_20261030T111521Z/allocation/daily_returns.csv
market-regime-platform/research_outputs/study_20261030T111521Z/allocation/matched_controls.csv
market-regime-platform/research_outputs/study_20261030T111521Z/allocation/matched_controls_summary.json
market-regime-platform/research_outputs/study_20261030T111521Z/allocation/paired_bootstrap.csv
market-regime-platform/research_outputs/study_20261030T111521Z/allocation/performance.csv
market-regime-platform/research_outputs/study_20261030T111521Z/allocation/reality_check.json
market-regime-platform/research_outputs/study_20261030T111521Z/allocation/reality_check_ranking.csv
market-regime-platform/research_outputs/study_20261030T111521Z/audit/baseline_probability_diagnostics.json
market-regime-platform/research_outputs/study_20261030T111521Z/audit/data_summary.json
market-regime-platform/research_outputs/study_20261030T111521Z/audit/execution_timing_sensitivity.csv
market-regime-platform/research_outputs/study_20261030T111521Z/audit/feature_correlations.csv
market-regime-platform/research_outputs/study_20261030T111521Z/audit/feature_redundancy_top_pairs.csv
market-regime-platform/research_outputs/study_20261030T111521Z/audit/feature_vif.csv
market-regime-platform/research_outputs/study_20261030T111521Z/discovery/seed_stability.csv
market-regime-platform/research_outputs/study_20261030T111521Z/discovery/selection.json
market-regime-platform/research_outputs/study_20261030T111521Z/discovery/state_alignment.csv
market-regime-platform/research_outputs/study_20261030T111521Z/discovery/state_count_folds.csv
market-regime-platform/research_outputs/study_20261030T111521Z/discovery/state_count_sweep.csv
market-regime-platform/research_outputs/study_20261030T111521Z/emissions/duration_diagnostics.csv
market-regime-platform/research_outputs/study_20261030T111521Z/emissions/emission_comparison.csv
market-regime-platform/research_outputs/study_20261030T111521Z/emissions/selection.json
market-regime-platform/research_outputs/study_20261030T111521Z/features/feature_ablation.csv
market-regime-platform/research_outputs/study_20261030T111521Z/features/selection.json
market-regime-platform/research_outputs/study_20261030T111521Z/manifest.json
market-regime-platform/research_outputs/study_20261030T111521Z/predictive/entropy_conditioning.csv
market-regime-platform/research_outputs/study_20261030T111521Z/predictive/expanding_oos.csv
market-regime-platform/research_outputs/study_20261030T111521Z/predictive/hac_regressions.csv
market-regime-platform/research_outputs/study_20261030T111521Z/predictive/predictive_summary.json
market-regime-platform/research_outputs/study_20261030T111521Z/predictive/state_forward_characteristics.csv
market-regime-platform/results/.gitkeep
market-regime-platform/run.py
market-regime-platform/run_dashboard.py
market-regime-platform/src/regime_backtester/__init__.py
market-regime-platform/src/regime_backtester/__main__.py
market-regime-platform/src/regime_backtester/allocation.py
market-regime-platform/src/regime_backtester/attribution.py
market-regime-platform/src/regime_backtester/cli.py
market-regime-platform/src/regime_backtester/config.py
market-regime-platform/src/regime_backtester/data.py
market-regime-platform/src/regime_backtester/diagnostics.py
market-regime-platform/src/regime_backtester/discovery.py
market-regime-platform/src/regime_backtester/emhmm.py
market-regime-platform/src/regime_backtester/execution.py
market-regime-platform/src/regime_backtester/experiment_tracking.py
market-regime-platform/src/regime_backtester/features.py
market-regime-platform/src/regime_backtester/hmm.py
market-regime-platform/src/regime_backtester/holdout.py
market-regime-platform/src/regime_backtester/metrics.py
market-regime-platform/src/regime_backtester/pipeline.py
market-regime-platform/src/regime_backtester/predictive.py
market-regime-platform/src/regime_backtester/reporting.py
market-regime-platform/src/regime_backtester/research_metrics.py
market-regime-platform/src/regime_backtester/research_reports.py
market-regime-platform/src/regime_backtester/research_run.py
market-regime-platform/src/regime_backtester/risk_free.py
market-regime-platform/src/regime_backtester/significance.py
market-regime-platform/src/regime_backtester/strategies.py
market-regime-platform/src/regime_backtester/stress_testing.py
market-regime-platform/src/regime_backtester/study.py
market-regime-platform/src/regime_backtester/validation.py
market-regime-platform/src/regime_backtester/walkforward.py
market-regime-platform/tests/conftest.py
market-regime-platform/tests/manual_job_e2e.py
market-regime-platform/tests/test_api.py
market-regime-platform/tests/test_config_data.py
market-regime-platform/tests/test_execution_metrics.py
market-regime-platform/tests/test_hmm.py
market-regime-platform/tests/test_pipeline_causality.py
market-regime-platform/tests/test_research_discovery.py
market-regime-platform/tests/test_research_extensions.py
market-regime-platform/validation/independent_nifty/README.md
market-regime-platform/validation/independent_nifty/data_quality.csv
market-regime-platform/validation/independent_nifty/metadata.json
market-regime-platform/validation/independent_nifty/one_session_delay_bootstrap.csv
market-regime-platform/validation/independent_nifty/one_session_delay_performance.csv
market-regime-platform/validation/independent_nifty/regime_summary.csv
market-regime-platform/validation/independent_nifty/run_config.yaml
market-regime-platform/validation/independent_nifty/same_close_bootstrap.csv
market-regime-platform/validation/independent_nifty/same_close_performance.csv
model.ipynb
nifty_index.csv
run_backtest.py
strategy_backtest_summary.csv
tempCodeRunnerFile.py
test_df
test_df.csv
test_strategy_signals.csv
train_df
train_df.csv
```


# SOURCE FILE: `phase0-integration-audit/inventory/1c-commit-history.tsv`

```tsv
c46541e9ab8611330489a920c46cdb00342931d5	2026-10-30T11:41:39Z	Research report: correct paired-comparison units, add headline results and archived-control finding
efc504c0a5608562ee5b30373caf0f47f360dc47	2026-10-30T11:41:24Z	Add independent research programme: report, verification, research engine and study artifacts
f1602c5c95c14e4bd7795433ca6ecfd3d98794d6	2026-10-30T09:52:29Z	Add files via upload
f7d98f81baed62ed9f61524d73d480f59131d89e	2026-10-24T05:57:45Z	Feature timeline correction and strategy OS testing
640d43cdd644d8ec5ad8da28d27f19416ca0dcb4	2026-10-22T12:43:14Z	Merge pull request #1 from Akshat-1234/add-quantlab
41d62f3b28d97cf8018e1ed25a3b86c08d9cac84	2026-10-22T12:42:27Z	Merge Market Regime Analyzer with QuantLab
3678f1fc62abfcbcf5079129e3694add03c1f1ee	2026-10-22T12:33:30Z	Initial commit: Complete QuantLab project
8c9a9eadf8c569b799baaeb94d25d7d1db7aa753	2026-10-20T12:56:45Z	Backtester made
7869f86a230f0d0fdd8cccfc668bd52e1537805c	2026-10-17T18:38:34Z	Merge branch 'main' of https://github.com/Akshat-1234/Market-Regime-Analyzer
5797be61b3e6ca66f1a372560dec6f04bb592c0b	2026-10-17T18:38:30Z	Model and Strategy upload
842d86515041fae6ad3c2329db54187c26e4344f	2026-10-17T14:57:28Z	Delete Data_Exploration.ipynb
ee310846eab492b8ef4917e52229fc3a10e882a3	2026-10-17T13:33:08Z	INITIAL COMMIT
```
