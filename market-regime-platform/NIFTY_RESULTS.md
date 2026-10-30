# Results on the supplied NIFTY CSV

These results use the user-supplied `data/raw/nifty_index.csv` (SHA-256 `ea6dfffb93e5eabd8b6a2f96cd40d6b3ec5c7f47f2f9e6c0cbd3ca9a5f2ac5e4`). The input has 4,684 observations from 2007-09-17 to 2026-10-22. The previous conversation's exact 14-model experiment and configuration were not provided; this is the reconstructed **four-model** ensemble, not an exact reproduction of the earlier results.

## More conservative execution: one-session delay

The first OOS signal is 2012-01-03; returns are measured from **2012-01-05 to 2026-10-22** (3,632 observations). A decision at close `t` is executed at the next session's close; the strategy earns the following close-to-close return. This is not a simulation of next-open orders.

| Strategy | CAGR | Sharpe | Max drawdown | Calmar |
| --- | ---: | ---: | ---: | ---: |
| Buy & Hold | 11.45% | 0.364 | 38.44% | 0.30 |
| Trend 50 | 9.26% | 0.286 | 20.93% | 0.44 |
| Vol Target | 8.88% | 0.246 | 19.76% | 0.45 |
| HMM Ensemble | 8.83% | 0.254 | 21.01% | 0.42 |
| HMM + Trend | 9.12% | 0.287 | 17.20% | 0.53 |

The HMM + Trend portfolio had less historical max drawdown than Buy & Hold in this run, but lower CAGR and Sharpe. Its Sharpe is also very close to the simple trend baseline; this does **not** establish an HMM edge.

The paired 20-day block-bootstrap 95% interval for the HMM + Trend Sharpe difference is **[-0.339, +0.191]** versus Buy & Hold and **[-0.189, +0.177]** versus Trend 50 (1,000 resamples). These intervals include zero; that does not prove equality, and they do not correct for the extensive earlier experimentation.

## Same-close execution sensitivity

This convention uses a signal based on the final close and assumes a fill at that same close. It is optimistic and may not be executable. The first return is 2012-01-04, one session earlier than in the delayed run.

| Strategy | CAGR | Sharpe | Max drawdown | Calmar |
| --- | ---: | ---: | ---: | ---: |
| Buy & Hold | 11.42% | 0.362 | 38.44% | 0.30 |
| Trend 50 | 9.55% | 0.313 | 20.12% | 0.47 |
| Vol Target | 8.74% | 0.236 | 19.54% | 0.45 |
| HMM Ensemble | 8.51% | 0.228 | 20.87% | 0.41 |
| HMM + Trend | 9.11% | 0.289 | 17.39% | 0.52 |

Both runs use a 50/50 average of HMM and trend exposures, a 6.5% annual cash rate, 10 bps one-way cost, 252 sessions per year, and annual expanding-window refits. The historical NIFTY price series is not an investable total-return instrument; taxes, dividends, spreads, market impact and changing cash rates are not modeled.

## State concentration and data quality

In the delayed run the primary three-state model's rank occupancies are **56.0%, 39.3%, and 4.6%** (effective state count 2.12). So the model is still concentrated in two ranks; there is no claim that the states are balanced. State ranks are recomputed after every refit and should not be interpreted as identical economic states across all years.

The supplied OHLC file has no missing prices or duplicate dates under the loader's checks. Its early-year overnight-gap volatility is unusually small relative to intraday volatility; investigate the Open data with the vendor before relying on Open-based features. The default HMM features use Close only.

The 2023–2026 period was already inspected during the earlier strategy search and is **not an untouched holdout**. The drawdown result is an observation for this particular historical path, not a guarantee of future risk reduction or profitability.

## Full output and reproduction

- [Delayed execution report](results/nifty_2012_delayed/report.md)
- [Same-close report](results/nifty_2012_same_close/report.md)
- Each folder includes daily returns, decision signals, positions, costs, regime tables, bootstrap intervals, model fit details, quality checks and charts.

After installing the project dependencies:

```bash
python run.py --csv data/raw/nifty_index.csv --start 2012-01-01 --execution-delay 1 --output results/nifty_2012_delayed
python run.py --csv data/raw/nifty_index.csv --start 2012-01-01 --output results/nifty_2012_same_close
```
