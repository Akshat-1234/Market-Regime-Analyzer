# Research audit and decision log

## Phase 0 — inventory (2026-11-04)

The root repository is the original notebooks, serialized model, CSV outputs, a Python backtester, FastAPI backend and React/Vite frontend. `market-regime-platform.zip` is a separate later Arena project; it remains unchanged and is the archival source for its `src/regime_backtester`, configs, tests, reports, synthetic example, historical result CSVs and two purported runs. Its bundled `.venv` is not research source. No other ZIP was supplied. Root notebooks/CSVs and the legacy implementation are retained, not silently rewritten.

The attached CSV has SHA-256 `ea6dfffb93e5eabd8b6a2f96cd40d6b3ec5c7f47f2f9e6c0cbd3ca9a5f2ac5e4`, 4,684 rows, 2007-09-17–2026-10-22, byte-identical to the archive's raw file. Root `nifty_index.csv` has the same stated range and row count but a different byte hash (line endings); `backend/nifty_index.csv` ends 2026-10-16 (4,682 rows). No independent vendor verification or total-return series was supplied. Preserve the attachment verbatim as the new research input. OHLC quality, especially early opens, needs independent vendor verification.

### Prior experiments, conclusions, and missing evidence
- The archive `examples/synthetic_run` is synthetic, not NIFTY evidence. `validation/independent_nifty` contains aggregate-only third-party results; input and provenance/licensing are inadequate for independent reproduction.
- Archive `results/nifty_2012_delayed` and `results/nifty_2012_same_close` contain genuine-data-labelled historical outputs and configs. `runs/run_20261030_080824_12346d` contains tables and a freeze. The purported later main `run_20261030_081436_12ea5b` contains reports, input snapshots and some source, **but not its claimed CSVs, status or freeze**. Its summary is a historical claim, not a newly verified result. Raw input exists despite the issue stated in the request; complete filtered probabilities are not identifiable in the archive. The former 14-model source/config is missing.
- Archive default specifies `rvd_3`, diag Gaussian HMM, features daily return, 20-day volatility, 252-day drawdown, 3 states; ensemble includes 2- and 3-state RV/RVD models. Root backend fits a different 3-state model and frontend assumes IDs 0–2. No `rv2_k4` artifact or E7 protocol/specification definitions were found in the supplied ZIP or repository. Therefore neither a four-state model's status nor the exact prior four E7 specifications can be verified. Do not present either as validated. E7 cannot be faithfully completed without its preregistered four independent specifications, ranking rule and fold/bootstrap details; selecting them after reading historical reports would change the hypothesis. Request those exact configs/protocol.
- Prior archive reports a delayed 2012–2026 HMM + trend Sharpe 0.287 versus trend 0.286, 95% paired block-bootstrap interval approximately [-0.189, 0.177], and lower historical drawdown. It does not establish an incremental Sharpe edge; approximate controls and prior search weaken inference. Its 63-day control history was chosen after looking at results. The baseline claims reproduction by its author; this workspace has not yet independently reproduced it. Same-close execution is optimistic. Fixed 6.5% cash and 10 bps costs are assumptions; index excludes dividends and implementation frictions.
- Prior reports claim prospective freeze after 2026-10-30, but source hash must match the actual frozen code; altered source invalidates it. No post-freeze data and no completed prospective validation. Gaussian HMM durations are geometric; empirical duration diagnostics are descriptive, not an HSMM validation.
- Original adaptive selector ranks strategies by returns masked by contemporaneous training regimes: same-day state uses that day's return and creates in-sample selection bias. Close-based signals shifted one row against close-to-close returns assume filling at the signal close, not a next-close fill. Do not use that output for deployable performance claims. Frontend hardcodes three states and the backend dataset is stale. Root historical results are preserved, not promoted to validated research.

## Decisions
1. Retain all originals and the intact archive; keep new research distinct and identify input hashes and code/config.
2. Use close-only features for model inputs while OHLC quality is unresolved; diagnostics must be explicitly separate.
3. Use training-only scalers/fits and forward-filtered OOS probabilities; at close t a signal can execute at t+1 close and earns returns starting t+2. Avoid interpreting smoothed training assignments as live decisions.
4. Treat all historically inspected periods as exploratory. Do not announce a final optimal model or prospective validation without independent evidence.
5. No new findings for the absent exact E7 protocol, forecasting, or adaptive strategy selection should be implied by dashboard placeholders.

## Progress
- Phase 0: completed inventory above; archive preserved. Model identity and E7 protocol remain unresolved.
- Subsequent phases and verification: see `docs/PROGRESS.md` as work proceeds.
