# HMM incremental-value study — executive summary

**Question:** Does an HMM regime overlay add meaningful value beyond a simple trend strategy and causal randomized controls?

**Finding:** The historical experiment does not establish a Sharpe improvement over trend alone. HMM + Trend had a lower observed maximum drawdown, but its CAGR was slightly lower. The evidence is exploratory: the strategy family and dates were previously examined, the matching lookback was chosen after inspecting preliminary diagnostics, and all paired Sharpe-difference intervals below include zero. None is a p-value or proof of equivalence.

## Sample and timing

- User-supplied NIFTY index OHLC, 2007-09-17 through 2026-10-22; SHA-256 `ea6dfffb93e5eabd8b6a2f96cd40d6b3ec5c7f47f2f9e6c0cbd3ca9a5f2ac5e4`.
- 3,632 common OOS return observations, 2012-01-05 through 2026-10-22. Fifteen expanding annual walk-forward folds, four fixed HMM configurations, two fit seeds per configuration.
- Signal at close **t**; execution at the **next session close**; first earned close-to-close return is after that execution. No next-open execution is assumed. The same-close baseline is separately retained and is optimistic.
- Long/cash, 10 bps one-way costs, 6.5% fixed annual cash. The HMM + Trend portfolio is the original 50/50 arithmetic blend, not a multiplicative gate. Index price returns exclude dividends, taxes and real-world market impact.

## Main delayed results

| Strategy | CAGR | Sharpe | Max drawdown | Mean exposure | Turnover / year |
| --- | ---: | ---: | ---: | ---: | ---: |
| Buy & Hold | 11.45% | 0.364 | 38.44% | 100.0% | 0.07 |
| Trend 50 | 9.26% | 0.286 | 20.93% | 68.4% | 12.90 |
| HMM Ensemble | 8.83% | 0.254 | 21.01% | 75.4% | 1.77 |
| HMM + Trend | 9.12% | 0.287 | 17.20% | 71.9% | 7.35 |

The paired 20-session block bootstrap gives **HMM + Trend minus Trend Sharpe +0.0014**, with 95% interval **[−0.1887, +0.1774]** (1,000 resamples). The interval includes zero. Recomputed aggregate fold metrics exactly equal full-series metrics; they are not averages of annual Sharpes.

## Randomized controls: 200 simulations each

The controls draw only from previously observed HMM exposures, except the initial current-exposure initialization. Here they use a **63-session rolling history** chosen after examining the poorer matching of the earlier full-history experiment. Block controls copy completed historical blocks; the matched random control uses a history-based redraw/hold rule. They do not guarantee exact distribution or turnover matches.

| HMM leg / control | Median net Sharpe | Empirical 5th–95th percentile | Blend exposure | Turnover / year | Median HMM-leg KS distance | Real Sharpe exceeds control |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Real HMM + Trend | 0.287 | — | 71.9% | 7.35 | 0 | — |
| Past-only shuffled | 0.226 | 0.189–0.263 | 71.8% | 13.88 | 0.014 | 99.5% |
| Past-only block shuffled | 0.293 | 0.277–0.315 | 71.7% | 7.64 | 0.025 | 31.0% |
| Exposure/turnover-approximate random | 0.298 | 0.262–0.350 | 71.2% | 7.42 | 0.076 | 36.5% |

The plain shuffle turns over much more than the real strategy. Its apparent net advantage should not be interpreted as an HMM information advantage without accounting for costs: the median real-minus-control **common-fee-schedule counterfactual** Sharpe is approximately **−0.001**. That equal-fee calculation is a diagnostic counterfactual, not an executable strategy.

Paired 95% intervals versus each **daily mean control portfolio** are [−0.019, +0.154] for the shuffled control, [−0.098, +0.094] for block shuffled, and [−0.095, +0.077] for matched random. These are not intervals versus one randomly selected path. Simulation percentiles and the real-above-control fractions are descriptive distributions, **not p-values**.

The preserved preliminary full-history matched control had a median Sharpe of **0.334** and a median HMM-leg KS distance of **0.310**, showing why an approximate matching diagnostic matters. The rolling lookback improves this observed match but was chosen after inspection, so the sensitivity comparison itself carries selection risk.

## Stress windows and assumptions

| Window | HMM + Trend total return | Trend total return | HMM + Trend max DD | Trend max DD |
| --- | ---: | ---: | ---: | ---: |
| 2013 | +1.29% | −0.58% | 9.95% | 11.43% |
| 2015–2016 | +3.56% | +7.41% | 13.05% | 12.49% |
| 2020 calendar year, COVID + recovery | +24.60% | +35.68% | 14.24% | 7.47% |
| 2022 | −0.63% | −4.86% | 13.37% | 14.39% |

Windows retain the continuous portfolio's holdings and costs, without forced liquidation. Recovery is measured within the window and censored if unrecovered. Annualized metrics in short windows are noisy; the pattern is not uniformly favorable to the HMM blend.

The fixed 6.5% cash assumption materially affects risk-adjusted metrics. With 0% cash, HMM + Trend / Trend Sharpe is **0.725 / 0.673**; with the lagged RBI 91-day auction-yield proxy it is **0.298 / 0.295**. The RBI series is an imperfect cash proxy, uses only strictly earlier auction dates, and is up to 29 calendar days old; 19 signal dates use rates older than 14 days. No baseline performance was overwritten.

## Model, data and holdout caveats

- Primary model state occupancy is 56.0%, 39.3%, and 4.6% by local training-volatility rank. Ranks are not stable identities across refits. A volatility-based Hungarian match is a heuristic, not proof of latent-state equivalence.
- The two-state models spend about 89–90% of signal days in their lower-volatility rank. None of 120 within-fit state-exposure pairs were identical to 1e−6; differentiated allocations alone do not establish predictive value.
- Sixty selected model/fold fits completed; the recorded count of selected-fit rows containing rejected seed attempts was zero. This count is not a count of individual rejected seeds. If every seed fails checks, the engine aborts rather than falling back to hindsight.
- Sortino uses downside deviations over **all** observations, with nonnegative excess returns contributing zero. Paired bootstrap samples common dates. PCA is descriptive, fitted before first OOS signal and not in the default model.
- There are 315 opens within one basis point of the prior close, including 122 with an intraday move above 1%; unusual early gaps/correlations warrant vendor verification, not automatic deletion. Weekdays with no rows can include exchange holidays.
- The 2023–2026 retrospective slice was already examined. The prospective freeze date is 2026-10-30 and decisions must occur **strictly later than that date** and later than the original data end. No qualifying data were supplied; prospective evaluation is pending.

## Artifacts

- Main run: [`run_20261030_081436_12ea5b`](../runs/run_20261030_081436_12ea5b/) — [full attribution report](../runs/run_20261030_081436_12ea5b/reports/hmm_attribution.md), [simulations](../runs/run_20261030_081436_12ea5b/attribution_simulations.csv), [folds](../runs/run_20261030_081436_12ea5b/fold_metrics.csv), [stress windows](../runs/run_20261030_081436_12ea5b/stress_periods.csv), [holdout freeze](../runs/run_20261030_081436_12ea5b/holdout_freeze.json).
- Sensitivity: [`run_20261030_080824_12346d`](../runs/run_20261030_080824_12346d/), all prior exposure history. Both runs retain their own core-source and input snapshots.
- Original results: [`results/nifty_2012_delayed`](../results/nifty_2012_delayed/) and [`results/nifty_2012_same_close`](../results/nifty_2012_same_close/). The delayed baseline was rerun before modifications and matched exactly at CSV precision, with byte-identical signals.
