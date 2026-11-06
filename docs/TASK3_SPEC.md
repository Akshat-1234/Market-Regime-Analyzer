# Task 3 — HMM Core Engine Specification

**Engine version:** `task3-hmm-engine-v1`

**Model artifact schema:** `task3-hmm-model-v1`

**Parity schema:** `task3-hmm-parity-v1`

**Canonical-smoke schema:** `task3-canonical-smoke-v1`

**Numerical authority:** 1c commit `c46541e9ab8611330489a920c46cdb00342931d5`, `market-regime-platform/src/regime_backtester/emhmm.py`

**Feature/state-contract authority:** Task 2 commit `d9ea5e6122922312958fb6eb0d2370eb2275b63e`

This task supplies a deterministic, causal HMM inference engine and a fail-closed Task 2 adapter. It is not a regime-discovery, allocation, backtest, dashboard, or prospective-validation task.

## 1. Acceptance mapping

| Task 3 acceptance criterion | Implementation and evidence | Result |
|---|---|---|
| Establish the numerical reference | Exact 1c `emhmm.py` and `discovery.py` Git blobs are preserved and hash-checked against the Task 1 inventory. `docs/TASK3_PROVENANCE.md` separates migrated engine behavior from excluded discovery behavior. | **Verified** |
| Migrate the HMM core selectively | Ten modules under `research/hmm/` implement validated parameters, emissions, forward/backward, EM, smoothing, adapter, safe persistence, and one smoke. No Task 2/backend/frontend file is changed. | **Verified** |
| Support the original model families | Gaussian diagonal/full and Student-t diagonal share the exact original arithmetic. Student-t with full covariance was unsupported by 1c and is rejected explicitly at emission, configuration, and parameter boundaries. State count is configurable. | **Verified** |
| Preserve initialization and EM semantics | Seeded scikit-learn `KMeans(n_init=4)`, biased covariance initialization, sticky transitions, original tolerance/cap, final-likelihood recomputation, and fixed Student-t dof grid are retained. | **Verified; exact parity** |
| Provide causal filtering and separate smoothing | `HMMFit.filter`/`predictive_loglik` are forward-only. `research.hmm.inference.smooth` explicitly returns retrospective gamma. Task 2 blocks use distinct inference kinds. | **Verified** |
| Reproduce accepted numerical behavior | All original valid-input comparisons in Gaussian diagonal/full and Student-t diagonal parity cases are bitwise equal (`rtol=atol=0`), including fit arrays/history, extreme-input emissions, filtering, chunked OOS, log-beta, and smoothing. | **Verified** |
| Check independent mathematics | SciPy references cover emissions and exhaustive state-path enumeration covers smoothing/xi. `hmmlearn` independently checks Gaussian-full likelihood and smoothing at predeclared tolerances. | **Verified** |
| Harden failures without changing valid-input parity | Nonfinite observations, invalid probabilities/covariances, unsupported families, empty state occupancy, and version/hash/type-invalid artifacts fail closed. Covariance regularization is counted, not silently hidden. | **Verified** |
| Integrate with Task 2 contracts | `fit_model` returns `FitRecord`, filtered probability blocks, predictive densities, occupancy diagnostics, optional explicitly smoothed training output, and strict serialization. | **Verified** |
| Prove OOS causality and fail-closed fit states | Prefix/chunk equality, future-mutation tests, accepted OOS boundary checks, and nonconverged/rejected/failed no-OOS tests are present. | **Verified** |
| Run one bounded canonical integration | Close-only RV; first 756 complete feature rows train; subsequent 126 rows OOS; K=3 Gaussian diagonal; seed 42; no tuning. Accepted converged fit and causal prefix check. | **Verified; smoke only** |
| Supply tests and governance | 79 focused tests, Task 2 regression suites, full repository suite, six Task 3 documents, source inventory, migration manifest, parity evidence, and root report. | **Verified** |

## 2. Numerical scope and tolerances

### Original 1c comparisons

The supported valid-input contract requires **bitwise equality** (`rtol=0`, `atol=0`) to the immutable original source for:

- KMeans initialization and fitted start/transition/mean/covariance arrays;
- likelihood history, final recomputed likelihood, convergence, iteration count, and fitted dof;
- Gaussian diagonal/full and Student-t diagonal emissions, including extreme finite observations;
- filtered probabilities, predictive log densities, final log-alpha, continued OOS filtering;
- log-beta and smoothed probabilities;
- explicit sticky-prior settings and nonzero regularization diagnostics.

This deliberately exceeds a loose `1e-8` equivalence claim. It does not require equality for newly rejected invalid inputs, where hardening is intentionally different.

### Independent references

Independent references are not expected to use identical floating-point operation order. The predeclared `hmmlearn` thresholds are likelihood `rtol=1e-11`, `atol=1e-9`, and smoothed probabilities `rtol=atol=1e-10`. SciPy density references use tight finite tolerances; exhaustive two-state path enumeration checks posterior and pairwise-count identities directly.

### Supported matrix

| Emission | Covariance | State counts | Status |
|---|---|---|---|
| Gaussian | diagonal | configurable `K >= 1` | Supported and exact-parity tested at K=2; adapter tested at K=4 |
| Gaussian | full | configurable `K >= 1` | Supported and exact-parity tested |
| Student-t | diagonal scale | configurable `K >= 1`; shared dof > 2 | Supported; deterministic fixed-grid dof update retained |
| Student-t | full | — | Rejected: not a valid original 1c family |

## 3. Causality and likelihood conventions

For observation vector `x_t`, filtering updates only from the prior filtered state, transition matrix, and current emission. It returns normalized filtered probabilities, per-row one-step predictive log density, and final unnormalized log-alpha for continuation. A later observation cannot change an earlier filtered row.

Smoothing uses the entire supplied block and is explicitly noncausal. Training-filtered, smoothed, and OOS-filtered blocks are never interchangeable. Predictive density units are nats per observation. `space="raw"` includes the identity-Jacobian declaration; `space="scaled"` explicitly excludes it and does not claim conversion back to raw feature units.

The EM convergence flag follows the original history criterion: after an M-step, compare the current and previous pre-update likelihoods using `abs(current-previous) < tol * max(1, abs(current))`. The returned model is always the post-M-step model, and its public likelihood is recomputed against those returned parameters. Hitting the iteration cap remains nonconverged.

## 4. Fixed canonical smoke

- Input SHA-256: `ea6dfffb93e5eabd8b6a2f96cd40d6b3ec5c7f47f2f9e6c0cbd3ca9a5f2ac5e4`; 4,684 rows, 2007-09-17 through 2026-10-22.
- Task 2 close-only RV features: `daily_return`, `volatility_20`; 4,664 common complete rows; no imputation.
- Split: first 756 feature-valid rows train (2007-10-16–2010-11-15), immediately subsequent 126 rows OOS (2010-11-16–2011-05-19).
- Training-only z-score, population `ddof=0`; Gaussian diagonal K=3; seed 42; cap 200; tolerance `1e-5`; minimum covariance `1e-4`; sticky 0.
- No model selection, configuration search, date search, economic ranking, or performance claim.

## 5. Acceptance/nonacceptance boundary

Only an accepted converged fit may expose an accepted OOS block/density. Nonconvergence, minimum training occupancy rejection, numerical failure, malformed inputs, and artifact incompatibility fail closed. The original nonconverged Gaussian fallback lives in excluded `discovery.py`, not `emhmm.py`, and was not migrated. Task 4 remains recommendation-only until separately authorized.
