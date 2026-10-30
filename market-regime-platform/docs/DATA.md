# Data sources and provenance

## Your data

The user-supplied `nifty_index.csv` is included in `data/raw/` (4,684 rows, 2007-09-17 through 2026-10-22; SHA-256 `ea6dfffb93e5eabd8b6a2f96cd40d6b3ec5c7f47f2f9e6c0cbd3ca9a5f2ac5e4`). The prior chat described the source as Yahoo Finance `^NSEI`; this has not been independently verified. Pass `--csv PATH` for another file. Required columns are `Date` and `Close`; column names are case-insensitive and whitespace is ignored. To use a different column such as `Adj Close`, set `data.price_column` in a YAML config. Be consistent about index price vs total-return vs adjusted series.

The user-supplied NIFTY file is included in the delivered archive; raw files are gitignored to avoid accidental publication, so check data rights before committing them. The marked `data/sample/synthetic_ohlc.csv` and all figures in `examples/synthetic_run/` are simulated. `Data_Source=SYNTHETIC` is recorded in the sample file so the loader marks its reports as synthetic.

## Yahoo Finance

`python run.py download --ticker "^NSEI" --start 2007-01-01` uses the optional `yfinance` package and records a normalized daily CSV. The downloader requests unadjusted `Close`, explicitly disables auto-adjustment, and uses Yahoo's exclusive `--end` date. Availability, historical data revisions, rate limits and licensing terms may change. Verify the resulting prices, dates and source permissions independently. This sandbox received HTTP 429 from Yahoo during the rebuild; the download command was tested with a mocked response, not a successful live Yahoo fetch.

## Independent validation snapshot

A separate public CSV was used for a software check, not as a replacement for the supplied original data. Its provenance, hash, summarized results and limitations are in [validation/independent_nifty](../validation/independent_nifty/README.md). It is not bundled because its redistribution terms were not established. You can fetch it directly from its public source if your use is permitted. This third-party snapshot is itself described as Yahoo-derived and has not been independently certified against NSE.

## Validation and caveats

Duplicate dates and invalid Close values cause errors. Optional OHLC fields are checked for numeric/positive values and `High >= Low`, but the pipeline cannot guarantee complete exchange calendars or validate a vendor's historical adjustments. `data_quality.csv` is diagnostic, not a certification: unusually small overnight gaps or unusually high close/intraday correlation may merit investigation, but can also have benign explanations. Returns should not be forward-filled across missing sessions. The default models use Close-derived features only.
