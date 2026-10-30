# Market Regime Backtester

A research-oriented Python project for evaluating a Gaussian hidden Markov model (HMM) as a long/cash risk overlay. It performs **annual walk-forward refits**, estimates **causal filtered** regime probabilities, blends the HMM overlay with a trend control, and compares it with simple benchmarks after trading costs. It also produces H1/H2 diagnostics, paired block-bootstrap intervals, charts, and an auditable run record.

> **Important reconstruction note:** The original `nifty_index.csv` has now been supplied and is included in `data/raw/`. The earlier repository, 14-model experiment scripts and exact configuration were not supplied. This four-model implementation is a documented reconstruction, not an exact reproduction of the earlier Sharpe 0.316 result. The separate sample data are **synthetic**. Research only, not investment advice.

## Quick start

Requires Python 3.10 or newer. From the extracted project directory:

```bash
# macOS / Linux
python -m venv .venv
source .venv/bin/activate

# Windows PowerShell, instead of the previous activation line:
# .\.venv\Scripts\Activate.ps1

python -m pip install -e ".[dev,download]"
python -m pytest -q
python run.py --synthetic --output results/synthetic
```

Open `results/synthetic/report.md`. For the supplied data, see [NIFTY_RESULTS.md](NIFTY_RESULTS.md). The dataset and results are fake and exist only to test the software. A previously generated synthetic report is in `examples/synthetic_run/`. You can also run the marked sample file explicitly:

```bash
python run.py --csv data/sample/synthetic_ohlc.csv --output results/sample_csv
```

### Use your own NIFTY data

1. The CSV you supplied is included as `data/raw/nifty_index.csv`. You can replace it with another file or use `--csv PATH`. The minimum format is:

   ```csv
   Date,Close
   2020-01-01,12182.50
   2020-01-02,12282.20
   ```

   Dates above are illustrative, not verified observations. Optional `Open,High,Low,Volume` are used for data-quality diagnostics or the optional PCA example. Sorted or unsorted rows are accepted; duplicate dates, missing/nonpositive closes and malformed numeric fields are rejected. Each row must represent one actual trading session; do not fill exchange holidays with duplicate prices.

2. Run (using the same 2012 start as the included validation):

   ```bash
   python run.py --csv data/raw/nifty_index.csv --start 2012-01-01 --output results/nifty
   ```

   The archive also includes the finished runs in `results/nifty_2012_same_close/` and `results/nifty_2012_delayed/`. Generated results and raw data are ignored by Git to prevent accidental publication; they are nevertheless included in the delivered ZIP.

   Alternatively download a Yahoo Finance snapshot (availability, rate limits and terms vary):

   ```bash
   python run.py download --ticker "^NSEI" --start 2007-01-01 --output data/raw/nifty_index.csv
   python run.py --csv data/raw/nifty_index.csv --output results/nifty
   ```

   `download --end YYYY-MM-DD` is **exclusive**, following Yahoo's convention. The run's `--end` is **inclusive**. Downloading requires the `download` extra. Yahoo was rate-limited during this rebuild; your original CSV is preferable and the data should be checked against the source.

3. Test a more conservative execution assumption:

   ```bash
   python run.py --csv data/raw/nifty_index.csv --start 2012-01-01 --execution-delay 1 --output results/nifty_delayed
   ```

The default uses a close-based signal and assumes it can be filled at that same close. This is an optimistic, potentially unexecutable convention, even though the signal earns only the *following* close-to-close return. A one-session delay executes at the following session's close and starts earning the return after that. It is a sensitivity test, not a simulation of actual auction orders or next-open fills.

Installed commands are also available as `regime-bt run ...` and `python -m regime_backtester ...`. `python run.py --help`, `python run.py download --help`, and `python run.py sample --help` show options. If run from the project root, `config/default.yaml` is loaded automatically; elsewhere the packaged Python defaults are used unless `--config` is specified. Paths are relative to the current working directory.

## What's implemented

- **Data and features:** close-to-close returns, 20-day volatility, 252-day rolling drawdown; additional optional features adapted from the supplied `feat.py`. All features are trailing. Input hashes and annual OHLC-quality checks are recorded.
- **HMM:** four fixed variants (2/3 states × returns/volatility, with/without drawdown), diagonal covariance, two seed attempts, annual refit on earlier data only. Standardization and optional PCA are train-only. Rejected fits stop the run if no seed succeeds; failures are not quietly replaced with hindsight.
- **Filtering and state calibration:** a log-space forward filter carries the last training posterior into the test block. States are sorted by training-weighted next-day volatility; exposures target 12% annualized volatility, capped at 100%. The four model exposures are averaged.
- **Strategy:** by default, 50% HMM ensemble + 50% 50-day trend signal. This is an average, **not** multiplication of the two signals. The trend indicator is the sign of the rolling mean return, equivalent to a positive t-statistic when volatility is positive.
- **Controls:** buy-and-hold, 50-day trend, 20-day momentum, MA-band and RSI reversion, Donchian breakout, and plain volatility targeting. The original scripts' MA-band concept is retained without their import-time demo/plot side effects.
- **Accounting:** long/cash, exact self-financing proportional trading costs, daily cash interest, fractional weights and drift-aware rebalancing; no terminal forced sale. Defaults are 10 bps per one-way traded notional and 6.5% annual cash rate, both configurable.
- **Evaluation:** performance, primary-regime occupancy/transition diagnostics (H1), conditional strategy results (H2), and paired circular moving-block bootstrap intervals for HMM + Trend minus three controls (H3).

The prior request to avoid concentration is addressed transparently: training fits are rejected if any argmax state has less than 2% occupancy by default, and the report shows OOS occupancy and effective state count. This is **not** a promise of balanced OOS regimes, and a genuine rare risk state should not be artificially forced to be common.

### Optional PCA experiment

```bash
python run.py --csv data/raw/nifty_index.csv --config config/pca_example.yaml --output results/pca
```

This optional example uses 16 features and requires `Open`, `High`, and `Low`; it is exploratory, not the default or a claim that PCA improves returns. It fits the scaler/PCA inside each training fold. Historical Open prices may be unreliable, particularly in early years, so check `data_quality.csv`. Different feature warm-ups may produce different test dates: use the same `--start` and `--end` when comparing configurations, and compare the resulting return calendars before interpreting differences.

## Configuration and output

Edit `config/default.yaml`, or supply a partial YAML file with `--config`; partial files override the built-in defaults. Common command-line overrides include:

```bash
python run.py --csv data/raw/nifty_index.csv \
  --start 2023-01-16 --end 2026-10-13 \
  --cost-bps 15 --risk-free 0.065 --execution-delay 1 \
  --bootstrap-samples 2000 --output results/sensitivity
```

`--start` is the first permitted **signal** date, provided enough training history exists. It does not discard earlier training observations. `--end` truncates the data inclusively. The previously discussed 2023–2026 period has already been examined, so it is **not an untouched holdout**. Freeze the design and use genuinely unseen data for a final holdout.

Every completed run writes:

| File | Contents |
| --- | --- |
| `report.md`, `figures/` | Human-readable summary, equity/drawdown and filtered probabilities |
| `performance.csv`, `daily_backtests.csv` | Summary and daily portfolio/turnover/cost detail |
| `signals.csv`, `daily_returns.csv`, `equity_curves.csv` | Decision-time signals and aligned realized outputs |
| `fits.csv`, `train_state_calibration.csv`, `train_transition_matrices.csv` | Train windows, convergence, state exposures and transition matrices |
| `regime_summary.csv`, `empirical_transitions.csv`, `regime_strategy_sharpe.csv` | H1/H2 descriptive diagnostics |
| `bootstrap.csv` | Paired Sharpe-difference intervals versus buy-and-hold, trend and vol target |
| `data_quality.csv`, `metadata.json`, `run_config.yaml` | Yearly checks, input/core-code hashes, dates, dependency versions and exact config |

Bootstrap intervals quantify uncertainty conditional on the chosen setup; they do **not** correct for the many variations explored previously. An interval crossing zero is not proof of equivalence. Use multiple markets and genuinely new data before making performance claims.

## Structure

```text
market-regime-backtester/
├── config/                 # Default and optional PCA configuration
├── data/raw/               # User-supplied NIFTY CSV (gitignored)
├── data/sample/            # Clearly marked synthetic OHLC example
├── docs/                   # Methodology, data and reproduction notes
├── examples/synthetic_run/ # Pre-generated synthetic result (not market evidence)
├── validation/             # Summary of a separate public-data validation
├── results/                # Included NIFTY runs and future local runs; gitignored
├── src/regime_backtester/  # Data, features, HMM, execution, reporting, CLI
├── tests/                  # Unit + full-pipeline no-look-ahead tests
├── pyproject.toml
├── Makefile
└── run.py
```

See [methodology](docs/METHODOLOGY.md), [data sources](docs/DATA.md) and [independent validation](validation/independent_nifty/README.md). The public-data validation is separate from your supplied original dataset. No licence is specified for this reconstructed code; select one before redistributing.
