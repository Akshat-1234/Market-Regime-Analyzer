# Task 4 Results — nested RV regime discovery v1.0.0

## Bottom line

The frozen experiment executed completely and reproducibly, but it does **not** support a clean claim of five occupied, identifiable, temporally reproducible market regimes.

- **Numerical execution was successful:** all 14 outer folds were accepted; all 1,526 fits converged and were accepted. No candidate failure, rejection, nonconvergence, or inconclusive outer fold occurred.
- **K=5 was selected in all 14 folds.** The selected form was Gaussian full six times, Gaussian diagonal four times, and Student-t diagonal four times.
- **Model form was not stable:** the selected candidate changed in 8 of 13 adjacent pairs and the selected seed changed seven times. Median candidate persistence was one annual fold (maximum three).
- **Outer occupancy was concentrated:** 58 of 70 fold-state rows carried the existing rare-state flag; 26 had zero hard assignments. Thirteen of 14 years had at least one empty state. The median within-year dominant-state hard fraction was 59.8% (range 36.3%–100%). In 2017, one state received every hard assignment.
- **Alignment was mixed:** across 13 subsequent pairs, 41 of 65 states were accepted, 16 were ambiguous, and eight were new/unmatched. Agreement ranged from 0 to 1 (median 0.8). In 2025 all five mappings were ambiguous and none was forced.
- **Seed sensitivity was mostly about form, not K:** all counterfactual single-seed winners also had K=5. All three single-seed winners agreed on the exact candidate in 11 of 14 folds; 38 of 42 fold-seed winners matched the multi-seed selected candidate.

These findings concern latent density components under this protocol. They are not semantic bull/bear/crisis labels, return forecasts, trading signals, allocation evidence, economic usefulness, or prospective-holdout performance.

## Frozen execution and coverage

| Item | Verified value |
|---|---|
| Protocol | `task4-rv-nested-v1.0.0` |
| Protocol SHA-256 | `60aa2f84cf797155aa1003450121b37d0b89206929785fffb887dc8b7c432a16` |
| Fold-design SHA-256 | `09fea0230b86fa1ad132651591e4a597a4fed54e511534a5aae0997308615502` |
| Recovery source commit | `e96a7434d52e98b3cd34297df37cdeecd3ff44b7` |
| Execution interval (UTC) | 2026-11-06 09:18:50–10:07:18 |
| Outer tests | 2012–2025; 14 complete, nonoverlapping annual blocks; 3,437 rows |
| Inner attempts | 14 × 3 × 12 × 3 = **1,512** |
| Selected outer refits | **14** |
| Total retained attempts | **1,526 / 1,526 expected** |
| Fit status | 1,526 accepted; 0 rejected; 0 failed; 0 nonconverged |
| Fold status | 14 accepted; 0 inconclusive |
| Dataset / feature SHA-256 | `ea6dfffb…c5e4` / `e00dbde5…c72a9` |
| Artifact verification | 121 recovery checksums plus every Task 2 fold manifest verified |

`coverage_verification.json` independently checks the complete rectangular candidate/seed/inner-fold design, unique fit IDs, chronological boundaries, selected outer-refit identity, and compatible raw-density contracts. The stored aggregate also reproduces exactly from the persisted JSONL records. There are no missing unsuccessful candidate outcomes to explain: none occurred in this execution.

## Annual selections and outer diagnostics

Densities are per-observation raw-feature-space values in nats with the training-transform Jacobian included. Inner and outer columns describe different validation/test periods; their difference is not a return forecast or economic performance measure.

| Outer fold | Selected candidate | Seed | Inner raw density | Outer raw density | Training rare | Outer rare | Alignment agreement | Unmatched/ambiguous |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| 2012 | `k5_gaussian_full` | 42 | 4.5122 | 5.1304 | 20% | 80% | — | 0% |
| 2013 | `k5_gaussian_full` | 42 | 4.6181 | 5.2233 | 20% | 80% | 0.4 | 60% |
| 2014 | `k5_gaussian_full` | 42 | 4.5308 | 5.8374 | 20% | 80% | 0.4 | 60% |
| 2015 | `k5_gaussian_diag` | 2 | 4.8208 | 5.6126 | 20% | 80% | 1.0 | 0% |
| 2016 | `k5_gaussian_full` | 7 | 4.6832 | 5.8595 | 20% | 80% | 1.0 | 0% |
| 2017 | `k5_gaussian_diag` | 2 | 4.9775 | 5.2317 | 20% | 80% | 1.0 | 0% |
| 2018 | `k5_gaussian_diag` | 42 | 4.9146 | 5.7044 | 20% | 80% | 0.8 | 20% |
| 2019 | `k5_student_t_diag` | 42 | 5.1228 | 5.8452 | 20% | 80% | 0.8 | 20% |
| 2020 | `k5_gaussian_diag` | 2 | 4.9712 | 4.9524 | 20% | 80% | 1.0 | 0% |
| 2021 | `k5_student_t_diag` | 7 | 4.9257 | 5.8207 | 0% | 100% | 0.2 | 80% |
| 2022 | `k5_gaussian_full` | 7 | 5.0518 | 5.4537 | 20% | 100% | 0.2 | 80% |
| 2023 | `k5_gaussian_full` | 7 | 5.2230 | 6.1407 | 20% | 80% | 0.4 | 60% |
| 2024 | `k5_student_t_diag` | 42 | 5.1935 | 5.8078 | 20% | 80% | 1.0 | 0% |
| 2025 | `k5_student_t_diag` | 42 | 4.7771 | 6.3374 | 0% | 80% | 0.0 | 100% |

The initial 2012 alignment establishes fold-local structural IDs and has no predecessor agreement. “Unmatched/ambiguous” is the alignment record's non-accepted frequency, combining explicit new/unmatched and ambiguous states.

## Descriptive distributions

Annual folds are the units below. Overlapping training windows, repeated candidates, and daily observations are not independent samples; no significance test or pooled-independent claim is made.

| Metric | n | Mean | Median | Sample SD | Min | Max |
|---|---:|---:|---:|---:|---:|---:|
| Selected inner raw log density / observation | 14 | 4.8802 | 4.9202 | 0.2327 | 4.5122 | 5.2230 |
| Outer raw log density / observation | 14 | 5.6398 | 5.7561 | 0.3961 | 4.9524 | 6.3374 |
| Training posterior entropy (nats) | 14 | 0.0829 | 0.0827 | 0.0105 | 0.0655 | 0.1051 |
| Outer posterior entropy (nats) | 14 | 0.0808 | 0.0803 | 0.0362 | 0.0001 | 0.1353 |
| Training mean maximum posterior confidence | 14 | 0.9677 | 0.9678 | 0.0042 | 0.9589 | 0.9747 |
| Outer mean maximum posterior confidence | 14 | 0.9675 | 0.9704 | 0.0161 | 0.9424 | 1.0000 |
| Training rare-state fraction | 14 | 0.1714 | 0.2000 | 0.0726 | 0.0000 | 0.2000 |
| Outer rare-state fraction | 14 | 0.8286 | 0.8000 | 0.0726 | 0.8000 | 1.0000 |
| Subsequent alignment agreement | 13 | 0.6308 | 0.8000 | 0.3728 | 0.0000 | 1.0000 |

High posterior confidence and low entropy do not resolve the occupancy and alignment problems: a model can be confidently concentrated in a small subset of its components.

The existing rare-state characterization is `hard_count < 100` **or** `hard_fraction < 0.05`. With roughly 250 outer rows and five states, the count condition makes the flag common even for non-empty states. Therefore 58/70 rare must not be read as 58/70 empty. The separate zero-assignment result (26/70, affecting 13/14 years) and dominant-state fractions provide the sharper occupancy evidence. The rare flag was not used to select or reject outer models.

## Selection and seed sensitivity

| Selected item | Frequency across 14 folds |
|---|---:|
| `k5_gaussian_full` | 6 |
| `k5_gaussian_diag` | 4 |
| `k5_student_t_diag` | 4 |
| Seed 2 / 42 / 7 | 3 / 7 / 4 |
| Candidate changes | 8 / 13 adjacent pairs |
| Seed changes | 7 / 13 adjacent pairs |

There were nine candidate-persistence episodes: 2012–2014 full Gaussian; 2015 diagonal Gaussian; 2016 full Gaussian; 2017–2018 diagonal Gaussian; 2019 Student-t; 2020 diagonal Gaussian; 2021 Student-t; 2022–2023 full Gaussian; and 2024–2025 Student-t.

The selected candidate's within-fold complete-seed score spread had median 0.000120 and maximum 0.070400 raw log-density units per observation. Exact candidate choice was less seed-stable than K: 2014, 2015, and 2017 had disagreement among single-seed winners. In addition, 11 of 14 folds had a best-versus-runner-up inner-score gap below 0.005 per observation. This cautions against treating the particular covariance/emission winner as a sharply identified structural choice. Full rankings and all seed counterfactuals are retained in `candidate_rankings.csv` and `seed_sensitivity.csv`; no alternate outer refit was performed.

## State alignment, occupancy, and duration

Among 65 states in subsequent fold pairs:

| Alignment outcome | Count | Share |
|---|---:|---:|
| Accepted | 41 | 63.1% |
| Ambiguous, mapping left blank | 16 | 24.6% |
| New/unmatched, new structural ID | 8 | 12.3% |

Accepted mappings had training-profile distance median 0.0117 and maximum 0.1872. These are distances for already accepted mappings, not evidence that unmatched states should have been forced. Self-transition probabilities of accepted pairs were often similar (median absolute difference 0.00083), while expected-duration differences had median 0.783 sessions and maximum 33.707. Implied geometric duration and observed hard episodes are different quantities.

There were 148 outer hard-state episodes when segmented separately within each annual test. Duration median was 13 sessions, mean 23.223, maximum 248, and 14 episodes (9.46%) lasted one session. These durations do not cross annual boundaries and do not establish cross-year regime persistence, especially where alignment was ambiguous or unmatched.

## Reproducibility and preserved engineering failure

The initial execution at source `123ca197…` produced all 14 fold directories and then failed during final aggregation because it read `candidate_id` instead of `selected_candidate_id`. Its in-memory global candidate attempts were lost. That directory remains preserved with `FAILED_RUN.json`; it is not represented as a completed experiment.

Commit `e96a743…` made only the aggregation-key and incremental-persistence repairs. The independent recovery completed with all attempts present. Comparison against the preserved fold outputs shows:

- **98/98 core artifacts byte-identical** (14 folds × seven model/diagnostic/selection/alignment/transform/probability/density artifacts);
- **42/42 global selection, diagnostic, and alignment objects identical** to their preserved per-fold counterparts;
- fold-manifest source commit and execution timestamps are expected provenance differences;
- initial global candidate attempts remain unavailable and are not fabricated; recovery coverage is instead verified against the frozen design.

A reporting-only alignment-key error (`fold_id` versus `current_fold_id`) was subsequently fixed before derived analysis. It did not alter the experiment, recovery artifacts, candidate decisions, or numerical outputs. The incomplete derived directory and execution log were preserved outside the result directories.

The final recovery passed `verify_run`, every nested Task 2 `verify_experiment`, and independent `sha256sum -c` checks. The analysis directory has its own manifest and nine verified checksum entries.

## Limitations and unresolved questions

1. **K is stable; interpretation is not.** Repeated K=5 selection can reflect density approximation under this grid, not five real market regimes.
2. **Outer occupancy is weak.** Empty components and dominant-state concentration limit a claim that all five states are empirically occupied out of sample.
3. **Cross-year identity is incomplete.** Ambiguous and unmatched mappings are material, including complete ambiguity in 2025.
4. **Exact model form is sensitive.** Candidate and seed paths vary, often with small inner-score gaps.
5. **Annual boundaries only.** No shifted-boundary protocol was predeclared; boundary robustness remains unresolved.
6. **Small descriptive fold count.** Fourteen annual folds do not support independent-sample significance claims.
7. **Rare-state count convention.** The `<100` rule is stringent in annual five-state blocks and must be read alongside zero counts and fractions.
8. **No economic evaluation.** Predictive feature density does not predict direction or establish return, allocation, trading, or economic value.
9. **No extra families/features.** Conclusions are bounded to close-only return/volatility features and the frozen Gaussian/Student-t grid.
10. **Retrospective diagnostic scope.** Smoothed probabilities were not used; outer inference was causal continuation from each training terminal filtered state. That causal mechanics validation is not a prospective-holdout claim.

## Result artifacts

- Completed immutable run: `research/experiments/task4_v1_0_0_recovery1/`
- Aggregate distributions: `research/experiments/task4_v1_0_0_recovery1/aggregate_results.json`
- Every candidate attempt: `research/experiments/task4_v1_0_0_recovery1/candidate_fits.jsonl`
- Coverage verification: `research/experiments/task4_v1_0_0_analysis/coverage_verification.json`
- Stability summary: `research/experiments/task4_v1_0_0_analysis/stability_analysis.json`
- Occupancy and episodes: `state_occupancy.csv`, `state_episodes.csv` in that analysis directory
- Rankings and seed sensitivity: `candidate_rankings.csv`, `seed_sensitivity.csv`
- Reproducibility: `research/experiments/task4_v1_0_0_analysis/reproducibility_comparison.json`
- Preserved failed initial execution: `research/experiments/task4_v1_0_0/FAILED_RUN.json`
- Reporting method: `docs/TASK4_ANALYSIS.md`

**Council C conclusion:** execute-and-report acceptance is met; a positive scientific claim of robust five-regime discovery is not. Preserve the mixed/negative result and do not tune the protocol retrospectively.
