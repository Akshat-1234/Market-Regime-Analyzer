# 91-day Treasury bill yield reference

`rbi_tbill_91_yields.csv` is a two-column subset of the RBI auction-series
compilation **Every auction of the 91-day Treasury bill since 1993**, Reserve
Bank of India (via the Data Bank), compiled by Measure of India, vintage
8 October 2026, <https://measure.thisindianlife.today/data/rates-tbill-91/>.
The compilation and layout are CC BY 4.0; figures retain the agency's terms.
Source CSV SHA-256: `e9162d1b391a5876ffe47a44d8d4a3d8eb7aaa02ff1155733b66d473f33392c0`.
The two columns are auction date and annualized cut-off yield in percent.

This is an imperfect cash-rate proxy, not a directly observed daily investable
cash return. The sensitivity study uses the most recent auction strictly before
the execution date and carries it forward at most 31 calendar days. Auction-day
use is deliberately prohibited because its publication time is not known.
The source stops on 2026-09-23; the last NIFTY observation uses a 29-day-old
rate. Report the age, staleness and approximation; never fill with future data.
