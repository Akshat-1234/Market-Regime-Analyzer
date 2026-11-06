# Task 3 — Simulated Review Council

## 1. Review frame

The following are simulated reviewer perspectives used to challenge the implementation, not independent human approvals. Evidence is limited to the clean-checkout tests, exact-source parity, independent mathematical references, canonical smoke, source manifests, and final Git scope checks.

## 2. Numerical-methods reviewer

**Concern:** A refactored EM implementation can look equivalent while changing operation order, initialization, final parameters, or smoothing semantics.

**Evidence reviewed:** Immutable Git-object fixture; bitwise parity for all supported fit arrays/history, emissions, filtering, continued OOS, log-beta, and gamma; independent KMeans capture; SciPy formula checks; exhaustive state-path smoothing/xi; `hmmlearn` likelihood/posterior check.

**Findings:**

- Original convergence checks pre-update history after each M-step. The returned public likelihood is therefore recomputed against final parameters; this is explicit and tested.
- Full-covariance EM applies its original floor/eigenvalue projection and now records 14 events in the parity case. Counting regularization does not change original arithmetic.
- Student-t full covariance is not silently approximated: it is rejected consistently at emission, configuration, and fit validation layers.
- Independent `hmmlearn` smoothed probabilities differ by only `1.354472090042691e-14`; this is inside the predeclared tolerance and is not misreported as bitwise equality.

**Disposition:** Numerical acceptance is supported for the tested families and boundaries. No claim extends to unsupported families or predictive performance.

## 3. Causality and contracts reviewer

**Concern:** Smoothed training states could leak into OOS, chunk continuation could differ from one-shot filtering, or a failed fit could still produce accepted-looking outputs.

**Evidence reviewed:** Future-mutation and prefix/chunk tests; explicit `InferenceKind`; Task 2 date/feature/state validation; accepted/nonconverged/rejected/failed adapter tests; canonical smoke future-mutation check.

**Findings:**

- Filtered prefixes are invariant to later observations. Smoothed prefixes are expected to change and are explicitly labeled noncausal.
- The final log-alpha is the continuation state; OOS starts strictly after training. No OOS observations enter fitting or scaling.
- Only accepted converged fits receive OOS blocks/densities. Nonconvergence does not invoke the original discovery fallback.
- Raw versus scaled predictive-density/Jacobian declarations are explicit. Scaled log density is not mislabeled as raw density.

**Disposition:** Causal and fail-closed acceptance criteria are met at the implemented adapter boundary.

## 4. Provenance and reproducibility reviewer

**Concern:** A mutable source branch, incomplete manifest, missing data, or unpinned reference could invalidate parity.

**Evidence reviewed:** Full 1c/f10 commit IDs, Task 1 blob inventories, three verbatim source files, inline canonical input identity in the migration manifest, canonical CSV hash, direct dependency pins/freeze, and regeneration commands.

**Findings:**

- The fresh single-branch clone initially lacked the original source object, causing 10 setup errors. Exact full-commit fetches fixed the fixture without changing the integration branch. This is disclosed rather than counted as a passing test.
- The canonical CSV is present and hash-verified. The smoke uses Task 2 features and a fixed split, not a searched split.
- Three preserved source files are verbatim 1c Git blobs. Canonical CSV provenance is generated Task 3 metadata embedded in the migration manifest, not mislabeled as a historical source manifest.
- The original study environment is not falsely claimed to be reproduced; Task 3 verification pins are stated separately.

**Disposition:** Source identity and current environment are reproducible. Historical vendor/calendar/licensing and incomplete-run limitations remain.

## 5. Serialization and failure reviewer

**Concern:** A valid payload hash alone could authorize malformed types, inconsistent dimensions, or incompatible artifacts.

**Evidence reviewed:** Round-trip/determinism/corruption tests; strict schema/engine/source versions; nested metadata and JSON scalar checks; exclusive-create behavior; parameter/config/spec dimension agreement.

**Findings:**

- The hash authenticates canonical payload bytes, not semantic validity; both are validated.
- Strings such as `"false"` cannot become boolean convergence flags, and nonfinite serialized likelihoods are rejected.
- Executable pickle deserialization is not used. Existing files cannot be silently overwritten.
- Invalid public covariance is rejected rather than repaired outside the original EM regularization path.

**Disposition:** Artifact/failure acceptance is met for the defined JSON schema. Hashing is integrity evidence, not cryptographic signing or external trust.

## 6. Governance and scope reviewer

**Concern:** Generated outputs could contaminate Git, unrelated files could change, or a smoke could be presented as Task 4 research.

**Evidence reviewed:** Additive path list, external logs/artifacts, six governance documents, report limitations, and fixed canonical-smoke configuration.

**Findings:**

- The recovery note's “30 files” conflicted arithmetically with a 32-path listing. The final design retains the required 30 by folding two redundant generated indexes into `task3_migration_manifest.json`; no source, test, engine, or governance deliverable was dropped.
- The smoke model and logs remain outside Git. No backend/frontend/Task 2 source is changed.
- The accepted smoke is not a model-selection study, forecast, allocation result, backtest, dashboard validation, E7, or prospective evidence.
- Final commit identity cannot be embedded self-referentially; external closure evidence is required after push.

**Disposition:** Scope is acceptable only with the final staged-diff and remote/local closure checks recorded.

## 7. Council conclusion

**Recommendation: PASS Task 3 after final additive-scope and push closure checks.** The numerical, causality, contract, persistence, provenance, and canonical-integration evidence supports the bounded task. It does not authorize Task 4 or establish predictive/economic validity. Residual risks and nonverified claims remain in `TASK3_RISKS.md` and the root report.
