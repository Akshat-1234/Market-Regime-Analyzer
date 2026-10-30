# Baseline audit (before platform modifications)

The provided `market-regime-backtester-with-nifty.zip` was extracted without
changing the original dataset, strategies or archived results. The declared
Python dependencies were installed and the original test suite ran: **21 passed**.

The saved one-session-delayed experiment was independently re-executed using:

```bash
python run.py --csv data/raw/nifty_index.csv --start 2012-01-01 \
  --execution-delay 1 --bootstrap-samples 1000 --output /home/user/baseline-audit
```

All reported performance fields were exactly equal to the archived
`results/nifty_2012_delayed/performance.csv` at CSV precision; its complete
`signals.csv` was byte-for-byte identical. Data SHA-256:
`ea6dfffb93e5eabd8b6a2f96cd40d6b3ec5c7f47f2f9e6c0cbd3ca9a5f2ac5e4`.

| Strategy | CAGR | Sharpe | Max drawdown |
| --- | ---: | ---: | ---: |
| Buy & Hold | 11.45% | 0.364 | 38.44% |
| Trend 50 | 9.26% | 0.286 | 20.93% |
| HMM + Trend | 9.12% | 0.287 | 17.20% |

The original `HMM + Trend` is an arithmetic **50/50 average**, not a
multiplication or gating of exposure. `HMM × Trend` in some descriptions is
therefore a misleading label. We retain the exact original strategy and call
it **HMM + Trend** throughout. Same-close and one-session-delayed results stay
separate; the original same-close convention is an optimistic fill assumption.

## Audit findings

- Original forward probabilities and preprocessing are causal at test time;
  historical decisions were tested against truncation and future mutation.
- Sortino correctly uses all observations, assigning zero downside to
  nonnegative excess returns.
- Gaussian HMM failures, insufficient occupancy, bad covariance and
  nonconvergence are rejected; no accepted seed means the run fails closed.
- State ranks are re-sorted by train-weighted next-day volatility each refit;
  equal rank is not proof of identical latent economic states.
- Bootstrap is paired by return date, and `fraction_le_zero` is a bootstrap
  proportion, not a conventional p-value. Prior strategy selection is unadjusted.
- The original fixed 6.5% annual cash rate is a simplification. A separate
  historical auction-yield sensitivity is added without changing the baseline.
- The initial project did not isolate HMM information, expose fold/stress
  diagnostics, provide freezeable prospective holdout tooling, or include a UI.
- The previously quoted 14-model experiment cannot be recreated because its
  source and exact config were not in the archive.
