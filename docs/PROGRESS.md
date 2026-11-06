# Progress record

## Phase 0 — audit
Completed: source and historical experiment inventory, dataset hash comparison, risks, unresolved provenance. See RESEARCH_DECISIONS.md. Archive remains intact.

## Phase 1 — reproduction
Executed the archived `run.py` from the extracted ZIP on the supplied CSV with `--start 2012-01-01 --execution-delay 1 --bootstrap-samples 1000`. Produced `research/experiments/baseline_20261104`; configuration, fit metadata, inputs and source snapshots, daily outcomes and signals are retained. This new directory is separate from the original archive. All headline metrics reproduce at displayed precision; CSV signal bytes differ (`92b569...` vs archived `e3e17a...`); observed metric differences were floating point at ~1e-14. Do not claim byte-for-byte reproduction. The version manifest accompanies the run. The previous full main attribution run is incomplete in the archive, so this reproduction is of the original delayed baseline, not that missing main run.

Source copied without modification to `research/legacy` to facilitate independent reproduction. This is a historical four-model 2/3-state ensemble, not proof that it is the optimal specification. Future research and product surface must clearly name the run and keep retrospective vs prospective distinct.

## Phases 2–4 — corrected research surface and exploratory model investigation
Added `research/analysis/characterize.py`, which consumes saved forward-filtered OOS probabilities, calculates posterior-weighted diagnostics, within-refit episodes and empirical transitions, and separates overlapping forward returns as descriptive. Saved the immutable `characterization_20261104` output. Added `model_grid.py` with joint 2/3/4-state, RV/RVD, diagonal/full, 2-seed expanding annual comparisons, rejected-fit records and held-out density; saved `model_grid_20261104`. No final model selected. The source already enforces the signal/next-close/next-return timing; the root teammate's selector is not promoted. See METHODOLOGY_AND_FINDINGS.md for results and limitations.

## Phase 5 — partial
Baseline allocation was reproduced against fixed and observable controls. Added `forecast_20261104`: four horizons, chronological indicator-only and regime-augmented ridge models, expanding-mean benchmarks and simultaneous stationary-bootstrap intervals. Results are exploratory and negative in aggregate; see the methodology report. The requested exact E7 protocol/specifications are absent, and E7, comprehensive forecasting, fully matched controls, and adaptive strategy selection remain incomplete. Forward outcomes are descriptive only. A prospective freeze is not valid with the current source hash. Do not treat this phase as complete.

## Phase 6 — product surface
Added read-only `backend/research_api.py` and replaced the active frontend entry point with four research sections tied to saved artifacts, including provenance checks, state comparisons, grid results and historical strategy metrics. Legacy frontend files remain in Git for historical reference but are not loaded. The legacy backend's unrelated routes are not used by the new UI.

Integrated the completed Task 4 nested discovery as a fifth dashboard section without rerunning research or changing frozen outputs. The read-only API verifies the recovery and analysis manifest inventories and serves compact selected-model, occupancy, alignment, stability and reproducibility records. Navigation and explanatory text distinguish the original three-state/15-refit baseline, Task 4's five-component/14-fold close-only RV experiment, and baseline-only strategy results.

Final delivery pass: replaced the light surface with a restrained responsive dark financial-research theme using system fonts. Corrected the dated local-rank and four-strategy account-equity charts to use saved observations with explicit sampling; added accessible transition/occupancy heatmaps, subsequent-pair alignment bars, zero-referenced Sharpe and MSE-improvement intervals, and exact evidence tables. Candidate-rank margins and near-tie counts are derived after Task 4 analysis-manifest verification rather than hardcoded. Baseline and Task 4 loading/error states are independent, artifacts are grouped by purpose, and the absent project-download feature was removed.

## Phase 7 — verification completed for dashboard; research remains partial, no release
Tests, HTTP smoke checks, production build and real Chromium browser checks are recorded in `docs/TEST_AND_VALIDATION.md`. All five sections were checked at 1440, 1280, 768 and 390 pixels, including overflow, navigation, charts, tables, keyboard focus and forced independent API failures. A release tag is intentionally not created: E7, comprehensive forecasting, matched controls, full inference and a validated clean prospective holdout remain incomplete. Cross-browser, real-device and formal accessibility audits also remain open. This is a work-in-progress, not a complete research release.

## Repository cleanup

The original tracked project at commit `31902b7` was archived, hash-verified, and removed from the active tree; the unchanged later Arena archive was moved to `historical/`. The active frontend no longer contains disconnected legacy pages. See `historical/README.md` for the exact preservation and recovery procedure. Research experiments, inputs and provenance snapshots remain in place.
