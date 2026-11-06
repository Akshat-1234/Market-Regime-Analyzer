# Task 4 — deterministic analysis and reproducibility reporting

This reporting layer does not fit models, select candidates, or change the frozen v1.0.0 protocol. It reads a completed, hash-verified recovery run and derives descriptive artifacts in a separate directory. The completed run remains immutable.

## Command

```bash
python -m research.discovery.analysis \
  --run research/experiments/task4_v1_0_0_recovery1 \
  --comparison-run research/experiments/task4_v1_0_0 \
  --output-dir research/experiments/task4_v1_0_0_analysis
```

The source run is checked with `verify_run` before analysis. The output directory must not already exist. `analysis_manifest.json` records the analysis source commit, source-run manifest hash, artifact hashes, and execution interval; `SHA256SUMS` covers the manifest and every derived artifact.

## Coverage verification

`coverage_verification.json` requires the complete Cartesian product of every declared outer fold, three inner folds, twelve candidates, and three seeds. With fourteen selected outer refits, the expected total is **1,526 records**: 1,512 inner attempts plus fourteen outer refits. If a fold is inconclusive before an outer refit, the expected total is reduced accordingly rather than silently fabricating an attempt.

The verifier checks unique fit IDs, exact candidate/seed coverage, declared train/validation/test boundaries, the selected candidate and seed used for each outer refit, compatible raw-density comparison keys within each inner fold, and complete selection/diagnostic/alignment records. Accepted attempts must contain evaluation boundaries. Failed attempts retain their transform and declared-fold evidence even when an engine exception prevented evaluation fields from being produced. Status, convergence, rejection, and failure counts include unsuccessful records.

The persisted candidate, selection, diagnostic, and alignment JSONL records must reproduce `aggregate_results.json` exactly through the unchanged aggregation function.

## Statistical and stability outputs

- `selected_model_path.csv`: selected candidate and seed by outer fold, adjacent-fold changes, and multi-seed selection agreement.
- `candidate_rankings.csv`: deterministic rank of every eligible candidate by its already recorded inner score. This is not a new selection rule.
- `seed_sensitivity.csv`: each seed's counterfactual single-seed winner using only existing inner scores. These rows are not alternate outer refits and do not substitute for the protocol's multi-seed decision.
- `state_occupancy.csv`: training and nonoverlapping outer-test hard counts, fractions, posterior weights, effective sample sizes, raw/aligned IDs, and the existing Task 2 rare-state flag for every state.
- `state_episodes.csv`: contiguous hard-state episodes within each annual outer test. Episodes do not cross annual fold boundaries because raw IDs are fold-local and aligned IDs can be unmatched or ambiguous.
- `stability_analysis.json`: candidate-persistence episodes and durations, candidate/seed change counts, seed-winner agreement, rare and zero-occupancy fold-state counts, duration distributions overall and by selected candidate, alignment status counts, agreement/unmatched/distance distributions, and explicit descriptive/nonclaim notes.

The rare-state flag is the predeclared Task 2 rule (`hard_count < 100` and `hard_fraction < 0.05`). It is not a retrospective quality or selection threshold. Duration summaries use sessions, not calendar time, and are descriptive rather than evidence of forecastability or economic value.

## Reproducibility comparison

`reproducibility_comparison.json` compares the recovery with the preserved initial execution for all seven numerical/core fold artifacts:

1. serialized selected model;
2. fold diagnostics;
3. inner selection;
4. state alignment;
5. training transform;
6. causal outer filtered probabilities and hard assignments;
7. scaled and raw outer predictive densities.

Comparison is byte-for-byte and includes SHA-256 values. Global recovery JSONL selection, diagnostic, and alignment objects are also compared with their per-fold initial-run counterparts. Fold-manifest source commit and execution timestamps are expected provenance differences, not numerical differences. The initial run remains explicitly marked as failed after fold production, not as a completed experiment.

Global candidate-attempt comparison is unavailable because the initial process lost its in-memory attempt list at final aggregation. The report says so; recovery coverage is instead independently verified against the frozen rectangular fold design. No absent initial-run record is reconstructed or claimed to have been preserved.

## Interpretation limits

Annual folds are descriptive units, overlapping training windows and daily observations are not independent samples, and no significance test is performed. Likelihood, convergence, occupancy, alignment, persistence, and seed agreement do not establish semantic regimes, predictive usefulness, economic usefulness, allocation value, or prospective performance. Negative, rare, ambiguous, unmatched, rejected, failed, nonconverged, and inconclusive outcomes remain visible.
