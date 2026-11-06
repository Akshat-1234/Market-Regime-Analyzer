# Task 2 Council — Checkpoint A (before implementation)

Evidence cut-off: 2026-11-05T19:37:05Z recovery, followed by read-only source and environment inspection. This is a simulated five-person technical review, not independent human sign-off.

## Evidence and proposed boundaries

- The original dirty checkout is fully preserved at `/home/user/mra-task2-recovery-20261105T193705Z/original-dirty-checkout.tar.gz` (SHA-256 `19a856146d659cc2f9c63b9996b0abd68e66ba590ebb7ce97bcc8780349fc345`). All 122 non-Git files are byte-identical to the remote Task 1 tree; no unique local content was found.
- Task 2 will run in `/home/user/mra-task2-clean`, an independent clean clone on `arena/6b4913f3-market-regime-analyzer` at authoritative Task 1 commit `57ae0c238e497a059ce85f83da398477be705e8a`. The original checkout's files and Git refs are untouched.
- Original f10 and 1c refs remain `9bb7f92d…` and `c46541e…`. Exact 1c source was exported only to `/tmp` for inspection, not migrated.
- Actual f10 feature code uses `Close.pct_change(fill_method=None)` and `r.rolling(20).std() * sqrt(252)` (sample standard deviation). RVD separately adds `Close / Close.rolling(252).max() - 1`.
- f10 forecast training requires `decision_date < test_start` and `target_end < test_start`. 1c `expanding_oos` instead fits `y[slice(0, begin)]` without target end dates.
- Exact 1c source also shows global post-hoc specification selection, scaled-density comparisons across feature sets, a second occupancy permutation, nonconverged fallback, incomplete source provenance, circular control shifts, and a mean stored under `median_exposure_ks`.
- The base Python environment lacks all required test/research packages. A separate `/home/user/mra-task2-venv` now contains only the pinned packages needed for new and relevant existing Python tests. No frontend tooling is installed.

## Five-person review

### Contrarian

A set of newly written validators can pass while proving nothing about the historical defects. Require at least one behavioral execution of exact 1c `expanding_oos` showing that mutating a boundary-crossing target changes the first forecast, and an exact `fit_spec_fold` fallback reproduction with a deterministic nonconverged fixture. Static source/dataflow checks are acceptable for global selection and cross-feature ranking only if their limitations are stated. A green test means the invariant or reproduction worked, not that the old component is repaired.

### First Principles Thinker

Use exclusive test-fold cutoffs: both decision date and outcome end must be strictly before `test_start`, matching f10. Keep raw dataset SHA-256 distinct from a parsed-record fingerprint and never normalize canonical bytes. Volatility uses 20 returns, hence 21 price rows and sample `ddof=1`; its first valid position is 20. State alignment must consume training-only probabilities and produce an explicit current-to-reference mapping. Densities need identical ordered raw features, observation dates, units, and observation space; a Jacobian alone cannot make different dimensions comparable.

### Expansionist

The compact package should cover data, features, model outputs/density, temporal selection, state alignment, experiment manifests, and control-matching diagnostics. These are immediately useful for the likely HMM adapter and later forecast/discovery work. Avoid generic registries, plugin factories, a second research engine, or speculative APIs. Implement only validators and small deterministic calculations needed by executable tests and documentation.

### Outsider

Recovery must be auditable without trusting a clean status line: archive hash, member count, dirty-vs-remote comparison, clean clone path, and original unchanged status hash belong in provenance. Test documentation must name exact counts and versions and distinguish original missing dependencies from the isolated environment. Exact-source regression helpers should fail with a clear fetch instruction if the immutable 1c object is unavailable, not silently skip and inflate confidence.

### Executor

Use `research/contracts/` with small modules and `tests/contracts/` plus `tests/regression/`. Keep historical source untouched. Load exact 1c modules from `git show c46541e…:<path>` only in regression tests, with a clear hard failure if the object is missing. Use synthetic frames and fake model outputs, never historical refits. Run new tests first, then existing archive/platform tests, compile checks, dataset/artifact hash checks, and a final scope diff. Document confirmed implementation behavior separately from unresolved downstream numerical impact.

## Chairman Verdict

### WHERE THE COUNCIL AGREES

Recovery is safe and sufficient. Contracts must be versioned, compact, independent of the legacy package at runtime, and validated with deterministic fixtures. Temporal maturity, filtered-versus-smoothed semantics, arbitrary state labels, explicit fit failures, and machine-verifiable provenance are non-negotiable. No HMM, discovery, allocation, dashboard, E7, or prospective migration is authorized.

### WHERE THE COUNCIL CLASHES

The Contrarian wants direct original-code reproduction for every issue; the Executor notes that global multi-fold studies and model grids would be prohibitively broad and unnecessary for Task 2. The resolution is direct execution for target maturity and convergence fallback, focused behavioral reproduction for occupancy and matching statistics, exact-source dataflow checks for global selection/density/provenance, and explicit “downstream impact unresolved” labels. The Expansionist's reusable helpers are accepted only where tests require them.

### BLIND SPOTS CAUGHT

A same-branch second worktree would share the original branch ref, so an independent clone better satisfies “leave the original checkout untouched.” A naive warmup count can be off by one because 20 volatility inputs are returns, not prices. Equality of parsed data does not imply equal raw hashes. `target_end == test_start` is excluded under f10's strict rule. Testing only that a dataclass exists would not detect leakage, double permutation, false matching summaries, or manifest overwrite.

### THE RECOMMENDATION

**PROCEED WITH CONTRACTS AND REGRESSION FIXTURES ONLY.** Require meaningful negative tests and direct evidence for the two most executable 1c defects. Keep all other classifications precise and defer component fixes. Preserve the canonical dataset and every historical artifact byte-for-byte.

### THE ONE THING TO DO FIRST

Implement the data/feature/temporal primitives and their hand-calculated fixtures, including the boundary-crossing target example, before adding model or experiment helpers.

---

# Task 2 Council — Checkpoint B (implementation and test review)

Evidence cut-off: focused contract/regression implementation after the 72-test passing run and the pre-existing Python test run. This remains simulated review, not human approval.

## Five-person review

### Contrarian

The suite is meaningful because it fails invalid inputs and executes exact historical behavior, but it is not uniform proof. Target maturity, nonconverged fallback, circular shifting, and source/data lineage have direct exact-code behavioral evidence. Global selection and cross-dimensional likelihoods are exact-source dataflow findings plus independent contract guards; their historical numerical effects were not rerun. Occupancy has exact-source and synthetic behavioral evidence, but its per-state error must not be exaggerated into ranking damage without a consumer.

### First Principles Thinker

The implementation now uses the correct strict target purge and preserves sample-volatility/warm-up semantics. Review caught and corrected a real parsed-fingerprint bug for date-indexed frames. Alignment was improved from identical-date matching to the dated intersection of adjacent training windows, with no empty-overlap fallback. Fit outputs now check state count and OOS start against the model/training boundary. Nonconverged fallback remains diagnosable but cannot pass `require_usable_oos`.

### Expansionist

The APIs are sufficient for the next selective HMM adapter: a model spec, fit disposition, typed probability blocks, raw-density comparison key, inner-fold selection evidence, training-overlap Hungarian mapping, and immutable manifests. Later stages will need adapters from historical dictionaries into these types; the strict schema should not be weakened merely to accept old manifests. No new engine or feature family is hidden in the package.

### Outsider

The execution ledger is credible because it retains the initial **60 passed / 10 failed** run, subsequent **67 / 3**, **69 / 1**, and a fixture-date correction before **72 passed**. Existing tests are **13 passed, 1 skipped**; the skip is exactly “Frontend has not been built,” not a passed browser check. The environment is outside Git and package versions are pinned. Reports must not call exact-source static inspection an experiment reproduction.

### Executor

The focused suite has 72 passing tests with no skips. It covers canonical CRLF/LF identity, f10 formula parity, future mutation, maturity boundaries, probability types, fit rejection/failure, density dimensions, inner selection, arbitrary/rare/zero states, shifted-training overlap, manifest collision/hash/failure behavior, and all seven requested 1c risk classes. Next steps are documentation, a full-suite run, static/integrity verification, clean scope review, and closure. No model fitting or frontend build is needed.

## Chairman Verdict

### WHERE THE COUNCIL AGREES

The implementation satisfies the contract breadth requested and the tests exercise behavior rather than file existence. The original defects remain historical findings; only the new integration guards are implemented. The suite is ready for final documentation and verification, not for HMM migration.

### WHERE THE COUNCIL CLASHES

The Contrarian would prefer numerical historical reruns for global selection and density impact; the Executor correctly rejects them as unauthorized research reproduction and unnecessary for an implementation/dataflow defect. The Expansionist wants easy historical manifest loading, while First Principles requires rejection. The decision is to retain strict validation and require an explicit provenance-enriching adapter in a later migration task.

### BLIND SPOTS CAUGHT

The first fingerprint implementation rejected its own normalized data frame. The f10 feature reference has no family parameter. A two-state fixture initially carried three IDs. Adjacent training windows need intersection rather than identical dates. Occupancy min/max/effective-state aggregates are permutation-invariant; the confirmed per-state mapping error has no reviewed consumer in discovery/study/allocation, so ranking impact is not established. The only existing-test skip is an unbuilt frontend.

### THE RECOMMENDATION

**PROCEED TO DOCUMENTATION AND FINAL VERIFICATION.** Preserve direct-versus-static evidence labels, record all actual counts and limitations, and gate migration on downstream consumers adopting the contracts. Do not repair or rerun the historical study.

### THE ONE THING TO DO FIRST

Write the defect register with exact reproduction evidence and explicit downstream-impact boundaries, especially the occupancy aggregate qualification and the unquantified historical effects of selection, density, maturity, and fallback defects.

---

# Task 2 Council — Checkpoint C (final gate)

Evidence cut-off: final focused/full test runs, completed contracts/matrix/defect/readiness/report documents, machine-readable verification, and pre-commit integrity checks. Simulated technical review only; no human sign-off.

## Five-person review

### Contrarian

The strongest evidence is not the green count alone: exact 1c maturity and fallback behavior was executed, and immutable source hashes gate the regressions. The weakest evidence remains historical numerical impact, which was deliberately not rerun. The report says so. No output can be promoted as a corrected forecast, discovery result, allocation, or prospective claim. The final commit hash is handled externally rather than through a dirty post-commit report edit.

### First Principles Thinker

The contracts preserve raw-versus-parsed data identity, 20-return sample-volatility semantics, exclusive target maturity, filtered/OOS distinctions, raw same-vector density, outer-fold selection, overlapping-training alignment, and fail-closed fit/provenance behavior. Canonical bytes and historical implementations are unchanged. The mean/median and circular-control findings are correctly separated from any profitability interpretation.

### Expansionist

The next HMM adapter has a usable integration surface, but the readiness document correctly makes it conditional on explicit authorization and new parameter-level tests. The contracts should be adopted selectively rather than becoming a parallel framework. No further abstraction, migration, or dashboard work belongs in this commit.

### Outsider

An auditor can reproduce the environment and counts: 72 focused tests, 85 passed plus one skip across 86 total tests, one named warning, and zero final failures/errors. The original interpreter's missing-pytest error is preserved separately. Recovery archive, original status bytes, source inventories, dataset hash, source refs, and preserved-path diff all check out. The exact final SHA must be verified after push, not inferred before it.

### Executor

There are 29 additive paths including the report. No existing path is modified. Final logs and JUnit are outside Git. The remaining actions are mechanical: stage exactly those paths, inspect cached names/status and whitespace, commit once on the fixed branch, push without force, then verify local/remote HEAD equality, clean status, Task 1 ancestry, unchanged f10/1c refs, and original recovery invariants. Write the external closure JSON and stop.

## Chairman Verdict

### WHERE THE COUNCIL AGREES

Task 2 meets its technical acceptance criteria: preserved recovery, clean Task 1-descendant workspace, executable contracts, meaningful deterministic regressions, known-risk coverage, actual test execution, precise limitations, and a restrictive migration gate. The branch is ready for a single additive closure commit. All research migration remains unauthorized.

### WHERE THE COUNCIL CLASHES

The Contrarian would prefer historical numerical impact estimates; the Executor and scope gate prohibit unauthorized study reproduction. The Expansionist could continue into the HMM adapter; the agreed stop forbids it. The final-hash reporting convention is accepted because embedding a commit's own hash in its content is self-referential, while the external closure record and final response can provide the exact value with a clean worktree.

### BLIND SPOTS CAUGHT

The review distinguishes 86 total tests from 85 passes plus one intentional skip, records the warning, and does not count the base interpreter's zero-collection error as a test failure. It catches the self-referential final-hash problem, preserves both text and NUL status hash formats, qualifies permutation-invariant occupancy aggregates, and requires post-push rather than pre-push source/branch verification.

### THE RECOMMENDATION

**PASS TASK 2 FOR COMMIT/PUSH CLOSURE, THEN STOP.** Do not begin custom 1c HMM, forecast/discovery/allocation migration, dashboard integration, E7, or prospective validation. Any later work needs explicit user authorization and the gates in `TASK2_MIGRATION_READINESS.md`.

### THE ONE THING TO DO FIRST

Stage exactly the 29 declared additive paths and inspect the cached diff before creating the single Task 2 commit.
