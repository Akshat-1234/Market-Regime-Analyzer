# Task 3.1 — Serialization Consistency and Compatibility

## Outcome

The artifact boundary now validates the complete model/configuration/specification relationship on both save and load. New artifacts use `task3-hmm-model-v2` and engine `task3-hmm-engine-v1.1`. Strict loading remains available for valid Task 3 `task3-hmm-model-v1` / `task3-hmm-engine-v1` artifacts. A canonical SHA-256 is checked first, but is never treated as semantic validation.

## Enforced invariants

- `model.n_states == spec.state_count == config.n_states`.
- `model.n_features == len(spec.feature_names)`.
- Covariance type, emission, and seed agree across fitted model, `EMConfig`, and `ModelSpec`.
- `ModelSpec.model_version` agrees with the artifact engine version; v2 artifacts also carry an independent `fitted_seed` field.
- Start/transition probabilities are finite, nonnegative, correctly shaped, and normalized; means and covariance parameters are finite with shapes appropriate to diagonal/full covariance.
- Full covariance is symmetric positive definite; diagonal variances are strictly positive; Student-t remains diagonal-only with dof > 2.
- Likelihood/history are finite; iteration count is a positive integer no greater than the configured cap and exactly matches history length.
- Convergence agrees with the original relative-history criterion. Nonconvergence must exhaust the cap without meeting that criterion.
- Training boundaries are ordered exact `YYYY-MM-DD` values on load; state IDs are unique, nonblank strings matching state count.
- Dependency metadata and all detailed regularization counters are present, correctly typed, nonnegative, and internally consistent.

## Student-t dof semantics

`EMConfig.dof` is the **initial** dof used to initialize EM. The original M-step may profile a different `HMMFit.dof` on its fixed grid. Therefore equality is a false invariant and is not imposed.

Schema v2 instead stores:

```json
"degrees_of_freedom": {
  "initial": 8.0,
  "fitted": 6.0,
  "semantics": "config_initial_model_profiled_final"
}
```

Both values must be finite and > 2, and the metadata must equal the declared config/model values. A different valid initial/fitted pair round-trips deliberately. Gaussian artifacts must have `null` dof in both model and config and cannot carry Student-t dof metadata.

## Regularization and convergence metadata

V2 convergence records retain `regularization_events` and add the four precise counters defined in `TASK3_1_DIAGNOSTICS.md`. The legacy value must equal the detailed sum. Full-covariance floor applications must equal `n_iter * n_states`; diagonal artifacts cannot contain full-matrix counters. These checks catch valid-hash but semantically impossible artifacts.

## Legacy v1 compatibility

A v1 artifact is accepted only with the matching v1 schema/engine pair, original source lineage, valid payload hash, valid config/spec/model semantics, and consistent legacy diagnostics. Detailed counters are derived deterministically:

- diagonal: the legacy aggregate is the diagonal floor-hit count;
- full: `n_iter * n_states` are deliberate floor applications and the nonnegative remainder is eigenvalue clipping.

An inconsistent negative remainder is rejected. Legacy loading does not change fitted arrays or filtering results. Saving always writes v2; migrating a legacy artifact to v2 requires deliberately updating its `ModelSpec.model_version` to the current engine.

## Adversarial verification

Tests construct semantically invalid payloads and then **recompute a valid canonical payload hash**. Covered defects include model emission/covariance/seed mismatch, spec/config contradiction, Student-t dof metadata mismatch, Gaussian Student-t metadata, wrong covariance shape, unnormalized transition/initial probabilities, duplicate state IDs, nonfinite/non-numeric parameters, invalid convergence, and inconsistent regularization counters.

Current valid v2 and legacy-v1 round trips preserve filtering probabilities exactly. Save-side mutation tests ensure validation is not limited to loading. See `tests/hmm/test_serialization.py` and the verification report.
