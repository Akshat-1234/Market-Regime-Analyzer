# Walk-forward regime backtest

**SYNTHETIC DATA: these figures do not describe NIFTY or any real market.**

Research only; not investment advice. This is a reconstruction, not an exact rerun of the unavailable earlier 14-model implementation.

## Data and setup

- Source: `synthetic`; path: `generated in memory (seed=314159, n=2200)`; SHA-256: `2dbacf1f11fa2b6f9073690df06e1d93c45c3fe924a23d3df4e9fbc72f2e6423`.
- Source URL, if provided: not recorded.
- Data used: 2008-01-01 to 2016-06-06 (2200 rows).
- OOS signal dates: 2010-11-23 to 2016-06-06; realized return dates: 2010-11-24 to 2016-06-06 (1444 observations).
- Expanding training window, annual refits, at least 504 feature-valid days; rolling maximum: None.
- Primary model: `rvd_3`; 4 pre-specified model(s); state ordering is by **training weighted next-day volatility**.
- Target vol: 12.0%; HMM/trend blend: 50%/50%.
- Cash earns 6.50% annualized; 10 bps per one-way traded notional; 252 trading days/year.
- **Execution:** Same-close fill is assumed after observing that close; this is optimistic and may not be practically executable. Rerun with `--execution-delay 1` for a more conservative next-close sensitivity test.

## Input quality

`data_quality.csv` lists yearly close-return volatility and, if Open is available, its coverage, OHLC out-of-range observations, overnight/intraday volatility and the fraction of opens essentially equal to the previous close. These checks flag investigation candidates; they do not certify data quality. Early Open quotes can be unreliable. The default models use Close only.

## Performance

| Strategy | CAGR | Volatility | Sharpe | Sortino | Max DD | Calmar | Exposure | Turnover/yr |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Buy & Hold | 18.33% | 21.10% | 0.60 | 0.89 | 22.35% | 0.82 | 100.0% | 0.17 |
| Trend 50 | 10.44% | 17.60% | 0.29 | 0.43 | 30.79% | 0.34 | 64.9% | 14.13 |
| Momentum 20 | 10.40% | 16.36% | 0.30 | 0.43 | 23.50% | 0.44 | 58.4% | 25.99 |
| MA Reversion | 8.18% | 10.94% | 0.20 | 0.30 | 18.67% | 0.44 | 26.9% | 11.16 |
| RSI Reversion | 12.67% | 9.51% | 0.64 | 1.07 | 11.03% | 1.15 | 19.6% | 9.07 |
| Donchian | 11.31% | 14.21% | 0.38 | 0.55 | 17.63% | 0.64 | 43.1% | 6.45 |
| Vol Target | 13.94% | 13.24% | 0.58 | 0.82 | 11.65% | 1.20 | 73.0% | 4.97 |
| HMM Ensemble | 12.68% | 12.60% | 0.51 | 0.73 | 11.98% | 1.06 | 67.6% | 2.78 |
| HMM + Trend | 11.72% | 14.30% | 0.41 | 0.59 | 18.21% | 0.64 | 66.2% | 8.45 |

Max DD is a positive magnitude; turnover is one-way traded notional divided by portfolio value, annualized. Fractional targets rebalance daily and their turnover includes weight drift. Initial entry costs are included; no artificial terminal liquidation. Sharpe uses daily excess returns over the cash rate; CAGR is annualized by trading observations. Index price returns omit dividends unless the input is a total-return series.

![Equity and drawdowns](figures/equity_drawdown.png)

## H1 — descriptive regimes

Labels use the primary model's probability at each **decision close**; outcomes below are the market returns over the interval held after execution. Run lengths and occupancy describe the observed rank labels, not evidence that a distinct underlying economic regime exists. The effective number of occupied states is 2.59; the largest rank covers 44.6% of intervals. Ranks are recalibrated at every refit and can change meaning across years.

| Volatility rank | Days | Occupancy | Mean run | Held-interval mean | Held-interval vol/yr |
| --- | --- | --- | --- | --- | --- |
| 0 | 213 | 14.8% | 23.7 | -0.002% | 14.4% |
| 1 | 587 | 40.7% | 53.4 | 0.037% | 14.9% |
| 2 | 644 | 44.6% | 42.9 | 0.136% | 26.9% |

`train_transition_matrices.csv` contains the fitted matrices per refit; `empirical_transitions.csv` summarizes adjacent OOS rank labels, including boundaries between refits.

![Primary filtered probabilities](figures/regime_probabilities.png)

## H2 — conditional strategy results

See `regime_strategy_sharpe.csv` for post-cost Sharpe and sample size by decision-time regime. These are descriptive, conditional ex-post comparisons, not a significance test or an investable per-regime policy. The strategies have shared market exposure; small states can be highly unstable.

## H3 — paired Sharpe difference: HMM + Trend minus control

Circular moving-block percentile bootstrap, 20-day blocks, 95% intervals, seed 42. The same dates are sampled jointly for both strategies.

| Control | Observed Δ Sharpe | Block-bootstrap interval | Fraction Δ ≤ 0 | Samples |
| --- | --- | --- | --- | --- |
| Buy & Hold | -0.199 | [-0.520, +0.130] | 87.2% | 1000 |
| Trend 50 | +0.112 | [-0.095, +0.320] | 14.8% | 1000 |
| Vol Target | -0.171 | [-0.526, +0.189] | 82.4% | 1000 |

The fraction at or below zero is a bootstrap proportion, **not** a p-value. An interval containing zero does not prove equality or equivalence. Intervals do not correct for the many strategies tried in the previous conversation, hyperparameter choice, nonstationarity or data snooping.

## Important limitations

1. This rebuild uses a documented four-model volatility-target ensemble; the prior 14-model ensemble's code and configuration were not supplied. Do not compare these figures as an exact reproduction.
2. The prior discussion tested many variants and examined 2023–2026, so that period is not an untouched holdout. Freeze the design and evaluate on genuinely unseen data and other markets.
3. Yahoo or other index quotes can contain inaccurate historical OHLC, revisions, missing dates or corporate-action issues. Validate against the provider, and use an investable total-return proxy, realistic fees/taxes/slippage and an appropriate cash/funding rate.
4. A Gaussian HMM can overfit, has arbitrary labels, and filtered probabilities are model-dependent—not guarantees. Failed or poorly occupied fits are rejected; see `fits.csv`.
5. A drawdown reduction or historical Sharpe does not establish future alpha. No leverage, shorting, market impact, taxes, dividends, intraday execution or India VIX/FII features are modelled by default.
