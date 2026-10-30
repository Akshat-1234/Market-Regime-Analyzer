# Research platform guide

## Scope and interpretation

This project evaluates one user-supplied NIFTY index-price history, not a diversified set of tradable instruments. The core question is the *incremental contribution* of HMM information, not whether any single in-sample winner exists. Earlier model searches and 2023–2026 examination make this exploratory. The original unavailable 14-model code/configuration is not reconstructed, and the independently sourced daily third-party snapshot is not redistributed.

### Timing and accounting

Features are trailing. Each expanding HMM refit uses observations strictly before its signal block. Scaling, state-volatility mapping and optional PCA are fitted within training only; test probabilities are forward-filtered rather than backward-smoothed. Model states are ranked by fitted training volatility, but an equal rank across refits does not establish identical economic meaning.

The original baseline HMM strategy averages four model exposures; HMM + Trend is the arithmetic blend `0.5 * HMM + 0.5 * Trend`, not multiplication. The delayed case uses a decision at close `t`, a fill at the next session's close, then the following close-to-close return. The separate default legacy same-close mode is optimistic. Neither claims next-open fills. Accounting is self-financing long/cash with drift-aware turnover, proportional one-way costs including entry, daily cash accrual, and no forced terminal sale. No dividends, taxes, index-tracking error, financing or impact are modeled.

### Attribution controls

All strategies share the same return calendar, cost assumption, initial capital, cash convention and lag. Each causal control resamples the *HMM exposure output*, rather than retrospectively shuffling state labels with future knowledge:

1. **Past-only shuffled:** independent draws with replacement from earlier observed exposures.
2. **Past-only block shuffled:** contiguous historical blocks that were already complete at the draw date.
3. **Exposure/turnover-approximate random:** redraw/hold probability estimated using only historical variation and the same prior-only exposure pool.

The first decision initializes at the current real HMM exposure. The main experiment draws from a 63-session history; the earlier experiment samples the whole prior history. The 63-session choice was made **after** inspecting preliminary full-history matching, not preregistered. This reduces any confirmatory force, even though both runs and their snapshots are preserved. A short lookback can also preserve local exposure patterns and is not a perfect null for all regime information.

Each simulation records seed, net metrics, exposure quantiles, HMM-leg KS distance, turnover, cost and a separately labeled common-fee-schedule diagnostic. That equal-fee result applies a fee schedule based on the real strategy to zero-cost control returns; it is an approximate counterfactual, not a tradable backtest. The controls are only approximately matched. Sampled distribution percentiles and the fraction of controls beaten are descriptive, not formal p-values.

Bootstrap draws are paired across the same market dates in 20-session blocks. Real HMM + Trend is contrasted with Trend and the **daily equal-weight mean return of each group of simulations**. These intervals reflect resampling uncertainty under the selected setup, not uncertainty against an individual random path and not corrections for multiple past experiments. An interval crossing zero does not prove equivalence. The two original reports also include comparisons with Buy & Hold and Vol Target.

### Walk-forward, stress and holdout

`fold_metrics.csv` records each primary-model signal block's train and test boundaries, inherited portfolio returns, costs and metrics. Delay can put a fold's final earned return in the next calendar year. Aggregate metrics are recalculated from the concatenated daily OOS return series; annual ratios are never averaged. Drawdowns rebase to one at each analysis window, with no artificial entry or exit.

Stress windows are calendar 2013, calendar 2015–2016, calendar 2020 (crash and recovery), and calendar 2022. The continuous portfolio is sliced without forced liquidation. Recovery is measured from window-local peak to recovery and right-censored at the window end. Short-window annualized ratios can be unstable.

The retrospective 2023–2026 slice was already inspected; it is **not** an untouched holdout. `holdout_freeze.json` records the freeze timestamp, exchange date, original data hash, core source hash, frozen config and the strictly-later decision boundary. The main run's boundary is 2026-10-30. No qualifying post-freeze data have been evaluated.

Once an extended CSV genuinely contains later observations, with the original rows unchanged, use:

```bash
python -m regime_backtester.holdout \
  --freeze runs/run_20261030_081436_12ea5b/holdout_freeze.json \
  --original data/raw/nifty_index.csv \
  --extended path/to/extended_prices.csv --runs-dir runs
```

In PowerShell enter it on one line or use backticks. The evaluator rejects a changed historical prefix, wrong original hash, changed frozen configuration, changed core source, or an extension with no post-boundary observation. It scores only returns whose **decision date** is strictly after the boundary, and reports pending if there are insufficient earned returns. Scheduled refits may use earlier data under the fixed rules. As of delivery the latest core matches the main freeze; to reproduce the earlier run's freeze use its own `source/regime_backtester/` snapshot in an isolated copy and pass `--runs-dir` explicitly. Environment/library differences remain a reproducibility risk.

### Risk-free rate and Sortino

The original fixed **6.5% annual** cash and excess-return benchmark is retained as baseline, not asserted to be constant historically. Separate replayed sensitivities cover 0%, 6.5%, and a strictly prior auction-date RBI 91-day cutoff yield proxy. The source and licensing attribution are in [data/reference/README.md](../data/reference/README.md). Auction yields are not actual daily cash returns; future rates are never used and the carry limit is 31 days. The supplied reference has 19 signal dates older than 14 days and a 29-day maximum age.

Sortino's daily downside denominator is `sqrt(mean(min(excess_return, 0)^2))` across **all** observations, scaled annually; positive excess-return days contribute zero, not missing values. Sharpe uses sample standard deviation; drawdown is a positive magnitude. Rates and return windows are aligned by actual execution/return dates.

### Diagnostics

- Data checks include raw duplicate/missing values, invalid OHLC, extreme/zero closes, gaps and intraday/overnight relationships. Weekday gaps are *candidates* only; exchange holidays are not misclassified as confirmed missing sessions. An Open near prior Close may be legitimate, but the early pattern merits vendor investigation.
- PCA, loadings and feature correlations use the 16-feature pre-first-OOS training data only, and are descriptive. The default HMM remains unchanged. Inputs lacking enough OHLC data report PCA unavailable.
- Fit checks reject invalid covariance, failure to converge and too-small training occupancy; no acceptable seed causes failure. `rejected_seed_fits` in `model_diagnostics.csv` counts model/fold fit rows with at least one rejected seed, **not** individual seed attempts. Calibrations and identical-exposure pair checks are exported. State matching uses a Hungarian assignment on log-volatility distance; unmatched states are omitted and this is not proof of identity.
- Source data and core Python files are copied into each comprehensive run along with hashes, config, status, dependency versions, logs and reports. Absolute original paths in metadata reflect the machine that created the run; use the bundled `inputs/prices.csv` snapshot after moving the project.

## Dashboard and API

The five primary sections display saved data: overview, model-specific causal probabilities, strategy comparisons and controls, fold/stress/holdout validation, and quality/PCA diagnostics. Global return-date/strategy filters recalculate from the underlying daily run artifacts, without artificial liquidation at the filtered boundary. Chart downsampling is visual only. Full-run attribution, regime summaries and predefined stress/holdout tables are marked when unaffected by a chart date filter. Table CSV exports include the complete **filtered** table, even when only the first page of rows is displayed; artifact downloads are explicitly full-run files.

Important API routes (all use relative paths from the browser):

| Route | Purpose |
| --- | --- |
| `GET /api/health`, `GET /api/runs` | Health and immutable run inventory/status |
| `GET /api/runs/{id}/overview` | Metadata, assumptions, performance and holdout |
| `GET /api/runs/{id}/series?start=...&end=...&strategies=...` | Filtered, rebased daily series and recalculated statistics |
| `GET /api/runs/{id}/regime?model=...` | Filtered probabilities, exposures and occupancy |
| `GET /api/runs/{id}/attribution`, `/validation`, `/quality` | Actual saved diagnostic artifacts |
| `GET /api/compare-runs?run_ids=id1,id2` | Side-by-side diagnostics and provenance mismatch warnings |
| `GET /api/runs/{id}/export/{artifact}` and `/report/{name}` | Allowlisted CSV and Markdown downloads |
| `POST /api/job`, `GET /api/job` | Launch and observe one fixed-dataset local research job |

CSV/JSON loads are cached by file path, modification time and size. Inputs, dates, strategy/model names, allowed paths and job limits are validated; missing artifacts and unfinished runs are reported as errors, not populated with placeholders. The job uses an argument list without a shell or user-controlled filesystem path, but **the API has no authentication**. Use locally behind a firewall, never as a public multi-user deployment.

## Known limitations

Single index, previously researched dates and post-inspection control choice limit inference. Prices are not independently verified or a dividend-adjusted tradable fund. The quarterly-lookback random controls can inherit local HMM exposure dynamics; matching is imperfect. Historical models and bootstrap assumptions may not generalize, especially across structural changes; no multiple-testing correction is applied. RBI yields have vintage/staleness limits, exchange-calendar verification is incomplete, and suspicious Open values need source confirmation. Matching state labels by volatility is heuristic. The browser chart is downsampled, while reported metrics use all dates. Dependency/BLAS and OS differences may affect exact HMM optimization; versions are recorded and a core constraints file is included. No live market feed, accounts, brokerage, AI assistant or trading functionality is provided.
