# Task 3.1 — Precise Regularization Diagnostics

## Definitions

The counters describe operations, not inferred numerical instability.

| Field | Exact increment rule |
|---|---|
| `diagonal_variance_floor_hits` | Number of individual diagonal variance components strictly below `config.min_covar` before `np.maximum(raw, min_covar)` clips them. |
| `full_covariance_floor_applications` | One per full-covariance state matrix per M-step when `covars[j] += I * min_covar` is deliberately applied. This occurs even when no eigenvalue needs clipping. |
| `eigenvalue_clipping_events` | Number of eigenvalues strictly below `NEAREST_PD_EPSILON` (`1e-8`) before `_nearest_positive_definite` raises them to that floor. |
| `regularization_applications` | Exact sum of the three fields above. It counts deliberate floor applications and actual clips; it is not an instability score. |
| `regularization_events` | Historical compatibility field, unchanged in meaning and exactly equal to `regularization_applications`. |

The full update still executes the positive-definite projection after adding the diagonal floor, but a projection with no clipped eigenvalue adds zero clipping events. No EM equation, operation order, tolerance, or covariance formula was changed.

## Compatibility

`m_step(... )` retains its default historical integer return. `m_step(..., return_diagnostics=True)` returns `RegularizationDiagnostics`. `fit_config` aggregates the detailed object and populates all fields on `HMMFit`.

For previously persisted v1 artifacts, the loader derives detailed counters from the known original update rules. For new v2 artifacts, all counters are explicit and checked against covariance type, iteration count, and state count.

## Independent tests

- A well-conditioned diagonal update has zero events of every kind.
- Two zero diagonal state covariances in two features produce exactly four actual variance-floor hits and no full/eigenvalue events.
- A well-conditioned full update with two states produces exactly two full-matrix floor applications and **zero** eigenvalue clips.
- Two singular zero full covariance matrices with `min_covar=1e-12` produce two floor applications and four eigenvalue clips; the legacy aggregate remains six.
- Fitted full models preserve `regularization_events == regularization_applications` and `full_covariance_floor_applications == n_iter * n_states`.

## Parity interpretation

In the predeclared seven-iteration, two-state Gaussian-full parity case, the historical value 14 is now explained as **14 full-covariance floor applications and zero eigenvalue clips**. It is no longer presented as evidence of 14 instability events. Gaussian diagonal and Student-t diagonal retain zero events. All original arrays/history/filtering/smoothing remain bitwise equal.

Regularization counts must be reported alongside convergence, occupancy, and held-out diagnostics; none alone establishes model validity.
