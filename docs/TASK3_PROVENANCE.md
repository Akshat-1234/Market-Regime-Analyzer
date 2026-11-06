# Task 3 — Source and Numerical Provenance

## 1. Immutable references

| Role | Commit/path | Verification |
|---|---|---|
| HMM numerical authority | `c46541e9ab8611330489a920c46cdb00342931d5:market-regime-platform/src/regime_backtester/emhmm.py` | Exact Git blob; SHA-256 `181d251fb8b3b78c907c6518a1714898041dbcb048275f82bd5dd308c2d1f6c9` |
| Discovery/fallback boundary | Same 1c commit, `market-regime-platform/src/regime_backtester/discovery.py` | Exact Git blob; SHA-256 `c80ff9130f18106f2e354ed2a5c34d34111ad1d78d2682d0bab828518824fe27` |
| Historical study manifest | Same 1c commit, `market-regime-platform/research_outputs/study_20261030T111521Z/manifest.json` | Exact Git blob; SHA-256 `c59d7e8d9119e4b23ef988b70e55e6b4c4fdd3f3593b2742412b55321844de6b` |
| Feature/model/state contracts | `d9ea5e6122922312958fb6eb0d2370eb2275b63e` | Existing Task 2 modules reused without modification |
| Feature lineage | `9bb7f92d5785462462971d0479595c1d4166868c` | Existing Task 2 feature contract and tests reused |
| Canonical CSV | `research/data/nifty_index.csv` | Raw SHA-256 `ea6dfffb93e5eabd8b6a2f96cd40d6b3ec5c7f47f2f9e6c0cbd3ca9a5f2ac5e4` |

The three historical files above are verbatim copies of tracked 1c Git blobs. `provenance/task3_migration_manifest.json` separately records their provenance kind and embeds the measured raw/parsed canonical CSV identity under `canonical_input`; it does not invent a historical tracked data manifest. No incomplete historical manifest was silently repaired.

## 2. Selective migration map

| Original 1c behavior | Task 3 destination | Disposition |
|---|---|---|
| `emission_logprob`, Mahalanobis/density arithmetic | `research/hmm/emissions.py` | Migrated; valid-input arithmetic retained |
| `_lse`, `_log_forward`, `filter_causal` | `research/hmm/forward_backward.py`, `parameters.py` | Migrated; explicit causal API and continuation state |
| KMeans initialization and EM loop | `research/hmm/em.py` | Migrated; original seed, covariance, sticky, cap, tolerance, and dof grid |
| Internal backward/log-gamma/xi calculations | `forward_backward.py`, `inference.py` | Made explicit and separately testable |
| Original fitted tuple/dict outputs | `parameters.py`, `adapter.py` | Validated fit object and Task 2 contract blocks |
| Ad hoc model persistence | `serialization.py` | New deterministic JSON with schema/engine/source versions and payload hash |
| Discovery caller, model selection, nonconverged fallback | Excluded | Not migrated; no discovery or Task 4 behavior |
| Allocation, forecasts, backtests, dashboard, E7 | Excluded | No implementation or validation claim |

The original `fit_hmm` signature is retained as a convenience wrapper over `EMConfig`. The refactored functions separate initialization, E-step, M-step, filtering, smoothing, and persistence so each can be verified independently.

## 3. Exact parity evidence

Regenerate with:

```bash
python scripts/verify_task3_parity.py --output provenance/task3_parity.json
```

The command loads `emhmm.py` directly from the exact Git object, verifies its bytes against the Task 1 inventory, executes both implementations on identical deterministic inputs, and fails if any required original comparison differs bitwise or the independent reference exceeds its predeclared tolerance.

Current evidence: `provenance/task3_parity.json`, SHA-256 `ba9f8112b0b5137b1ec243824c9ce434102b52c72aa7259946c71dce32bbd130`.

| Case | Fit/history | Emissions | Filter + OOS | Backward/smoothing | Regularization events (new diagnostic) |
|---|---|---|---|---|---|
| Gaussian diagonal | Bitwise equal | Bitwise equal, including extreme finite rows | Bitwise equal | Bitwise equal | 0 |
| Gaussian full | Bitwise equal | Bitwise equal | Bitwise equal | Bitwise equal | 14 |
| Student-t diagonal | Bitwise equal, including dof | Bitwise equal | Bitwise equal | Bitwise equal | 0 |

All three cases use K=2, seven iterations, `tol=0`, sticky=2, seed=7, and `min_covar=1e-4`. Original valid-input tolerance is exactly zero. Regularization-event counts are additional diagnostics; they do not alter the original arithmetic.

An independent `hmmlearn.GaussianHMM` full-covariance reference gives likelihood absolute difference `0.0` and maximum smoothed-probability difference `1.354472090042691e-14`, within `1e-10`. Focused tests additionally compare Gaussian/Student-t densities to SciPy and smoothing/xi to exhaustive state-path enumeration. These are mathematical checks, not predictive validation.

## 4. Intentional hardening outside parity

- Reject NaN/infinite observations and malformed probability/covariance inputs.
- Reject negative diagonal variance, nonsymmetric/non-PD full covariance, and unsupported Student-t full covariance instead of silently repairing them at public boundaries.
- Preserve original covariance regularization inside EM, but count floor/eigenvalue/full-update events.
- Raise explicit empty-component and nonfinite-chain errors.
- Keep nonconverged fits nonconverged; never convert them to accepted fits or emit accepted OOS outputs.
- Serialize data-only JSON, verify canonical payload hashes, schema/engine/source versions, finite numeric values, strict JSON scalar types, dependencies, state IDs, dimensions, and training boundaries.
- Use exclusive-create file writes to prevent artifact overwrite/collision.

These changes apply to invalid inputs, diagnostics, and contracts; the exact valid-input comparisons above remain bitwise equal.

## 5. Environment and reproducibility

The regenerated environment uses Python 3.11 and direct pins `numpy==2.3.5`, `pandas==2.2.3`, `scipy==1.17.1`, `scikit-learn==1.6.1`, `hmmlearn==0.3.3`, and `pytest==8.4.2`. These are the Task 3 verification pins, not a claim to recreate the original historical study's complete environment. The original study manifest is retained separately. The external evidence bundle contains the full `pip freeze`, `pip check`, commands, logs, JUnit files, smoke artifacts, and SHA-256 checksums.

The immutable original source commits were fetched into the clean verification clone without changing its fixed integration branch. Tests address them by full commit hash, not a mutable source branch.

## 6. Limitations

Parity establishes equivalence to the selected original implementation, not correctness of every modeling choice or economic usefulness. The canonical CSV is structurally validated and hash-identified, not independently vendor-verified, total-return, calendar-complete, or licensing-cleared. Historical study outputs and their performance claims are not migrated. No forecast, allocation, backtest, dashboard, E7, or prospective-validation work is authorized by this task.
