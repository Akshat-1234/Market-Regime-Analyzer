# Task 3 — HMM Core Engine Report

## Outcome

**Task 3 implementation and verification are complete; final Git closure is recorded externally after commit/push.** The additive change implements a deterministic causal HMM engine, explicit retrospective smoothing, a fail-closed Task 2 adapter, safe versioned JSON persistence, focused/parity tests, and one bounded canonical RV smoke. It does not implement Task 4.

The numerical authority is immutable 1c commit `c46541e9ab8611330489a920c46cdb00342931d5` (`emhmm.py`, SHA-256 `181d251fb8b3b78c907c6518a1714898041dbcb048275f82bd5dd308c2d1f6c9`). Task 2 commit `d9ea5e6122922312958fb6eb0d2370eb2275b63e` remains the contract authority and an ancestor of the integration branch.

## Verified results

| Check | Result |
|---|---|
| Focused HMM tests | **79 passed** |
| Task 2 contracts/regressions | **72 passed** |
| Full repository suite | **164 passed, 1 skipped, 1 pre-existing third-party warning** |
| Original Gaussian diagonal parity | Bitwise equal for fit/history, emissions, filter/OOS, backward/smoothing |
| Original Gaussian full parity | Bitwise equal; new diagnostics record 14 regularization events |
| Original Student-t diagonal parity | Bitwise equal, including fitted dof |
| Independent `hmmlearn` reference | Likelihood difference 0.0; maximum smoothed difference `1.354472090042691e-14`, within `1e-10` |
| Canonical smoke | Accepted/converged at iteration 11; no fallback; zero regularization events; causal prefix verified |
| Dependency check | `pip check` passed in the recreated pinned environment |
| Scope | Exactly 30 additive files; no Task 2/backend/frontend modification |

Parity evidence is `provenance/task3_parity.json`, SHA-256 `ba9f8112b0b5137b1ec243824c9ce434102b52c72aa7259946c71dce32bbd130`. The migration manifest, including source classification and canonical-input identity, has SHA-256 `45ea24c9eb7dfb49fea21817d4ec6b04c8796190574cdac754b10f1a3daa8535`.

## Canonical integration smoke

The fixed run uses canonical CSV SHA-256 `ea6dfffb93e5eabd8b6a2f96cd40d6b3ec5c7f47f2f9e6c0cbd3ca9a5f2ac5e4`, close-only Task 2 RV features, 756 initial complete feature rows for training, and the immediately subsequent 126 rows for OOS. It uses training-only `ddof=0` scaling, Gaussian diagonal K=3, seed 42, cap 200, tolerance `1e-5`, minimum covariance `1e-4`, and sticky 0.

- Training: 2007-10-16–2010-11-15; OOS: 2010-11-16–2011-05-19.
- Training scaled log-likelihood: `-1268.0326484796867`.
- OOS scaled-density sum: `-104.6545315416222`.
- Hard training occupancy: 97 / 336 / 323 rows for local state IDs 0 / 1 / 2.
- Mutating later OOS observations leaves earlier filtered probabilities/densities unchanged within the declared numerical checks.
- External smoke summary SHA-256: `9aacb029776efe3fd81be200ed26b3e26e67e72b38306243ece980967c0cb7ee`.
- External model SHA-256: `dcf51ecd808ea82d2ae6a07fa20a3fc520d5e9d6b9b55eadb80e67bcb5cd6ba2`.

This is a single integration regression, not model selection or evidence of predictive/economic value.

## Correctness and failure behavior

- Gaussian diagonal/full and Student-t diagonal retain original valid-input arithmetic. Student-t full covariance was not supported by 1c and is explicitly rejected at emission, configuration, and parameter layers.
- Filtering is causal; smoothing is explicitly retrospective and separately labeled.
- Nonfinite observations, invalid probabilities/covariances, unsupported configurations, and empty state components fail explicitly.
- Covariance regularization remains where the original EM used it and is now counted in diagnostics.
- Nonconverged, occupancy-rejected, and failed fits never receive accepted OOS blocks/densities. The nonconverged fallback in excluded `discovery.py` was not migrated.
- Model artifacts are deterministic data-only JSON with payload hashes, schema/engine/source versions, dependencies, strict scalar/type/dimension/boundary validation, and exclusive-create writes.
- Raw/scaled predictive-density spaces and Jacobian declarations are explicit.

## Provenance and recovery

Three preserved files (`emhmm.py`, `discovery.py`, and the selected study manifest) are verbatim 1c Git blobs checked against Task 1 inventories. `provenance/task3_migration_manifest.json` records their lineage and measured raw/parsed CSV identity without inventing or repairing a historical data manifest. The original study environment is not claimed to be reproduced; Task 3 verification pins and the full freeze are recorded separately.

A sandbox reset deleted the earlier uncommitted implementation and evidence before any Task 3 commit/push. The original dirty checkout was preserved separately and never used for writes or pushes. The implementation was reconstructed in a clean Task 2-descendant clone, and **all current test, parity, smoke, dependency, scope, and hash evidence was regenerated**. Deleted historical logs are not cited as surviving evidence. One reconstruction setup run had 69 passes and 10 errors because the fresh clone lacked the immutable 1c object; fetching the exact full commit fixed the fixture, followed by the 79-test pass reported above.

## Deliverables and evidence

- `research/hmm/`: ten engine/adapter/persistence/smoke modules.
- `tests/hmm/`: 79 focused tests, including exact original and independent-reference checks.
- `scripts/verify_task3_parity.py`: reproducible parity generator.
- `docs/TASK3_SPEC.md`: acceptance criteria, conventions, tolerances, and fixed smoke.
- `docs/TASK3_PROVENANCE.md`: source map, exact parity, and hardening boundary.
- `docs/TASK3_MANIFEST.md`: 30-file map, commands, hashes, and external evidence index.
- `docs/TASK3_VERIFICATION.md`: commands, results, test coverage, and smoke measurements.
- `docs/TASK3_COUNCIL.md`: simulated critical review and disposition.
- `docs/TASK3_RISKS.md`: residual risks and explicitly unverified claims.
- `provenance/`: three source copies plus migration and parity manifests.
- `/home/user/mra-task3-evidence-20261106`: external logs, JUnit XML, smoke artifacts, dependency evidence, checksums, scope snapshots, and post-push closure JSON.

The final commit hash is deliberately not embedded self-referentially. External `task3_closure.json` records the actual normal commit, fixed-branch push, local/remote equality, Task 2 ancestry, clean status, and exact additive scope after those checks occur.

## Limitations and next task

No forecast skill, regime usefulness, allocation benefit, backtest result, dashboard correctness, E7 result, or prospective validation is claimed. Data hashes and structural checks do not verify vendor accuracy, corporate actions, total return, calendar completeness, or licensing. Full-covariance regularization and rare states remain modeling risks. The smoke does not select or recommend a model.

**Recommendation:** accept Task 3 only with the external final Git closure checks. Task 4 remains recommendation-only and requires separate explicit authorization; it was not started.
