# Run inventory and provenance

## Preserved original work

- `results/nifty_2012_delayed/` and `results/nifty_2012_same_close/` are the original completed results delivered before the platform expansion. The original dataset is `data/raw/nifty_index.csv`. Its SHA-256 is `ea6dfffb93e5eabd8b6a2f96cd40d6b3ec5c7f47f2f9e6c0cbd3ca9a5f2ac5e4`.
- Before modification, the delayed experiment was rerun with identical performance fields at saved CSV precision and byte-identical `signals.csv`; see [BASELINE_AUDIT.md](BASELINE_AUDIT.md).
- The prior reconstructed four-model engine and all strategies remain. The original 14-model repository/config was not available, so its claimed results cannot be exactly reproduced. The prior README and Makefile are saved as `ORIGINAL_BACKTESTER_README.md` and `ORIGINAL_MAKEFILE.txt`.
- `examples/synthetic_run/` is synthetic; `validation/independent_nifty/` contains previously generated aggregate-only independent validation. The external third-party daily input is not redistributed because its licence was not established.

## Complete platform runs

| Run ID | Purpose | Control history | Simulations per control | Bootstrap | Notes |
| --- | --- | --- | ---: | ---: | --- |
| `run_20261030_080824_12346d` | Preliminary full-history sensitivity | All prior observations | 200 | 1,000 | Median matched HMM-leg KS 0.310; control method differs from main run |
| `run_20261030_081436_12ea5b` | Main rolling-history attribution | Most recent 63 prior sessions | 200 | 1,000 | Lookback selected after preliminary matching inspection; median matched KS 0.076 |

Both use the same input, 2012 start, one-session execution delay, 10 bps one-way, 6.5% fixed cash, seed 1701 and 20-session attribution blocks. Their underlying baseline strategy metrics are identical; their control algorithms and core source hashes differ. Treat direct control comparisons as sensitivity analyses, not matched confirmatory trials. The dashboard compares provenance and reports differences.

Each run contains:

- `run_status.json` — unique identity, completion/error state, seeds, control settings, warnings, hashes.
- `config.yaml`, `run_config.yaml`, `metadata.json`, `data_manifest.json` — assumptions, dependency versions, data/code hashes, date ranges and reference provenance.
- `inputs/prices.csv`, `inputs/rbi_tbill_91_yields.csv` — byte-identical source snapshots; `source/regime_backtester/*.py` — the core Python source snapshot used by that run.
- `signals.csv`, `daily_returns.csv`, `daily_backtests.csv`, `performance.csv`, `equity_curves.csv` — decision signals, realized return/turnover/cost series and aggregate metrics.
- `attribution.csv`, `attribution_simulations.csv`, `attribution_bootstrap.csv`, `attribution_periods.csv`, `attribution_control_daily_means.csv` — controls, per-seed diagnostics, paired intervals, stress breakdown and mean control returns.
- `fold_metrics.csv`, `fold_aggregate.csv`, `stress_periods.csv`, `holdout_retrospective.csv`, `holdout_freeze.json`, `cash_sensitivity.csv`, `rbi_aligned_rates.csv` — validation, freeze and cash assumptions.
- `fits.csv`, `train_state_calibration.csv`, `train_transition_matrices.csv`, `model_occupancy.csv`, `state_allocation_diagnostics.csv`, `state_stability.csv`, `state_cross_model_matching.csv` — accepted fits, train state allocation/transition and heuristic matching.
- `data_quality_summary.json`, `data_quality_annual.csv`, `data_quality_flags.csv`, `data_quality_weekday_candidates.csv`, `pca_variance.csv`, `pca_loadings.csv`, `feature_correlations.csv`, `feature_distributions.csv` — auditable input and training-only exploratory diagnostics.
- `reports/`, `figures/`, `logs/research.log` — research writeups, actual plots and execution log.

Completed comprehensive runs are written to a new uniquely named directory, never overlaid on existing results. Failed runs keep status/log information rather than disappearing. The old `run.py` command similarly refuses to overwrite a nonempty explicit output and defaults to a unique directory; its legacy artifact set is smaller than the comprehensive research command. The prospective evaluator creates its own run after verifying the frozen data, source and configuration.

The run manifests record the original machine's absolute paths. Those paths are not required after moving the project: use the copies under `inputs/` and `source/`. The RBI series is attributed in `data/reference/README.md`; its cut-off yield is an imperfect historical cash proxy. Version pins in `requirements-research-locked.txt` correspond to the research environment, although platform/BLAS differences may still change numerical optimization.
