# Independent research audit and advancement of the Market Regime Analyzer

**Date:** 30 October 2026 · **Scope:** the uploaded `market-regime-platform.zip` (extracted unchanged into `market-regime-platform/`) plus a new research extension layer.
**Data:** user-supplied NIFTY 50 index OHLC, 2007-09-17 → 2026-10-22, SHA-256 `ea6dfffb…5f2ac5e4`, 4,684 sessions.
**Evaluation window:** 2012-01-05 → 2026-10-22 (3,632–3,634 out-of-sample return observations depending on execution lag).

This report separates what was **verified**, what was **executed**, and what is **inference**. Every number below is produced by code in this repository and can be regenerated with the commands in §12.

---

## 1. Executive diagnosis

The platform is careful about causality and honest about its negative result. It is *not*, however, a test of the research question it states. The decisive design fact is:

> In the original engine, a latent state is used only through
> `exposure = min(1, 0.12 / state_vol)`,
> where `state_vol` is the training-window volatility of the next-day return in that state.
> The model's only action channel is therefore a smooth, monotone function of estimated
> volatility, and the estimated state volatility is itself a smoothed function of realised
> volatility. The design cannot, even in principle, distinguish "regime information" from
> "volatility targeting".

Everything else follows from that:

1. The fitted posteriors are effectively degenerate: the median normalised entropy of the primary model is **0.0012** and **87.6 %** of out-of-sample days have a max state probability above 0.99. The "probability uncertainty" channel that the HMM is supposed to add is numerically unavailable.
2. The primary model's exposure has **R² = 0.42** against a single regressor, `1/volatility_20`, and correlates **0.67** with the platform's own observable `Vol Target` benchmark.
3. Consequently, when the previous team matched controls on exposure, the controls reproduced the strategy: an exposure-matched random path has no reason to be worse, because the exposure *is* the information.
4. Nothing in the baseline uses the state-conditional **return** estimates that the model already computes (`state_means`), so the research question about latent *directional* structure was never tested.

The new experiments address (1)–(4) directly. Their conclusion, stated in advance of the allocation results, is that the data do contain a persistent two-to-four-state volatility structure with real out-of-sample density gains over one or two states, but that **causal state information does not improve out-of-sample return or volatility forecasts beyond conventional observables, and its allocation timing does not beat strong matched controls** (§8–§10).

**Headline results** (all from `research_outputs/study_20261030T111521Z/`; the paragraph above was written before these were computed, and the results confirm it with one addition marked †):

| Result | Number | Section |
| --- | --- | --- |
| Best state count by held-out density | K = 4 (−0.697 nats/day at the selected feature set); BIC keeps improving to K = 6 and K = 7 is unidentifiable | §6 |
| Best feature set | `daily_return + volatility_20`; the shipped 3-feature model is 0.485 nats/day **worse**, and every other feature family is worse still | §7 |
| Best emission family | Gaussian diagonal; Student-t fits ν ≈ 74–100 and sticky transitions lower held-out density; geometric durations rejected (χ² = 26.5, p ≈ 7 × 10⁻⁵) | §9.4 |
| Regime information vs observables, in-sample | +1.2 pp R² at the 20-day return horizon, joint Wald p = 0.057 (entropy, t = −2.09) | §8.2 |
| Regime information vs observables, out-of-sample | OOS R² −0.005 to −0.027, Diebold–Mariano p ≥ 0.13 → **no gain** | §8.3 |
| Allocation | regime vol-state Sharpe 0.260 vs Trend 50 0.286; paired interval −0.334 to +0.325 → **indistinguishable** | §9.1 |
| † Exposure-timing test | real exposure path sits at the **4.5th percentile** of 200 circular shifts with identical marginal and turnover → **timing worse than random** | §9.2 |
| Family-wide reality check (17 strategies) | observed 1.830, **p = 0.12** | §9.3 |
| Defects found / fixed during the programme | 11 found, 4 fixed (including a −243 OOS R² that was an estimator artefact, and a cash-rate scale error that reversed several paired comparisons) | §8.1, §9.1, `VERIFICATION.md` |

---

## 2. Verified baseline (reproduction, not quotation)

The archived delayed experiment was re-executed with the current source:

```bash
python run.py --csv data/raw/nifty_index.csv --start 2012-01-01 \
  --execution-delay 1 --bootstrap-samples 1000 --output <new-directory>
```

| Strategy | CAGR | Sharpe | Max drawdown | Mean exposure | Turnover/yr |
| --- | ---: | ---: | ---: | ---: | ---: |
| Buy & Hold | 11.45 % | 0.364 | 38.44 % | 100.0 % | 0.07 |
| Trend 50 | 9.26 % | 0.286 | 20.93 % | 68.4 % | 12.90 |
| HMM Ensemble | 8.83 % | 0.254 | 21.01 % | 75.4 % | 1.77 |
| HMM + Trend | 9.12 % | 0.287 | 17.20 % | 71.9 % | 7.35 |

* All nine strategies in `performance.csv` reproduce the archived `results/nifty_2012_delayed/performance.csv` **exactly** at CSV precision (frame equality after rounding to 10 decimals).
* The regenerated `signals.csv` is **identical on all 17 shared columns** (max absolute difference 0.0) to `runs/run_20261030_080824_12346d/signals.csv`. The older `results/nifty_2012_delayed/signals.csv` predates the addition of per-model probability columns and is byte-different for that reason only; its strategy performances are identical.
* The claimed attribution numbers (real HMM + Trend 0.2873; past-only shuffled 0.2203; block shuffled 0.3316; matched random 0.3342) are consistent with the archived `attribution.csv` of `run_20261030_080824_12346d`, but that run is a *reconstruction* (4 models, not the historical 14), so the historical figures cannot be claimed as reproduced.

**The archived attribution control is only first-moment matched.** The supplied "exposure/turnover-matched random" control reproduces the real strategy's *mean* exposure (0.693 vs 0.719) and turnover (7.29 vs 7.35 per year) across its 200 simulations, but **not its exposure distribution**: the median Kolmogorov–Smirnov distance between the control's exposure path and the real one is **0.310** (range 0.212–0.433). A control that agrees on the mean and the turnover but differs by 31 % of the exposure CDF is not an exposure-matched control, so the headline attribution comparison (real 0.2873 vs matched random 0.3342) cannot be read as "the real exposure path is worse than an equivalent random path". This is one of the reasons the research programme rebuilt the control set (report §5, §9.2) instead of trusting the archived one. It is now encoded as a test (`test_archived_attribution_control_matches_only_the_first_moment`).

**Provenance defect found.** The "main" run `run_20261030_081436_12ea5b` is **incomplete in the archive**: it contains only `figures/`, `inputs/`, `logs/`, `reports/` and `source/`. Every referenced table (`attribution.csv`, `fits.csv`, `fold_metrics.csv`, `performance.csv`, `holdout_freeze.json`, …) is missing. Five API/integration tests skip because of this. The executable run `run_20261030_080824_12346d` is complete and was used as the audit baseline.

---

## 3. Baseline audit: exact configuration

| Item | Verified value |
| --- | --- |
| Dataset | `data/raw/nifty_index.csv`, Date/Open/High/Low/Close, 4,684 rows, 2007-09-17 → 2026-10-22 |
| Data quality | 0 duplicate dates, 0 invalid OHLC rows, 4 zero-return days, 43 days with \|r\| > 5 %, 301 weekdays without a row (holidays are not distinguished from gaps) |
| Suspicious field | **315** opens within 1 bp of the previous close, **122** of which have a > 1 % intraday move — Open is excluded from all research features |
| Features (baseline) | `daily_return`, `volatility_20` (annualised 20-day close-to-close), `drawdown_252`, and for the 3-feature models `drawdown_252` |
| Preprocessing | `StandardScaler` fitted **inside each training window**; no imputation; contiguous complete rows only; optional PCA unused by default |
| States | Gaussian HMM, `covariance_type=diag`, 2 or 3 states, `min_covar=1e-3`, `n_iter=250`, `tol=0.05`, seeds `[2, 42]`, best in-sample likelihood with occupancy ≥ 2 % |
| Transition model | unconstrained row-stochastic matrix, geometric durations |
| Refit | expanding window, annual (first session of each calendar year), `min_train_days=504`, training ends strictly before the first signal |
| Probabilities | causal **forward** recursion only, seeded with the last training-window alpha; `predict_proba`/Viterbi (smoothed) never used for decisions |
| State interpretation | states re-ranked each refit by **training** next-day volatility; exposure `min(1, 0.12/max(state_vol, 0.03))`; ensemble = mean of four models |
| Allocation | `HMM + Trend = 0.5 × HMM Ensemble + 0.5 × Trend 50` (arithmetic blend, not a gate) |
| Execution | decision at close *t*, filled at close *t+1*, earns the close-to-close return *t+1 → t+2* (the code's "one-session delay"); same-close is retained as an optimistic sensitivity |
| Costs | 10 bps one-way proportional, applied to the exact self-financing rebalance; drift-driven rebalancing also trades |
| Cash | constant 6.5 % annual, plus a lagged RBI 91-day auction-yield sensitivity |
| Metrics | CAGR (n/252 years), annualised Sharpe on excess returns, max drawdown including initial capital, Sortino with downside over all observations, Calmar |
| Inference | paired 20-session circular block bootstrap of Sharpe differences (1,000 resamples), descriptive control percentiles (not p-values) |

### 3.1 Methodological weaknesses identified

**Design-level (most important)**

1. **No return-information channel** (§1). State *means* are estimated but never used; the exposure map is pure volatility targeting.
2. **No state-count selection.** Four configurations were fixed; the primary (`rvd_3`) was carried over from an earlier conversation. No AIC/BIC/predictive-likelihood comparison, no seed-stability study, and no test that K = 3 is even identifiable.
3. **Controls match only the exposure marginal.** Phase-shifted, block-shuffled and "matched random" controls preserve or approximate the exposure distribution, but the real strategy differs from them only in *timing*; the controls are therefore the correct null yet they were interpreted as a matching diagnostic rather than as a test of information.
4. **The "HMM + Trend" label is an arithmetic average.** At 50/50 the HMM contributes half of a volatility-targeted exposure; any drawdown improvement can come from lower average risk, not from regime identification. The report says this, but no exposure-matched trend benchmark is run to prove it.
5. **No reality check over the strategy family.** The bootstrap compares one pre-selected pair; it does not account for the many strategies and variants examined.

**Model-level**

6. **Gaussian emissions on a series with excess kurtosis 16.0.** The Gaussian likelihood is dominated by a handful of extreme days; no heavy-tailed alternative is tested.
7. **Degenerate posteriors.** With `min_covar=1e-3`, three correlated standardized features and a loose convergence tolerance (`tol=0.05`), the filtered posterior saturates. Median entropy 0.0012 means the "uncertainty" variables are numerically dead.
8. **Geometric duration assumption untested.** Mean implied durations of 59–70 sessions coexist with a 4.6 % state that switches frequently; the fit quality of a geometric duration law was never examined.
9. **BIC-style complexity is not used at all**, and raw likelihood grows with K; the previous team had no principled way to judge whether "more states" helped.
10. **Feature redundancy.** `drawdown_252` correlates −0.70 with `volatility_20` and 0.79 with `ma_distance_200`; adding it to a 2-feature model raises max VIF to 2.0 and adds a near-duplicate dimension. Downside and Parkinson volatility correlate 0.91 and 0.95 with `volatility_20`.
11. **Seed fragility undisclosed at the state level.** With two seeds the engine accepts the best likelihood; nothing reports how different the two solutions are (see §6: ARI falls from 0.99 at K = 2 to 0.56 at K = 6).

**Evaluation-level**

12. **Execution-timing sensitivity was never quantified.** It is large (§4): the HMM + Trend Sharpe moves from 0.288 (one-session delay) to 0.329 (two sessions) and its drawdown from 17.2 % to 15.0 %, while Trend moves from 0.286 to 0.364. A one-day change in fill convention changes the apparent value of the regime overlay by more than any regime effect found.
13. **The 2023–2026 slice has already been examined**, so no part of the evaluation window is a clean holdout. The freeze mechanism is a good idea but its evaluation date (2026-10-30) is *after* the last supplied observation (2026-10-22), so the holdout is necessarily pending.
14. **Constant 6.5 % cash** for 2012–2026 is historically wrong for 2012–2016 and 2020–2021; the RBI sensitivity exists but is not the headline.
15. **No multiple-testing correction and no experiment register** existed before this audit.

### 3.2 What is verified fact vs hypothesis

| Claim | Status |
| --- | --- |
| Baseline numbers reproduce exactly | **Verified** (this audit) |
| Filtered probabilities are causal | **Verified** by code inspection, truncation test in the existing suite, and a new truncation test (§11) |
| States are "regimes" in an economic sense | **Not supported.** They are training-volatility ranks; occupancy 56/39/5 %; identity across refits fails 7–43 % of the time depending on K |
| The HMM adds information beyond trend | **Not supported** by the archived controls; confirmed and sharpened in §10 |
| The HMM reduces drawdown | **Descriptively true for one execution convention**; not separable from lower average exposure (§4, §10) |
| Probability uncertainty is usable | **False as fitted**: the posterior is saturated |

---

## 4. Execution-timing sensitivity (new evidence)

Identical archived exposure paths, re-simulated under four fill conventions (`research_outputs/*/audit/execution_timing_sensitivity.csv`):

| Strategy | delay 0 (same close) | delay 1 (baseline) | delay 2 | delay 3 |
| --- | ---: | ---: | ---: | ---: |
| Buy & Hold Sharpe | 0.362 | 0.364 | 0.364 | 0.364 |
| Trend 50 Sharpe | 0.313 | 0.286 | 0.364 | 0.314 |
| HMM Ensemble Sharpe | 0.228 | 0.254 | 0.253 | 0.269 |
| HMM + Trend Sharpe | 0.289 | 0.287 | 0.329 | 0.310 |
| HMM + Trend max DD | 17.4 % | 17.2 % | 15.0 % | 13.5 % |

A single extra session of delay moves the HMM + Trend Sharpe by +0.042 and cuts its drawdown by 2.2 points. The mechanism is path-dependent exit timing around a handful of crash days (2020-03 in particular), not information. Any claim of the form "the overlay reduces drawdown" must be reported per convention, and the convention is a research degree of freedom — another reason the effect cannot be interpreted as regime skill.

---

## 5. Research design (Phase C)

Hypotheses, one modelling dimension at a time, all with the **same causal protocol**:

* **H1 (discovery).** A state count above two is required, and is identifiable: held-out predictive density improves, states are occupied, seeds agree and identities persist across refits.
* **H2 (representation).** Trend, downside asymmetry, range volatility or vol-of-vol add held-out information beyond returns and volatility.
* **H3 (emissions/duration).** Heavy tails (Student-t) or duration priors (sticky transitions) improve held-out density relative to Gaussian/geometric.
* **H4 (predictive information).** Causal state probabilities predict future returns/volatility/drawdown after controlling for trend, momentum, volatility and drawdown.
* **H5 (allocation).** A regime-conditioned allocation rule beats trend, volatility targeting and **matched controls** after costs.

**Selection rule, fixed before running.** Choose K, feature set and emission family by the mean *inner* held-out predictive log-density over the last 20 % of every training window (never used to fit that candidate). AIC, BIC, seed ARI, duration and downstream Sharpe are reported but **never** used to select. Downstream allocation uses one specification for all folds; no per-fold or per-year model choice.

**Controls, fixed before running (and deliberately not weakened):**

1. **Phase shift** of the real exposure path (200 circular offsets ≥ 250 sessions): identical marginal distribution, identical autocorrelation, zero alignment with returns.
2. **Markov path**: state paths simulated from each fold's fitted transition matrix and mapped through the same state exposures: identical persistence and marginal, no data information.
3. **Vol-matched**: an isotonic map `volatility_20 → exposure` refit causally every 21 sessions on past data only: no latent state at all.
4. Family-wide **Hansen-style reality check** (studentised, stationary bootstrap, 1,000 resamples) against trend + observable volatility targeting.

---

## 6. H1 — Latent-state discovery

Executed on `daily_return + volatility_20 + drawdown_252`, K = 2…7, Gaussian-diagonal, seeds {2, 42, 7}, 15 annual folds (`research_outputs/*/discovery/`).

| K | inner held-out log-density (nats/day) | test-block log-density | BIC (sum) | min state occupancy | effective states | seed ARI (mean) | identity alignment |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 2 | −2.071 | −2.026 | 197,722 | 20.7 % | 1.58 | **0.988** | **100 %** |
| 3 | −1.419 | −1.412 | 145,136 | 8.8 % | 2.55 | 0.767 | 92.9 % |
| **4** | **−1.182** | **−1.183** | 122,133 | 6.2 % | 3.20 | 0.721 | 78.6 % |
| 5 | −1.383 | −1.328 | 105,857 | 4.3 % | 4.10 | 0.574 | 85.7 % |
| 6 | −1.380 | −1.352 | 100,491 | 2.0 % | 4.56 | 0.563 | 57.1 % |
| 7 | **rejected** | — | — | < 2 % | — | — | — |

Findings:

* **Two states are clearly insufficient** (−2.07 vs −1.18 nats/day) and K = 4 is the best held-out specification. The improvement from K = 3 to K = 4 is large relative to numerical noise (0.24 nats/day).
* **BIC keeps improving to K = 6**, and even K = 7 would improve it if states were allowed below 2 % occupancy. BIC is a poor selector here because the likelihood gain from splitting a volatility state is large while the penalty is O(log n) for K² parameters; held-out density (which pays for over-fitting) turns over at K = 4. This is a concrete demonstration that likelihood-based state-count selection would have chosen the wrong model.
* **Stability degrades with K.** Seed agreement falls from ARI 0.99 to 0.72 (K = 4) and 0.56 (K = 6); state identity across annual refits is preserved for 100 % of folds at K = 2, 79 % at K = 4 and 57 % at K = 6. So even the selected 4-state solution is only moderately reproducible: the fourth state is real for density but its identity is partly arbitrary.
* **K = 7 is not identifiable** under a 2 % occupancy floor: every seed produced a state below the floor in at least one fold.

This is the first defensible answer to "how many states?": **four for density, but three of them carry most of the weight and the fourth is unstable.**

---

## 7. H2 — Is the market representation adequate?

Same protocol at K = 4, one dimension added per specification (`research_outputs/*/features/feature_ablation.csv`):

| Feature set | inner held-out log-density | Δ vs rvd3 | max VIF | verdict |
| --- | ---: | ---: | ---: | --- |
| **rv2** (`daily_return`, `volatility_20`) | **−0.697** | **+0.485** | 1.00 | selected |
| rvd3 (+ `drawdown_252`) | −1.182 | 0.000 | 2.02 | duplicate risk dimension |
| + downside volatility | −1.425 | −0.243 | 6.21 | redundant with σ (ρ = 0.91) |
| + Parkinson range volatility | −1.676 | −0.494 | 8.98 | redundant with σ (ρ = 0.95) |
| + vol-of-vol | −2.277 | −1.095 | 2.80 | dilutes separation |
| + risk-adjusted trend | −2.527 | −1.346 | 2.18 | harmful |
| accumulation (7 features) | −4.187 | −3.005 | 13.95 | clearly harmful |

Every added dimension **reduces** out-of-sample predictive density. The two-dimensional representation is not merely adequate; it is the best of the tested families. The explanation is straightforward: with ~1,000–3,400 training observations, each extra dimension adds Gaussian covariance parameters and spreads a fixed number of states over more space, so the posterior stops being informative. The brief's warning against indicator accumulation is empirically confirmed on this dataset.

**Implication for the original design:** the chosen primary model (`rvd_3`) is *not* the best representation. This is a substantive correction to the baseline, not a cosmetic one.

---

## 8. H4 — Does causal regime information predict anything?

Two questions are separated here: *in-sample association* (does a filtered state probability covary with the future after controlling for trend, momentum, volatility and drawdown?) and *out-of-sample forecasting* (does adding regime variables to an expanding-window model reduce forecast error?). Only the second can support a claim that the information is usable.

### 8.1 An implementation defect found before the result was read

The first version of the expanding-window comparison scaled its regressors once, on the initial 500-session window, and applied a ridge penalty of 1.0 to a design whose scale was set by that window. On this dataset the fuzzy high-volatility state is **essentially never occupied before March 2020** (maximum filtered probability 0.012 across 2012–2020-02). A slope fitted on a column that is 0 for 99.9 % of its own estimation window is unidentified; when the state finally switched on, the model extrapolated it and produced:

* a 1-day return forecast of **+31 %** on 2020-03-20 (target range −13 % to +9 %),
* a 20-day volatility forecast of **−15.7** on 2020-03-12 (target range 5 % to 89 %).

Those forecasts are 8–314 training standard deviations away from the training target distribution. Reporting their OOS R² (−243 for forward volatility) as evidence that "regime information does not help" would have been a false negative dressed as a finding. The estimator was corrected before any conclusion was drawn, and three safeguards are now in the code and in the tests:

1. **Unidentifiable columns are neutralised.** In each estimation window a column whose standard deviation is below 10 % of its *own* estimation-window range is treated as a spike, not a regressor: its standardised values are set to exactly zero, so its coefficient is pinned at zero for that window. This happened in 509–515 window-columns (nearly all of them `p_high_vol` before 2020).
2. **No extrapolation beyond estimation support.** Standardised forecast values are clipped to the estimation window's own standardised range (131 clipped values across the whole run, all in the 2020-03 transition).
3. **Diagnostics are written out.** `predictive/expanding_oos.csv` carries `forecast_sd_*`, `max_abs_forecast_in_training_sd`, `columns_without_training_variation` and `forecast_values_clipped_to_training_support`, so a reader can see whether the estimator failed rather than having to trust a summary statistic. The maximum is now 8.9 training standard deviations (the volatility target during March 2020, where the model predicts 0.18 against a realised 0.88).

The rule this episode illustrates: **a negative result is only interpretable after the estimator has been shown not to be broken.**

### 8.2 In-sample association (HAC/Newey-West, 10 lags, n ≈ 3,614)

| Target | R² observables only | R² + regime block | ΔR² | joint Wald p |
| --- | ---: | ---: | ---: | ---: |
| Forward 1-day return | 0.0033 | 0.0047 | +0.0014 | 0.802 |
| Forward 5-day return | 0.0149 | 0.0208 | +0.0059 | 0.278 |
| Forward 20-day return | 0.0477 | 0.0597 | **+0.0120** | **0.057** |
| Forward 20-day volatility | 0.3562 | 0.3638 | +0.0076 | 0.323 |
| Forward 20-day drawdown | 0.0320 | 0.0463 | +0.0143 | 0.226 |

The regime block is a joint near-miss for the 20-day return, and the coefficient doing the work is **posterior entropy** (t = −2.09), not the high-volatility probability (t = 0.12). Posterior uncertainty is slightly *negatively* related to the subsequent 20-day return. The volatility block, by contrast, is not improved at all: the filtered states add nothing to a 35.6 %-explained volatility regression, which is what one expects given that the state map is itself a monotone function of realised volatility.

### 8.3 Out-of-sample forecasting (expanding window, refit every 21 sessions, minimum 500 observations)

The design is identical for both models (observable-only vs observable + `p_high_vol` + `entropy`), the ridge penalty is identical, and every forecast uses only data strictly before it.

| Target | OOS R² vs observable-only | Diebold-Mariano p | forecast sd (obs / +regime) |
| --- | ---: | ---: | ---: |
| Forward 1-day return | −0.0053 | 0.269 | 0.00051 / 0.00072 |
| Forward 5-day return | −0.0165 | 0.361 | 0.00266 / 0.00339 |
| Forward 20-day return | −0.0047 | 0.607 | 0.00973 / 0.01109 |
| Forward 20-day volatility | −0.0272 | 0.347 | 0.03311 / 0.03573 |
| Forward 20-day drawdown | −0.0125 | 0.130 | 0.00297 / 0.00451 |

**The regime information does not improve out-of-sample accuracy at any horizon.** The degradation is small (0.5–2.7 % of the baseline MSE) and statistically indistinguishable from zero (all DM p ≥ 0.13), so the correct reading is *no demonstrated value*, not *demonstrated harm*. The in-sample entropy association does not survive re-estimation: this is the pattern of an in-sample fit to a handful of episodes (the top state is occupied on 53 of 3,634 days).

### 8.4 What the states actually precede

States ranked by their own (training-window) volatility, concatenated over the 15 folds:

| rank | days | mean exposure | mean state vol | mean fwd 20-day return | mean fwd 20-day vol | mean fwd 20-day drawdown |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 0 (calm) | 2,281 | 0.886 | 0.137 | +0.84 % | 0.124 | −2.1 % |
| 1 | 866 | 0.715 | 0.171 | +0.44 % | 0.159 | −3.0 % |
| 2 | 434 | 0.524 | 0.235 | +1.93 % | 0.173 | −2.5 % |
| 3 (stressed) | 53 | 0.273 | 0.440 | **+6.42 %** | 0.385 | −4.0 % |

Forward return *increases* with the volatility rank while the allocation rule *decreases* exposure with it. The stressed state is followed by higher volatility (so the risk forecast is right) but also by the highest mean forward return (so the return forecast, implicitly, is wrong). The 53-day cell is small and its interval is wide, but the monotone ordering across four ordered cells is not what a "risk-off in stress" rule assumes.

Entropy quintiles tell a consistent but equally fragile story: mean forward 20-day return falls monotonically from 1.23 % (lowest entropy) to 0.51 % (highest entropy), and every overlapping bootstrap interval contains the neighbouring quintile's point estimate.

## 9. H5 — Allocation net of costs, against conventional strategies and matched controls

All rules are evaluated on the same 3,632 delayed out-of-sample sessions, 10 bps one-way, next-close execution, 6.5 % cash. The regime model is the study's selected specification (`rv2`, K = 4, Gaussian-diagonal, no stickiness — see §7 and §9.4) refit annually.

### 9.1 Performance

| Strategy | CAGR | Sharpe | MaxDD | Calmar | mean exposure | turnover/yr |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Buy & Hold | 11.45 % | 0.364 | 38.44 % | 0.298 | 1.000 | 0.07 |
| Trend 50 | 9.26 % | 0.286 | 20.93 % | 0.442 | 0.684 | 12.90 |
| Vol Target | 8.88 % | 0.246 | 19.76 % | 0.449 | 0.851 | 4.01 |
| Momentum 20 | 5.43 % | −0.048 | 17.63 % | 0.308 | 0.616 | 22.89 |
| MA Reversion | 7.34 % | 0.128 | 34.71 % | 0.212 | 0.226 | 9.85 |
| RSI Reversion | 6.16 % | 0.019 | 32.67 % | 0.189 | 0.188 | 6.93 |
| Donchian | 5.25 % | −0.086 | 14.81 % | 0.355 | 0.495 | 6.93 |
| **Regime vol-state** | 8.97 % | **0.260** | 19.14 % | 0.469 | 0.793 | 2.24 |
| Regime vol-expected | 8.95 % | 0.259 | 19.04 % | 0.470 | 0.792 | 2.24 |
| Regime vol-transition | 8.88 % | 0.254 | 18.98 % | 0.468 | 0.785 | 2.26 |
| Regime entropy-scaled | 8.70 % | 0.244 | 17.83 % | 0.488 | 0.757 | 5.95 |
| Regime return-tilt | 6.72 % | 0.070 | 24.38 % | 0.275 | 0.628 | 4.64 |
| Trend × vol target | 8.07 % | 0.201 | 15.74 % | **0.513** | 0.610 | 12.96 |
| Regime risk gate on Trend | 8.68 % | 0.240 | 18.96 % | 0.458 | 0.675 | 13.39 |
| HMM + Trend blend (legacy) | 9.19 % | 0.290 | 16.47 % | 0.558 | 0.738 | 7.59 |

Paired stationary-bootstrap comparisons (1,000 resamples, mean block 20), in annualised Sharpe units:

| Comparison | Difference | 95 % interval | fraction ≤ 0 |
| --- | ---: | ---: | ---: |
| Buy & Hold − Trend 50 | +0.078 | −0.302 to +0.460 | 0.35 |
| Regime vol-state − Trend 50 | −0.026 | −0.334 to +0.325 | 0.55 |
| Regime vol-state − Vol Target | +0.015 | −0.041 to +0.070 | 0.29 |
| Regime vol-state − Trend × vol target | +0.059 | −0.245 to +0.384 | 0.36 |
| Regime return-tilt − Trend 50 | −0.216 | −0.614 to +0.186 | 0.85 |
| HMM + Trend blend − Trend 50 | +0.004 | −0.166 to +0.179 | 0.48 |

(The same table in the superseded run — `study_20261030T104848Z` — reported these differences as −8.2 and −21.4 "Sharpe points". That was a units defect: the annual cash rate was passed where a daily rate was expected, which does not cancel in a Sharpe *ratio* and reversed the sign of differences between strategies of different volatility. Defect D6 in `docs/VERIFICATION.md`; the numbers above are from the corrected run.)

Readings that a careful reviewer would insist on:

* **Every regime comparison is statistically indistinguishable from its benchmark**, and the intervals are wide (a ±0.3 Sharpe band against Trend 50). The data cannot show that regime allocation is worse, and it certainly cannot show it is better. A reader who wants a single sentence: *the regime overlay neither helps nor hurts detectably, and the only reason it looks safer is that it is invested less.*
* **No regime rule beats the plain Trend benchmark on point Sharpe**, and none beats Buy & Hold. The best regime-flavoured rule (the legacy 50/50 blend, 0.290 vs 0.286) is inside any sensible error bar; its advantage over Trend 50 is +0.004 Sharpe with an interval of −0.166 to +0.179.
* **`policy_hmm_trend_blend` and `policy_volstate_trend_blend` are numerically identical** by construction — the legacy HMM exposure *is* the state-volatility mapping, so the two "different" blends are one rule. The table therefore contains one fewer independent strategy than it appears to.
* The return-tilt channel (state-conditional expected returns, shrunk) has the **worst** point estimate of any regime policy (0.070 vs 0.286 for Trend 50, −0.216 Sharpe, interval −0.614 to +0.186). This is directionally consistent with §8.4: using the states to forecast returns, rather than risk, is the wrong channel.
* **Reduced exposure is not skill.** The regime policies run 0.79 mean exposure against 1.00 for Buy & Hold; a rule that is right-scaled but empty most of the time will show a higher Calmar and Sharpe without predicting anything. This is why the matched controls below, not the raw table, decide the question.

### 9.2 Matched controls (the decisive test)

| Policy | real Sharpe | phase-shift median (p05–p95) | fraction real above | Markov-path median (0.05–0.95) | fraction real above | vol-matched median (p05–p95, 100 refits) | fraction real above |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Regime vol-state | 0.260 | 0.342 (0.264–0.432) | **0.045** | 0.301 (0.166–0.451) | 0.295 | 0.238 (0.228–0.260) | 0.95 |
| Regime return-tilt | 0.070 | 0.296 (0.127–0.488) | **0.000** | 0.290 (0.153–0.434) | 0.000 | — | — |

The three controls say three different things, and all three matter:

* **Against its own phase-shifted path, the real exposure schedule is in the 4.5th percentile.** The real rule has *identical* marginal exposure (KS = 0.00) and nearly identical turnover, so this is not an exposure-level effect: the timing of the exposure changes is worse than random timing of the same changes. The same test for the return-tilt policy puts the real rule at the 0th percentile. This is the strongest single result in the report, and it is negative: **the regime map's timing is anti-aligned with returns in this sample.**
* **Against Markov-path simulation** the real rule is at the 29.5th percentile — indistinguishable from a random draw from the fitted chain with the same persistence and marginal. No information.
* **Against the vol-matched isotonic control** the real rule is at the 95th percentile (0.260 vs 0.238 with a bootstrap band of 0.228–0.260). The regime map does add something over a smooth function of realised volatility — *provided* the volatility mapping is estimated inside each refit window from a bootstrapped history rather than in one shot. This is the one channel that survives, and it is the channel §3 identified as the only channel the baseline ever had.
* The vol-matched control was previously degenerate (a single deterministic path, `control_simulations = 1`, hence an uninterpretable "fraction above = 1.0"). It now resamples the past (volatility, exposure) pairs at every refit and produces 100 causal refits whose spread reflects estimation uncertainty in the mapping itself. Because that spread is narrow, `fraction_real_above_control` for this control is a *location* diagnostic, not a p-value.

### 9.3 Family-wide reality check

Hansen-style studentised stationary bootstrap (1,000 resamples, mean block 20) of the maximum Sharpe advantage over Trend × vol-target (`real 0.201`): **observed statistic 1.830, p = 0.12**. Nothing in the 17-strategy family (11 of them regime-based) beats that benchmark by more than sampling noise would produce. The largest point advantage is Trend 50 itself (+0.085 Sharpe, t = 1.83), which is not a regime finding at all.

### 9.4 Emissions and duration (why the allocation model is the plain one)

| Specification | inner held-out log-density | notes |
| --- | ---: | --- |
| **Gaussian diag** | **−0.6971** | selected |
| Gaussian full | −0.6978 | no gain from 3 extra covariance parameters per state |
| Sticky κ = 5 | −0.7360 | persistence prior *hurts* held-out density |
| Sticky κ = 20 | −0.7360 | identical to κ = 5 |
| Student-t (ν free) | −0.7574 | estimated ν = 74–100, i.e. the fit *rejects* the heavy tail it was given |

Two facts worth carrying forward: unconditional excess kurtosis of daily returns is 16.0, but the state-conditional two-dimensional fit finds almost no tail beyond Gaussian — the fat tails are in the *mixture*, not in the components. And the geometric duration assumption is rejected: implied mean duration 39.6 sessions vs 29.8 realised, with a run-length χ² of 26.5 on 5 df (p ≈ 7 × 10⁻⁵) for the selected model (and 55.8 for Student-t). Durations are shorter and less geometric than the Markov chain implies, so the standard HMM persistence structure is mis-specified even though adding a persistence prior makes held-out density worse.

## 10. Council review, peer review and synthesis

### 10.1 Contrarian

"The whole programme is one long demonstration that you cannot extract a return signal from a volatility signal. Look at what the matched controls actually say: the real exposure path sits at the 4.5th percentile of its own circular shifts. That is not 'no edge', it is a *negative* edge, and it is the most robust number in the report because it needs no model of expected returns — only that the path was applied to the returns it was fitted on. Meanwhile the headline table invites the reader to conclude that the legacy blend 'works' because it has the best Calmar, when §9.1 shows the blend is exposure reduction plus a trend signal, and §9.2 shows that the state-driven part of it, tested on its own, sits at the 4.5th percentile of its own circular shifts. My objection to the report is rhetorical, not technical: it is too polite about a result that is quite damning for the original claim."

### 10.2 First principles

"Start from identification, not from performance. Three things are established: (i) K = 4 maximises held-out density while BIC keeps rewarding more states, so the field's default information criterion would have chosen a worse model; (ii) every added dimension beyond (return, volatility) reduces held-out density, so the '7-feature accumulation' representation is measurably wrong; (iii) only 78.6 % of folds preserve state identity at K = 4, so the fourth state is partly arbitrary across refits. Together those say the object being allocated on is a noisy, order-dependent partition of a two-dimensional volatility plane. An estimator that reshuffles its own labels across refits cannot be expected to produce a stable exposure rule, and it does not. The negative allocation result is therefore *predictable from the discovery diagnostics*, which is the strongest kind of internal consistency, and it is also the reason I do not believe the positive forward returns in the stressed state: those come from 53 days whose state label is the least stable in the model."

### 10.3 Expansionist

"The negative result is narrow: NIFTY daily close, one asset, one 14-year window, one model family, one horizon structure. The parts of the programme that were never tested are the interesting ones. Nothing here says anything about (a) cross-sectional regime information — regimes *across* 30 stocks rather than in an index, where the covariance structure carries information the index average discards; (b) state-conditional *correlation* rather than state-conditional mean; (c) higher-frequency data, where the mixture's conditional densities are estimable with 10× the observations per regime; (d) durations, which the run-length test showed are mis-specified — a hidden semi-Markov or explicit duration model is a well-posed alternative that was specified but not fitted. I would not tell the club 'regimes do not exist'; I would tell it 'this estimator, on this asset, at this frequency, in this sample, does not convert regimes into returns'."

### 10.4 Outsider

"I am the person who has to read this without knowing what an HMM is. Questions I could not answer from the document as first written: *What is a state?* (answer: a recurring combination of return and volatility, ranked by its own training-window volatility — not 'bull' or 'bear'). *Why does the number 4 appear everywhere?* (because a held-out density criterion chose it, not because anyone picked it). *Why is a 0.004 Sharpe difference reported as if it were a finding?* (it should not be; the honest statement is 'no difference, and the drawdowns differ'). *Why does the report say the model is anti-aligned and then present a 17-row table where it looks fine?* The table needs the matched-control column inside it, and the words 'the regime overlay was worse than randomly reordering its own exposure changes' need to appear before the performance table, not 40 lines after it. Also: 'Sharpe' appears 60 times and 'what would I do differently tomorrow' not once."

### 10.5 Executor

"This is runnable, which is more than most of these reports manage: one command, 25 minutes, deterministic seeds (the discovery and feature tables reproduce bit-identically across two independent runs), a manifest with the data hash, and an experiment register that says which rows were confirmatory and which were decided after looking. Three execution problems remain. First, the archived 'prospective freeze' in `runs/run_20261030_080824_12346d/holdout_freeze.json` records a core-source hash (`11094a40…`) that no longer matches the current code (`abe195ac…`) — the freeze is void the moment the engine is edited, and it was edited. Second, one of the two bundled runs (`run_20261030_081436_12ea5b`) is incomplete: it holds figures, inputs, logs, reports and source but no tables, so five API integration tests silently skipped instead of failing; I pointed the fixture at the complete run so they now execute. Third, there is no honest out-of-sample data left. Every number in this report was computed on observations that were examined before the hypothesis was written down."

### 10.6 Peer review

An independent reviewer would raise, in order of severity:

1. **Multiple testing across the whole programme.** Five predictive targets × three model specifications × five entropy buckets × 17 allocation rules × three controls × five emission families. At α = 0.05 one expects false positives; the only near-significant in-sample result (Wald p = 0.057) does not survive OOS and should not be called a finding. Nothing in this report is claimed at 5 % significance after correction, and no correction could rescue a result whose OOS estimate has the wrong sign.
2. **No untouched data.** The "holdout" 2023-01→2026-10 was examined in the original project, and the freeze date (2026-10-30) post-dates the last observation (2026-10-22), so the freeze can only ever be evaluated prospectively. All confirmatory-looking numbers are retrospective.
3. **Dependence.** Daily overlapping 20-day targets make observations ~19/20 dependent; the report therefore relies on HAC (10 lags) and stationary-bootstrap inference throughout, never on i.i.d. standard errors. The market's own dependence (volatility clustering) is what the state model exploits, so inference about "regime information" is inherently about a serially correlated object.
4. **Single asset, single sample.** NIFTY total-return is unavailable; the index excludes dividends, so absolute CAGR comparisons to a total-return benchmark would be wrong. The 2020 crash carries a large share of the drawdown and control-matching results.
5. **Specification search inside the research loop.** The matched-control design, the vol-matched estimator and the OOS estimator were all revised *after* inspecting diagnostics. Each revision is documented and each made the model look worse or the control look stronger, but the sequence is still a search.
6. **Small stressed state.** The economic story hinges on 53 days in the top state (and, for the 20-day horizon, overlapping windows). That is not enough to establish a risk premium, which is exactly why §10.8 makes it the next question rather than a conclusion.

### 10.7 Synthesis

**WHERE THE COUNCIL AGREES**

* The discovered states are real as *density* objects (they beat K = 2 and K = 3 on held-out predictive density, they are occupied, and refits mostly agree), and useless as *return* objects (no OOS predictive gain, and a worse-than-random exposure-timing record).
* The correct primary model is not the one the project shipped: K = 4 with two features beats K = 3 with three, and every extra feature hurts. That is a substantive correction, and the "more indicators" instinct is empirically wrong here.
* Reduced exposure explains most of the apparent risk improvement; no claim of skill survives exposure matching.
* The programme's scientific value is in the negative result and its controls, not in any Sharpe ratio.

**WHERE THEY CLASH**

* Contrarian and First Principles read the 4.5th-percentile phase-shift result as *anti-skill* (a systematic sign error in the state→exposure map, consistent with the monotone forward-return table). Executor and Outsider read it as *one more in-sample curiosity* on a single 14-year path with a 53-day stressed state, and refuse to build on it. Both are right; the disagreement is about what a single history can support.
* Expansionist wants to leave the index and the daily frequency; First Principles wants a duration-correct model on the same data first. Outsider wants the report to stop at "the overlay did not work and we know why".
* Executor argues no further in-sample work should be done at all until a freeze exists; Expansionist argues a freeze is pointless if the data that would test it does not exist.

**BLIND SPOTS CAUGHT**

* **The estimator defect** (§8.1): a −243 OOS R² was an artefact of extrapolating an unidentifiable coefficient. Caught only because a diagnostic was added; without it the report would have contained a false negative.
* **The degenerate control** (§9.2): a "control" with one simulation and `fraction above = 1.0` had been passing as evidence of superiority.
* **The duplicate strategy** (§9.1): the legacy blend and the vol-state blend are the same rule, so the table overstated the number of independent policies.
* **The archived control was not distribution-matched** (§2): its median exposure KS distance from the real strategy is 0.31 while its mean exposure and turnover match, so the supplied "matched random beats the HMM" attribution rests on a control that only matches the first moment.
* **The void freeze** (§10.5): the archived freeze hash no longer matches the code, so the project has no valid prospective protocol at all.
* **The skipped integration tests** (§10.5): five tests covering the entire artifact API were skipping because they pointed at an incomplete run.
* **The cash-rate scale error** (§9.1, D6): the paired-Sharpe bootstrap subtracted an *annual* 6.5 % cash rate from *daily* returns, which shifts a ratio non-additively and reversed the sign of several comparisons. The first draft of this report quoted the corrupted numbers.

**THE RECOMMENDATION**

Report the programme as a **well-controlled negative result with two constructive by-products**: (i) an evidence-based specification (two features, four states) that is materially different from, and better identified than, the shipped one; and (ii) a reusable validation harness — held-out-density selection, phase-shift/Markov/vol-matched controls, reality check, and estimate-sanity diagnostics — that any future regime claim in this project must pass. Do **not** recommend deploying, tuning or extending the regime overlay, and do not recommend a new feature set.

**THE ONE THING TO DO FIRST**

**Freeze again, properly, and stop editing the engine.** Take a fresh code-hash freeze of `src/regime_backtester` (recording the current hash, the data hash and the frozen config), pre-register the single experiment in §10.8 with its decision rule, and quarantine every observation after the freeze date. Every in-sample result added before that point is a withdrawal from a credibility account that is already overdrawn — and the archived freeze now matches nothing, so today the project cannot make a prospective claim even if it wanted to.

### 10.8 The single most important next research question

> **Is the positive forward return of the highest-volatility latent state a genuine state-conditional risk premium (or recovery effect) that can be exploited, or a small-sample artefact of 53 days and an unstable state label?**

This is the highest-value question because *every* result in this report hinges on its answer. The state→exposure map fails for one identifiable reason: it shortens exposure exactly where realised forward returns are highest (§8.4), and its timing is worse than random (§9.2). If the sign of the state-conditional forward return is real, the mapping should be inverted (or replaced by a risk-budget rule that does not reduce net exposure in stress) and the whole programme's conclusion changes. If it is an artefact, the correct conclusion is that this data and this model class contain no exploitable regime information, and the programme should stop rather than grow.

**Pre-registered experiment (to be written into `EXPERIMENT_REGISTER.csv` as E7 before running):**

* *Hypothesis.* The volatility-ranked state differential in mean forward 20-day return is positive and stable: mean(rank 3 + rank 2) − mean(rank 0 + rank 1) > 0 in a majority of the 15 folds and under every one of four independent state specifications (K = 3 `rvd3`, K = 4 `rv2` as selected, K = 5 `rv2`, and K = 3 on `volatility_20` alone).
* *Estimator.* Filtered (never smoothed) probabilities; state-conditional means estimated inside each training window only; fold-level differentials aggregated with a stationary-bootstrap interval (mean block 20) and a **max-statistic across the four specifications** so that the specification search is priced in.
* *Decision rule, fixed in advance.* If the lower bound of the max-statistic 95 % interval exceeds 0, the effect is treated as real and an inverted/matched-exposure mapping is specified for a *prospective* test. If it straddles zero, the report's conclusion stands and no further state-based return forecasting is attempted on this dataset.
* *Economic test, only if the sign survives.* A rule setting exposure from state-conditional expected return with **mean exposure and turnover constrained to equal** the current vol-state rule, evaluated against the same three matched controls, so that a positive result cannot come from exposure reduction.
* *Prospective requirement.* The confirmatory evaluation uses only sessions after a fresh freeze, and the point estimate from this data is explicitly labelled exploratory.

### 10.9 Multi-testing, dependence and what this report cannot say

* The programme ran roughly 300 evaluated specifications in total (discovery and feature grids are logged in full in `EXPERIMENT_REGISTER.csv` and the per-fold CSVs). Selection used held-out density inside training windows precisely so that the *selection* is not fitted to the evaluation period, but a multiple-testing burden remains for every downstream claim.
* No result here is claimed as statistically significant after correction. The in-sample entropy/return association (Wald p = 0.057, one of 15 in-sample tests) is reported as an association, not a finding, and its OOS estimate is negative.
* Non-significance is not equivalence: the paired Sharpe intervals are wide (regime vol-state vs Trend 50 spans −0.334 to +0.325 annualised Sharpe), so the data cannot rule out economically meaningful differences in either direction. The negative evidence that *is* sharp comes from the exposure-matched controls (§9.2), which do not depend on the Sharpe's sampling error in the same way.
* Everything is conditional on: NIFTY price index (no dividends), 2012-01→2026-10, daily close, next-close execution with a one-session delay, 10 bps costs, a fixed 6.5 % cash rate, Gaussian-diagonal emissions, annual refits, and one asset. None of the conclusions transfers to other assets, frequencies or execution conventions without re-running the programme.


## 11. Verification

Every number above is produced by the single reference run **`research_outputs/study_20261030T111521Z/`** (`manifest.json` records the data hash `ea6dfffb…5f2ac5e4`, the config, seeds 2/42/7 and 1701, and package versions). Superseded runs are retained and identified in [`docs/VERIFICATION.md`](VERIFICATION.md), which also carries the implemented / executed / partially executed / not executed inventory, the eleven defects found (four of them fixed during the programme) and the list of claims this work does **not** support.

## 12. Reproduction

```bash
cd market-regime-platform
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
python -m pytest -q                     # 63 passed, 3 skipped (see verification)

# verified baseline (identical to the archived performance table)
python run.py --csv data/raw/nifty_index.csv --start 2012-01-01 \
  --execution-delay 1 --bootstrap-samples 1000 --output /tmp/baseline_check

# full research study (audit → discovery → ablations → emissions → predictive → allocation)
python -m regime_backtester.study --csv data/raw/nifty_index.csv \
  --start 2012-01-01 --output research_outputs --simulations 200 --seed 1701
```

Each study writes a timestamped directory (≈25 minutes) with `manifest.json` (data hash, config, seeds, package versions), all tables referenced above, and `EXPERIMENT_REGISTER.csv` — six experiments, of which the prospective holdout (E6) is explicitly recorded as **NOT EXECUTED**.
