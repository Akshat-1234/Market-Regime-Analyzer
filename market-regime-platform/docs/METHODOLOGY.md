# Methodology and audit notes

## Timeline: information, fitting and execution

1. Data are validated, sorted and reduced to the same contiguous feature-valid calendar across all HMM specifications. No missing rows are imputed. Every feature uses information available by the current close.
2. After a configurable minimum number of valid **training** observations and any requested start date, the first OOS signal is produced. The first available session of each later calendar year triggers a new refit. Training ends strictly before that signal date. The window is expanding unless `max_train_days` sets a rolling limit. Earlier OOS observations may legitimately enter a later refit's training window, after they have occurred.
3. Each model fits `StandardScaler`, optional PCA and Gaussian HMM using training observations only. Different initial seeds are checked; the best in-sample log-likelihood among converged, numerically valid fits satisfying the minimum training state occupancy is used. A max-iteration stop alone is not counted as convergence. There is no OOS model selection or silent fallback.
4. For HMM filtering, `α_t(j) ∝ emission_j(x_t) × Σ_i α_(t-1)(i) A_ij`. The final filtered posterior from the training window seeds the first test observation. No Viterbi path or forward-backward smoothing is used as a trading signal. A fitted model is held fixed for the block; only its filtered posterior evolves.
5. Calibrate each state's volatility from training-only pairs: the state probability at training date `t`, weighted against the **next** close-to-close return at `t+1`. The last train date is excluded from calibration because its next return is outside training. Sort states by this estimated volatility. For state `j`, use `w_j = min(1, target_vol / max(state_vol_j, volatility_floor))`. The model's exposure is `Σ_j α_t(j) w_j`; ensemble exposure is the simple average over configured models.
6. By default the final target is `0.5 × HMM exposure + 0.5 × trend exposure`. Both are calculated at close `t`. With `execution_delay_sessions=0`, the simulation assumes a fill at close `t` and earns the return from close `t` to close `t+1`. This is a close-fill idealization, **not** an executable post-close order. With `execution_delay_sessions=1`, the target is filled at close `t+1` and earns the return from `t+1` to `t+2`. The model does not use next-open prices. The last unobservable-return signal is not traded.

### Example

If a 0.7 target is computed on Monday's close, default execution assumes trading at Monday's close and applies 0.7 exposure to Tuesday's close-to-close return. With a one-session delay it trades on Tuesday's close and applies 0.7 to Wednesday's return. All benchmarks use the same convention and dates. A signal using Monday's close cannot realistically guarantee a Monday closing fill; run the delayed sensitivity.

## Accounting

Let pre-trade wealth be `W`, risky holdings `A`, target risky weight `w`, proportional one-way cost `c`, and signed trade notional `Δ`. To hit the target *after costs* while remaining self-financing,

```text
Δ = (wW − A) / (1 + wc)   if buying
Δ = (wW − A) / (1 − wc)   if selling
cost = c × |Δ|
```

After trading, risky and cash holdings accrue the market return and daily cash return `(1 + annual_rf)^(1/periods) − 1`. The next actual weight is allowed to drift before rebalancing. Costs apply to the initial purchase and every rebalance, including drift-driven trades; no forced liquidation is assumed on the last date. Long/cash targets only: no leverage or shorts. The model omits taxes, market impact, discrete lot size, spread variation, intraday fill risk, financing differences and dividends in a price-only index.

## Baselines

- **Buy & Hold:** target 1.0.
- **Trend:** hold if rolling mean of the past 50 daily returns is positive. For positive standard deviation its t-statistic has the same sign. On a perfectly flat window it is cash.
- **Momentum:** hold if the 20-day price change is positive.
- **MA Reversion:** enter below 98% of the 20-day moving average; exit at or above it. Signal is stateful.
- **RSI Reversion:** simple rolling RSI(14), enter below 30 and exit at or above 50. Signal is stateful.
- **Donchian:** enter above the *prior* 50-session close high and exit below the *prior* 20-session close low.
- **Vol Target:** `min(1, 0.12 / trailing_20d_annualized_vol)`, invested if volatility is exactly zero. No leverage.

The configurable trend, momentum and MA windows can differ from these defaults. RSI and Donchian windows are fixed in code. First OOS dates are constrained to occur after baseline warm-ups.

## Interpretation of metrics and hypotheses

- CAGR uses `n / 252` years (or the configured annualization). Volatility and Sharpe are annualized from daily post-cost returns; Sharpe subtracts the daily cash rate. Sortino uses the root-mean-square of negative daily excess returns. Max drawdown includes the initial capital and is reported as a positive magnitude; Calmar is CAGR divided by max drawdown.
- Mean exposure is the time average of target weights. Turnover/year is the sum of absolute traded notional / pre-trade wealth, scaled to 252 sessions. `total_cost_fraction_sum` sums daily fractions, which is descriptive rather than an exact compounded performance drag.
- H1 reports occupancy, run lengths and subsequent held-interval market behavior for the **primary model's** decision-time rank labels. Ranks are relabelled on each refit; equal ranks across refits need not be identical economic states. Fitted transitions and empirical OOS transitions are distinct. The effective count is `1 / Σ occupancy²`. These descriptive numbers do not prove regimes are structural or stable.
- H2 conditions each strategy's post-cost return on the primary model's decision-time rank. Small samples and conditional selection make the table noisy; it is not an independently trained regime-specific policy or significance test.
- H3 is a paired circular moving-block percentile bootstrap for Sharpe differences. The same blocks of dates are used for both strategies. `fraction_le_zero` is a bootstrap fraction, **not** a p-value. The method assumes enough local stationarity and does not correct for data snooping, multiple comparisons, model selection or structural change.

## Limitations and robustness

The original CSV is now supplied, but the exact 14-model ensemble and earlier implementation were not, so this implementation cannot establish that the previously quoted result is reproducible. The final 50/50 idea was chosen after examining many experiments, including 2023–2026, and should not be marketed as a clean holdout result. Try a truly unseen period, a different index, different data vendor and realistic fills/costs. Data revisions, errors, nonstationarity, state misidentification and transaction costs can overturn findings.

HMM emissions are called through `hmmlearn`'s private `_compute_log_likelihood` because the library lacks a public emission-density API; the package version is constrained and the filter is tested against a hand-computed recursion. PCA is optional and fitted only inside each training window. The supplied PCA design uses Open-based features that may be flawed; the default avoids Open entirely.
