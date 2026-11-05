# Task 2 Research Integration Contracts

**Contract package:** `research.contracts`
**Package version:** `task2-research-contract-v1`
**Experiment schema:** `task2-experiment-manifest-v1`
**Feature schema:** `f10-close-features-v1`
**Status:** executable validation boundaries only; no historical engine has been repaired or migrated.

## 1. Purpose and non-goals

These contracts are the machine-checkable boundary for later selective migration from immutable 1c source `c46541e9ab8611330489a920c46cdb00342931d5` into the f10 foundation. They do not fit models, rank research, allocate capital, or generate forecasts. A passing test establishes the documented invariant on real or synthetic fixtures, not predictive value, statistical validity, profitability, or prospective performance.

The modules are:

| Module | Contract |
| --- | --- |
| `data.py` | Canonical raw/parsed data identity and structural OHLC validation |
| `features.py` | Versioned f10 close-only RV/RVD formulas, warm-up, availability, and gaps |
| `model.py` | Model specifications, probability blocks, fit dispositions, density comparability, and causal selection evidence |
| `temporal.py` | Explicit target outcome ends, strict maturity purging, expanding folds, and delayed execution |
| `state.py` | Arbitrary state labels, occupancy, overlapping-training alignment, and descriptive characteristics |
| `experiment.py` | Immutable run directories, complete provenance, output hashes, collision/missing-artifact detection, and failure records |
| `controls.py` | Correctly named and thresholded control-matching diagnostics, without an allocation implementation |

## 2. Canonical data contract

### Identity and schema

`read_canonical_csv(path, expected_sha256=CANONICAL_DATA_SHA256)` reads bytes without modifying them and returns `CanonicalDataset(frame, provenance)`.

The preserved source is `research/data/nifty_index.csv`:

- raw SHA-256: `ea6dfffb93e5eabd8b6a2f96cd40d6b3ec5c7f47f2f9e6c0cbd3ca9a5f2ac5e4`;
- Task 2 parsed-record fingerprint: `826e89327af5b44d40c74e3ea9396a4c8f953db11493be4f7818c14f382b2be9`;
- exact columns/order: `Date, Close, High, Low, Open`;
- 4,684 rows, 2007-09-17 through 2026-10-22;
- raw line endings: CRLF.

The 1c root `nifty_index.csv` has raw SHA-256 `cf384a63c9137ec9b7f73d398c7ec5fc55ccdcccf89a514b824ad5341f409e59`, uses LF, and is parsed-equivalent. Raw identity is intentionally different. The parsed fingerprint hashes a canonical JSON list of ISO dates and `.17g` numeric values; it is a Task 2 logical-data fingerprint, not a historical hash and not a replacement for raw SHA-256.

### Required validation

`validate_ohlc_frame` requires:

1. exactly one each of the five required columns; canonical CSV also requires exact order;
2. nonempty, strictly increasing, unique, timezone-naive session dates; CSV text must be strict `YYYY-MM-DD`;
3. numeric, present, finite, strictly positive OHLC values;
4. `High >= max(Open, Close, Low)` and `Low <= min(Open, Close, High)`;
5. defensive copying and normalized date indexing.

It rejects missing values, duplicates, invalid dates, and OHLC-envelope violations. It does **not** certify vendor accuracy, adjustment/total-return semantics, exchange-calendar completeness, corporate actions, or licensing.

## 3. Feature contract

`build_contract_features(prices, family="rv" | "rvd")` returns `(feature_frame, manifest)`. Only preserved f10 RV/RVD columns are available; requesting another family raises an error.

For session close \(C_t\):

```text
daily_return[t]  = C[t] / C[t-1] - 1
volatility_20[t] = sample_std(daily_return[t-19:t+1], ddof=1) * sqrt(252)
drawdown_252[t]  = C[t] / max(C[t-251:t+1]) - 1       # RVD only
```

The pandas reference is exactly `Close.pct_change(fill_method=None)`, `rolling(20).std()`, and `Close / Close.rolling(252).max() - 1`. RV and RVD parity tests compare the actual f10 implementation values exactly.

| Column | Version | Input/lookback | First valid zero-based price row | Availability |
| --- | --- | --- | --- | --- |
| `daily_return` | `daily-return-f10-v1` | two closes / one interval | 1 | after close at `t` |
| `volatility_20` | `realized-vol20-f10-v1` | 20 returns | 20 | after close at `t` |
| `drawdown_252` | `drawdown252-f10-v1` | 252 closes | 251 | after close at `t` |

The feature manifest records formulas, ordered columns, annualization, simple-return semantics, `ddof=1`, warm-up, and missing-value policy. Twenty volatility inputs are returns, so 21 price rows are required. Warm-up rows remain `NaN`; no forward fill is performed. `complete_feature_rows` trims only the common leading warm-up and rejects every internal gap or nonfinite value.

## 4. Model output and fit contract

### Versioned specification

`ModelSpec` requires a nonempty name and `model_version`, feature family/version and ordered feature names, integer `state_count >= 2`, emission, covariance type, transformation, and nonnegative seed. State count is variable; no fixed three-state hierarchy is imposed.

### Probability semantics

`ProbabilityBlock` contains:

- strictly increasing, unique, timezone-naive dates;
- a finite nonnegative `N x K` matrix whose rows sum to one within `1e-10`;
- unique nonempty string `state_ids` matching the `K` columns;
- one explicit `InferenceKind`:
  - `TRAINING_FILTERED`: forward-only probabilities on fitting data;
  - `FILTERED`: generic forward-only probabilities;
  - `OOS_FILTERED`: forward-only probabilities for a later test block;
  - `SMOOTHED`: retrospective probabilities, never an OOS decision input.

This keeps fitting data, fitted parameters, training assignments, training probabilities, generic filtered probabilities, smoothed probabilities, and OOS filtered probabilities separate.

### Fit disposition

`FitRecord` carries a `ModelSpec`, training boundary, explicit `FitStatus`, convergence flag, parameters, optional typed probability blocks, and optional training assignments.

- `ACCEPTED` requires `converged=True`, fitted parameters, no fallback, and no rejection/failure reason.
- `NONCONVERGED` requires `converged=False` and a reason; `fallback_used` is explicit. It is never usable for OOS inference, even if diagnostic parameters/probabilities are retained.
- `REJECTED` requires a rejection reason, such as zero/rare occupancy.
- `FAILED` requires a failure reason, such as a numerical exception.

All attached blocks must have the declared kind and model state count. OOS dates must begin after training ends; training/OOS IDs must agree within a fit. `require_usable_oos` fails closed unless an accepted fit has an OOS-filtered block.

### Predictive density comparability

`PredictiveDensity` records dates, per-observation values, ordered feature names, `raw` or `scaled` space, `nats_per_observation` units, and whether the transformation Jacobian is included. `assert_comparable_density` requires identical ordered raw features, dimension, dates, units, raw space, and explicit Jacobian inclusion.

A Jacobian can account for a transformation of the **same** feature vector. It cannot make a two-dimensional density and a three-dimensional density comparable. Selection must use one raw feature vector and identical evaluation observations.

### Model selection

`SelectionScore` binds an outer fold, candidate, inner validation fold, validation end, outer test start, and score. `select_candidate_for_fold` rejects any validation end `>= outer_test_start` and uses only evidence tagged to that outer fold. Ties break deterministically by candidate ID. This forbids global post-hoc selection from later folds for earlier OOS predictions.

## 5. Temporal causality and target maturity

`TargetLabel` stores decision date, outcome end date, positive session horizon, and value. `forward_return_labels` computes:

```text
value[t] = Close[t+h] / Close[t] - 1
outcome_end_date[t] = session_date[t+h]
```

Trailing unknown outcomes are not fabricated. The f10-compatible purge is strict:

```text
eligible for training at test_start iff
    decision_date < test_start
and outcome_end_date < test_start
```

A label whose decision is in training but whose outcome ends on or after test start is excluded. `require_mature_labels` raises on any violation.

`FoldBoundary` requires `train_start <= train_end < test_start <= test_end`. `annual_expanding_folds` creates expanding annual test windows on the actual session index. `ExecutionTiming` requires `decision_date < execution_date < first_return_date`, preserving the delayed signal/trade/next-return gap.

## 6. State identity, occupancy, alignment, and description

State IDs are arbitrary local labels. Numerical IDs cannot be compared across refits without an explicit mapping.

`summarize_occupancy` reports, in the supplied column order and exactly once:

- hard count and hard fraction from `argmax`;
- mean posterior weight;
- rare status using configurable `rare_min_count` and `rare_min_fraction` (defaults 100 and 0.05, matching the f10 characterization heuristic, not a universal rejection rule).

Zero-occupancy states remain explicit with count zero. They are not removed or assigned a fake zero-volatility mean.

`align_training_states(reference, current)`:

1. accepts only `TRAINING_FILTERED` blocks;
2. requires equal state count and a nonempty intersection of training dates;
3. builds a hard-label contingency matrix on that overlap only;
4. uses SciPy Hungarian assignment to maximize matched training labels;
5. returns a one-to-one `current_to_reference` mapping, overlap start/end, contingency, agreement fraction, and method `training-hard-contingency-hungarian-v1`.

`apply_alignment` reorders current columns into reference order. Smoothed/OOS probabilities and forward returns are not alignment inputs. Permuted labels restore the same reference columns; nonoverlapping future rows cannot affect the mapping.

`posterior_weighted_characteristics` computes posterior-weighted means of measured variables and returns `None` when valid weight is zero. Such descriptions are contemporaneous unless a separately matured forward-outcome table is explicitly supplied by a later evaluation stage. Forward outcomes never determine state identity. Rare-state descriptions remain descriptive, not inferential.

## 7. Experiment provenance contract

### Required identity and records

`validate_manifest` requires:

- `schema_version` and immutable safe `experiment_id` (never `LATEST`);
- full source commit and/or Task 1 source-inventory SHA-256;
- dataset raw/parsed hashes and row count;
- ordered feature family/version/columns;
- consistent model version, feature version/names, state count, emission, covariance, transformation, and seed;
- chronological, nonoverlapping fold boundaries;
- seeds and explicit dependency versions;
- command, Python version, UTC start/finish timestamps;
- artifact-path-to-SHA-256 mapping;
- warnings and per-fit disposition records;
- `running`, `completed`, `partial`, or `failed` status.

Completed runs require a finish timestamp and at least one artifact. Accepted fit records require convergence; every unsuccessful fit needs a reason. A completed study containing rejected/failed fits must carry a warning. Failed experiments require a failure/warning record.

### Minimal complete example

The executable fixture is `tests/contracts/test_experiment_contract.py::manifest`. This equivalent JSON uses a synthetic payload, not a research result:

```json
{
  "schema_version": "task2-experiment-manifest-v1",
  "experiment_id": "synthetic_20261105T000000Z_deadbeef",
  "source": {
    "commit": "57ae0c238e497a059ce85f83da398477be705e8a",
    "source_inventory_sha256": "1111111111111111111111111111111111111111111111111111111111111111"
  },
  "dataset": {
    "raw_sha256": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
    "parsed_sha256": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
    "rows": 12
  },
  "feature_spec": {
    "family": "rv",
    "version": "f10-close-features-v1",
    "columns": ["daily_return", "volatility_20"]
  },
  "model_spec": {
    "name": "synthetic",
    "model_version": "fixture-model-v1",
    "feature_version": "f10-close-features-v1",
    "feature_names": ["daily_return", "volatility_20"],
    "state_count": 3,
    "emission": "gaussian",
    "covariance_type": "diag",
    "transformation": "training-zscore-with-raw-jacobian",
    "seed": 42
  },
  "folds": [{
    "fold_id": "fold_001",
    "train_start": "2020-01-01",
    "train_end": "2020-12-31",
    "test_start": "2021-01-01",
    "test_end": "2021-01-08"
  }],
  "seeds": [2, 42],
  "dependencies": {"numpy": "2.4.6", "pandas": "2.3.3"},
  "execution": {
    "command": "pytest synthetic",
    "python": "3.11.2",
    "started_utc": "2026-11-05T00:00:00Z",
    "finished_utc": "2026-11-05T00:00:01Z"
  },
  "artifacts": {
    "metrics/result.json": "f7862efad8e99454a367fa00895f995761e90cebc69eafed9b7f21b8c451e34f"
  },
  "warnings": [],
  "fit_records": [{
    "fit_id": "fit_001",
    "fold_id": "fold_001",
    "status": "accepted",
    "converged": true
  }],
  "status": "completed"
}
```

The declared artifact bytes are `b'{"observation":1}\n'`.

### Filesystem enforcement

`create_experiment` validates declared/actual artifact names and hashes before creating `base_dir / experiment_id`; directory creation uses `exist_ok=False` and files use exclusive `xb` mode. It never overwrites a collision or writes `LATEST`.

`verify_experiment` checks schema, exact declared-versus-actual regular file set, missing files, unrecorded files, and every SHA-256. Paths must be canonical relative POSIX paths without traversal. `record_failure` returns a failed manifest copy with a timestamp and warning; failures never become silent success.

A `LATEST` file in historical output may be a convenience pointer only. It is never an experiment identifier or provenance substitute.

## 8. Allocation-control matching diagnostics

No allocation rule is implemented. `ControlMatchDiagnostics` records exposure-KS distances, explicit causality, and absolute mean-exposure, annualized-turnover, and annualized-volatility differences.

`summary()` emits separate `mean_exposure_ks` and `median_exposure_ks`. `assert_control_matching` requires causal controls and thresholds for the named KS statistic and all three matching dimensions. It fails closed on noncausal input or any exceeded threshold. Preserving marginal exposure or autocorrelation through a circular shift is not evidence of causal timing or adequate matching.

## 9. Execution

From the integration root with the isolated environment:

```bash
/home/user/mra-task2-venv/bin/python -m pytest -q tests/contracts tests/regression
/home/user/mra-task2-venv/bin/python -m pytest -q tests/test_historical_archive.py tests/test_research_platform.py
```

The focused suite uses deterministic synthetic fixtures and immutable Git source blobs. It never refits the NIFTY research study. Exact 1c regression fixtures verify each source blob against `provenance/inventory/1c-c46541e-tracked-blobs.jsonl`; a missing Git object is a hard failure with an instruction to fetch the immutable commit without moving source refs.
