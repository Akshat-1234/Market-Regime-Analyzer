# Task 3.1 — HMM Engine Hardening Report

## Outcome

**Complete and gate-passing.** Serialization consistency and regularization diagnostics are hardened, original numerical behavior is unchanged, and the engine is frozen as `task3-hmm-engine-v1.1` for Task 4. Task 4 implementation had not begun when this gate passed.

## Changes

- `research/hmm/serialization.py`: v2 schema, complete save/load semantic validation, strict convergence/dof/diagnostic metadata, and strict v1 compatibility.
- `research/hmm/parameters.py`: precise `RegularizationDiagnostics` and detailed `HMMFit` counters while retaining `regularization_events`.
- `research/hmm/em.py`: exact event disaggregation without changing EM equations or operation order.
- `research/hmm/version.py`: centralized frozen engine/source identity; adapter and smoke use it.
- `research/hmm/adapter.py`, `smoke.py`: current version and detailed diagnostics.
- `tests/hmm/`: valid-hash semantic attacks, dof/version/legacy tests, and independent regularization cases.
- `scripts/verify_task3_1_parity.py`, `provenance/task3_1_parity.json`: bitwise parity plus explicit initialization capture.
- `provenance/task3_1_engine_freeze.json`: engine/file/source hashes and gate identity.
- Four focused documents and this report.

## Acceptance evidence

- Focused HMM: **94 passed**.
- Task 2 contracts/regressions: **72 passed**.
- Full suite: **179 passed, 1 pre-existing frontend-build skip, 1 pre-existing warning**.
- Original Task 3 parity script: passed unchanged.
- New parity artifact: all original initialization, EM, emission, filtering/density/continuation, and smoothing comparisons bitwise equal for all three supported families.
- `hmmlearn`: likelihood difference 0.0; maximum smoothed difference `1.354472090042691e-14`.
- Canonical smoke: exact Task 3 likelihoods and 11 iterations; accepted/converged; causal prefix verified.
- Dataset and original source hashes unchanged; no Task 2/backend/frontend modifications.

Parity SHA-256: `333b821e0d685b1fabfb9850e27f76491f2026108fb2766636d4669b34d1e5f8`. Freeze SHA-256: `53f61c24e75ddda81e374ce4629cb88cf1fb521a5dc8c1d91d1a68ce95cd0ea9`.

## Defect resolutions

A valid payload hash no longer allows contradictory model/spec/config semantics. Student-t initial and fitted dof are separately recorded rather than falsely required to match. Gaussian Student-t metadata, invalid probabilities/covariances/shapes, nonfinite values, invalid IDs/dates, impossible convergence, and inconsistent counters fail closed on both boundaries as applicable.

The historical full-covariance aggregate is preserved exactly. Its 14 events in the parity case are now correctly described as 14 deliberate matrix-floor applications and zero eigenvalue clips. Separate tests establish actual clipping behavior and diagonal floor hits.

## Council and limitations

Checkpoint A unanimously recommends passing Task 3.1 and freezing the engine, while emphasizing that hashes are not semantics, operation counts are not instability measures, and parity is not predictive validity. See `docs/TASK3_1_COUNCIL.md` for disagreements and blind spots.

No new model family, discovery experiment, forecast, allocation, backtest, dashboard, or economic claim is included. The separate Task 3.1 commit/push identity and clean-worktree checks are recorded in the external evidence bundle. Task 4 must use the freeze hash and preserve these numerical files unchanged.
