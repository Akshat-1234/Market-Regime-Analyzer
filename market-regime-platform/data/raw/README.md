# Raw data

`nifty_index.csv` is the file provided by the user and is included in the
archive (4,684 observations, 2007-09-17 through 2026-10-22). At minimum the
pipeline needs `Date,Close`. See `docs/DATA.md` for its hash and caveats.

Raw data is ignored by Git to avoid accidental redistribution. Check your
permissions before publishing a dataset; add it deliberately if appropriate.
`python run.py --synthetic` works without real data.
