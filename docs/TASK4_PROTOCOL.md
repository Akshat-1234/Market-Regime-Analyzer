# Task 4 Protocol v1.0.0 — Frozen Before Outer Experiments

**Protocol ID:** `task4-rv-nested-v1.0.0`

**Protocol manifest:** `provenance/task4_protocol_v1_0_0.json`

**Manifest SHA-256:** `60aa2f84cf797155aa1003450121b37d0b89206929785fffb887dc8b7c432a16`

**Fold-design SHA-256:** `09fea0230b86fa1ad132651591e4a597a4fed54e511534a5aae0997308615502`

**Engine:** `task3-hmm-engine-v1.1`; freeze manifest SHA-256 `53f61c24e75ddda81e374ce4629cb88cf1fb521a5dc8c1d91d1a68ce95cd0ea9`

This version was written, reviewed, tested, and committed before any real Task 4 candidate fit. No outer-fold outcome was available when these choices were frozen.

## Research question

Do bounded Gaussian/Student-t HMM specifications produce occupied, identifiable, and temporally reproducible latent states in close-only NIFTY RV features, when each specification is selected strictly by chronological inner validation? Higher likelihood, convergence, occupancy, or self-transition alone is not evidence of predictive or economic usefulness.

## Data and features

- Canonical `research/data/nifty_index.csv`: 4,684 rows, 2007-09-17–2026-10-22, raw SHA-256 `ea6dfffb93e5eabd8b6a2f96cd40d6b3ec5c7f47f2f9e6c0cbd3ca9a5f2ac5e4`.
- Task 2 f10 close-only RV contract, ordered `[daily_return, volatility_20]`; 4,664 complete rows, 2007-10-16–2026-10-22.
- Complete feature/date SHA-256 `e00dbde54886443dd3b0b80c84ef9b7e99d965d61591ba01a0892df68a6c72a9`; feature-manifest SHA-256 `552f25dddf194933ab95a2e9e26341bcdad4042ef59b91c5290e92a6be3ddda1`.
- No internal-gap imputation or additional features. Each train/validation/test transform is a training-only z-score with population `ddof=0`.

## Candidate grid and seeds

For each K in `{2,3,4,5}`:

1. Gaussian diagonal;
2. Gaussian full;
3. Student-t diagonal with initial dof 6.

This gives 12 candidates. Seeds are exactly `[2,42,7]`. Every inner fit uses cap 200, relative tolerance `1e-5`, minimum covariance `1e-4`, and sticky 0. Candidate/seed/fold attempts remain recorded whether accepted, nonconverged, occupancy-rejected, or failed. No outer outcome may alter this grid or these settings.

## Acceptance and selection

- Minimum hard training occupancy per local state: 2%; accepted convergence is mandatory.
- A seed is complete for a candidate only when accepted in all three inner folds for that outer fold.
- A candidate is eligible with at least two complete seeds.
- Each score is mean per-observation **raw-space** predictive log density on the subsequent 126-row inner validation block.
- Candidate score is the mean of all eligible seed/fold scores. Task 2 `select_candidate_for_fold` performs deterministic candidate-ID tie-breaking.
- The selected seed has the highest mean inner score among complete seeds, with the smallest numeric seed winning a tie.
- If no candidate has two complete seeds, the outer fold is inconclusive. No fallback specification is manufactured.
- The selected candidate/seed is refit once on full outer training. If that refit is not accepted, the fold is inconclusive and produces no accepted outer block.

## Density comparability

For `z=(x-mean)/scale`, the model yields `log p_z(z)`. Discovery converts it to `log p_x(x)=log p_z(z)-sum(log(scale))` and constructs Task 2 `PredictiveDensity(space="raw", transformation_jacobian_included=True)`. All accepted candidates in the same inner fold must pass Task 2 density comparability checks for dates, features, units, dimension, space, and Jacobian declaration. Scaled densities are retained separately and never compared across different transforms.

## Temporal design

Outer tests are complete calendar years 2012–2025 with expanding training and nonoverlapping subsequent annual blocks. Partial 2026 is excluded. Each outer training window has three inner validation endpoints at `floor(linspace(504+126, outer_train_rows, 3))`; every validation has 126 rows and training expands to the row immediately before it. Exact dates/counts are frozen in `provenance/task4_fold_design_v1_0_0.json` and listed in `TASK4_TEMPORAL_VALIDATION.md`.

Outer observations cannot influence candidate/seed selection, scaling, thresholds, alignment, or rejection. Only after inner selection and full-training refit does the model filter the untouched outer block from the terminal training filtered state.

## Alignment and diagnostics

Training-filtered posterior-weighted raw feature profiles characterize local states. Adjacent accepted folds use scaled profile distances and rectangular Hungarian matching with explicit unmatched/ambiguous states. Thresholds and margins are frozen in `TASK4_STATE_ALIGNMENT.md`; outer probabilities/profiles/outcomes are not alignment inputs.

Fold diagnostics retain fit/convergence/iterations/likelihoods, inner and outer densities separately, precise regularization counters, occupancy/effective sample size, raw state profiles, transitions, implied and empirical episode durations, entropy/confidence, rare states, alignment agreement, unmatched states, and adjacent stability differences. Aggregates report fold distributions (n, mean, median, sample standard deviation, min, max), not pooled-independent significance tests.

## Sensitivity, limitations, and non-claims

Seed sensitivity is measured from inner complete-seed scores and selected-seed frequencies. Annual fold distributions describe boundary variation, but no shifted-boundary protocol was predeclared; shifted-boundary robustness remains unresolved rather than retrospectively tuned.

This protocol does not test forecasting, return prediction, allocation, strategy performance, trading signals, economic usefulness, E7, dashboards, prospective holdout performance, or live investment value. It does not assign bull/bear/crisis/recovery/expansion labels. Negative and inconclusive outcomes are valid and must be preserved.

Any methodological change requires a new protocol version, preserved old outputs, and exploratory labeling. No such change is permitted merely to improve observed outer results.
