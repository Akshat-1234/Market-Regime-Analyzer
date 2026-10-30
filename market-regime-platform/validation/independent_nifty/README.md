# Independent NIFTY snapshot: software validation

This is an **independent third-party snapshot**, not the original `nifty_index.csv` from the earlier conversation. This validation predates the addition of the user-supplied CSV; its recorded code hash refers to the earlier reporting version. It was used to exercise the rebuilt pipeline on real-looking historical data. It is not an exact reproduction of the old 14-model experiment, nor an untouched out-of-sample test of a pre-registered strategy. The earlier conversation explored many variants and examined the later years. Results are research-only and can change with data source, execution and assumptions.

## Data provenance

- Public repository: [kaifahmedsiddiqui-47/nifty50-direction-forecasting](https://github.com/kaifahmedsiddiqui-47/nifty50-direction-forecasting), which describes its file as Yahoo Finance `^NSEI` data. The data have **not** been independently verified against NSE.
- Pinned source: <https://raw.githubusercontent.com/kaifahmedsiddiqui-47/nifty50-direction-forecasting/b366b4a55d6863f4641d559e58e24131ce0a33b2/nifty50_raw.csv>
- SHA-256: `8c1f1ca033c7e811fcee8a2f0f390dbf0a94fc765d84f810c7cb02e68724dd5b`
- Input: 4,121 daily rows, 2010-01-04 through 2026-10-13. Default features use Close, not Open. `data_quality.csv` summarizes, but cannot certify, the data.
- The raw data are **not bundled**: redistribution permission was not established. Results here are aggregated summaries, not the input time series.

## Same-close assumption, default configuration

First signal 2013-01-31; realized returns 2013-02-01 through 2026-10-13, 3,365 observations. The default uses a 4-model HMM volatility ensemble, a 50/50 average with the trend control, 10 bps one-way cost, 6.5% annual cash rate and 252 sessions/year. The same-close assumption is optimistic: a strategy that waits for the final close cannot guarantee a fill at that close.

| Strategy | CAGR | Sharpe | Max drawdown |
| --- | ---: | ---: | ---: |
| Buy & Hold | 10.43% | 0.306 | 38.44% |
| Trend 50 | 9.19% | 0.284 | 20.12% |
| Vol Target | 7.85% | 0.166 | 19.54% |
| HMM Ensemble | 8.31% | 0.201 | 27.49% |
| HMM + Trend | 8.85% | 0.259 | 17.83% |

For HMM + Trend minus Buy & Hold, the observed Sharpe difference is -0.047; the 95% paired 20-session block-bootstrap interval is approximately **[-0.287, +0.187]** (`same_close_bootstrap.csv`, 1,000 resamples). An interval crossing zero does not prove that the strategies are equivalent, and the interval does not adjust for past experimentation.

## One-session delayed execution sensitivity

This replays the same decision-time signals, executing each one at the **following** session's close and earning the return after that. The first return date moves forward one session; compare the calendar as well as the assumptions.

| Strategy | CAGR | Sharpe | Max drawdown |
| --- | ---: | ---: | ---: |
| Buy & Hold | 10.48% | 0.309 | 38.44% |
| Trend 50 | 8.79% | 0.248 | 20.93% |
| Vol Target | 8.03% | 0.179 | 19.76% |
| HMM Ensemble | 8.41% | 0.208 | 27.57% |
| HMM + Trend | 8.69% | 0.243 | 17.76% |

The delayed HMM + Trend minus Buy & Hold Sharpe difference is -0.066, with bootstrap interval approximately [-0.314, +0.167]. This is not evidence of a significant Sharpe edge. No assumption here models taxes, spread variation, market impact, real orders, dividends in a price-only index, or changing funding rates.

## Reproduce (if you have permission to use the data)

From the project root, after installation:

```bash
URL='https://raw.githubusercontent.com/kaifahmedsiddiqui-47/nifty50-direction-forecasting/b366b4a55d6863f4641d559e58e24131ce0a33b2/nifty50_raw.csv'
curl -fL "$URL" -o data/raw/nifty_external.csv
python -c "import hashlib; print(hashlib.sha256(open('data/raw/nifty_external.csv','rb').read()).hexdigest())"
python run.py --csv data/raw/nifty_external.csv --source-url "$URL" --output results/independent
python run.py --csv data/raw/nifty_external.csv --source-url "$URL" --execution-delay 1 --output results/independent_delayed
```

See `metadata.json` for the versions and hash of the validated run, and `run_config.yaml` for its parameters. The input path in the config is from the original validation environment; override it with `--csv` as above. Dependency or numerical-library versions can cause small changes.
