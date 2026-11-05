# Task 2 Migration Readiness

**Decision:** **TASK 2 CONTRACT GATE READY AFTER FINAL VERIFICATION; NO RESEARCH MIGRATION AUTHORIZED BY THIS DOCUMENT.**
**Stop point:** custom 1c HMM migration, discovery, allocation, dashboard integration, E7, and prospective validation have not started.

## Foundation status

| Layer | Evidence | Readiness |
| --- | --- | --- |
| Recovery/workspace | Verified archive, 122/122 dirty files equal to Task 1, independent clean Task 1-descendant clone | **Verified** |
| Canonical data | Raw CRLF identity, parsed LF-equivalent lineage, structural validator and real/synthetic tests | **Contract ready; external data validity unverified** |
| RV/RVD features | Exact f10 formulas, versioned metadata, warm-up/gap and future-mutation tests | **Contract ready** |
| Model outputs/fits | Variable-K probability blocks, inference kinds, accepted/rejected/failed/nonconverged dispositions | **Contract ready; no new model implemented** |
| Temporal causality | Explicit outcome ends, strict f10 purge, folds, delayed execution, raw-future mutation tests | **Contract ready** |
| State identity | Training-overlap Hungarian mapping, agreement, permutation, rare/zero occupancy | **Contract ready** |
| Density/selection | Same-raw-feature/date comparability and outer-fold inner-selection evidence | **Contract ready; historical rankings unrepaired** |
| Experiment provenance | Immutable directories, complete schema, output hashes, collisions, missing artifacts, failures | **Contract ready** |
| Control diagnostics | Mean/median distinction and causal/multi-dimensional matching thresholds | **Guard ready; no control/allocation run** |
| Regression evidence | 72 focused tests; seven requested 1c risk classes covered | **Verified at implementation review** |
| Existing platform/archive | 13 passed, 1 intentional frontend-not-built skip | **Verified with stated skip** |

## Migration-stage gate

| Later stage | Current state | Required gate before work |
| --- | --- | --- |
| Selective custom 1c HMM/filter adapter | **Not started; next technically addressable component only after explicit authorization** | Preserve immutable 1c reference; adapt to `ModelSpec`/`FitRecord`; validate Gaussian filtering against f10/hmmlearn on synthetic data; full/prefix future-mutation tests; fail closed on nonconvergence/rejection; variable K and state-ID tests; no baseline replacement |
| Forecast/predictive reactivation | **Blocked / not started** | HMM adapter accepted; every target matured by outcome end; raw future-price mutation tests for every horizon; OOS-filtered outputs only; no smoothed decision inputs |
| Discovery/specification search | **Blocked / not started** | Same-raw-feature/date predictive densities with Jacobian accounting; joint nested or predeclared causal selection; no future/global selection; failed candidate records; permutation/rare/zero-state gates |
| Allocation and synthetic controls | **Blocked / not started** | Accepted causal OOS signals; explicit delayed execution; causal control construction; correctly named mean/median statistics; exposure, turnover, volatility, and timing matching thresholds |
| Dashboard/API final integration | **Blocked / not started** | Accepted research outputs with immutable provenance; no latest-pointer identity; frontend/backend verification separately executed; existing f10 baseline preserved |
| E7 / prospective evaluation | **Blocked / not started** | Separate explicit authorization, frozen prospective protocol/data/decision boundary, and evidence that required future observations exist; no retrospective substitution |

## Conditional handoff for the next authorized HMM task

A later HMM task must not interpret “contract ready” as research approval. Its minimum acceptance packet is:

1. exact source commit and selective file list, with no wholesale 1c merge;
2. deterministic parameter-level filtering comparison against the preserved reference/hmmlearn where applicable;
3. `ProbabilityBlock` outputs for training and OOS filtering, with smoothing excluded from decisions;
4. `FitRecord` for every seed/fold, including explicit rejection/failure and nonconverged fallback;
5. variable state counts and arbitrary-label alignment on overlapping training dates;
6. raw-space predictive density only for identical ordered features/dates;
7. outer-fold causal selection records before any discovery comparison;
8. immutable experiment manifest with source/data/model/fold/seed/dependency/artifact hashes;
9. no claims of predictive value, significance, allocation value, or production readiness without separately executed evidence.

## Residual limitations

- Exact-source regression tests require the immutable 1c Git object. They fail with a fetch instruction rather than silently skipping.
- The parsed fingerprint establishes logical equality under the documented parser/format, not vendor correctness or licensing.
- Hungarian alignment measures training hard-label agreement; degenerate/tied or weak agreement remains a diagnostic requiring review, not proof of economically meaningful states.
- Rare-state defaults are configurable descriptive heuristics, not universal fit-acceptance thresholds.
- The new manifest is intentionally incompatible with incomplete historical manifests. A later adapter must enrich provenance from preserved evidence, not invent fields or rewrite history.
- The frontend was not built and no browser/E2E check was attempted. The isolated Python environment does not install unnecessary frontend tooling.
- Historical numerical effects of maturity, selection, density, and fallback defects remain unresolved because Task 2 did not rerun or repair the study.

## Gate statement

Task 2 supplies the requested contracts and regression evidence. It does **not** supply a migrated HMM, a corrected discovery study, a validated allocation, a production dashboard, E7 evidence, or prospective evidence. After final integrity/Git closure, work stops. Any subsequent stage requires explicit user authorization and its own acceptance tests.
