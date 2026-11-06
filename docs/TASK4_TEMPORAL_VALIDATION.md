# Task 4 — Nested Temporal Validation Design

## Frozen outer folds

All rows are complete Task 2 RV feature rows. Training always starts on 2007-10-16 and expands; test blocks are subsequent, calendar-year bounded, and nonoverlapping. Partial 2026 is excluded by protocol.

| Outer fold | Training dates | Train rows | Outer-test dates | Test rows |
|---|---|---:|---|---:|
| outer_2012 | 2007-10-16–2011-12-30 | 1030 | 2012-01-03–2012-12-31 | 242 |
| outer_2013 | 2007-10-16–2012-12-31 | 1272 | 2013-01-02–2013-12-31 | 247 |
| outer_2014 | 2007-10-16–2013-12-31 | 1519 | 2014-01-02–2014-12-31 | 240 |
| outer_2015 | 2007-10-16–2014-12-31 | 1759 | 2015-01-02–2015-12-31 | 244 |
| outer_2016 | 2007-10-16–2015-12-31 | 2003 | 2016-01-04–2016-12-30 | 244 |
| outer_2017 | 2007-10-16–2016-12-30 | 2247 | 2017-01-02–2017-12-29 | 248 |
| outer_2018 | 2007-10-16–2017-12-29 | 2495 | 2018-01-02–2018-12-31 | 245 |
| outer_2019 | 2007-10-16–2018-12-31 | 2740 | 2019-01-02–2019-12-31 | 241 |
| outer_2020 | 2007-10-16–2019-12-31 | 2981 | 2020-01-01–2020-12-31 | 250 |
| outer_2021 | 2007-10-16–2020-12-31 | 3231 | 2021-01-01–2021-12-31 | 248 |
| outer_2022 | 2007-10-16–2021-12-31 | 3479 | 2022-01-03–2022-12-30 | 248 |
| outer_2023 | 2007-10-16–2022-12-30 | 3727 | 2023-01-02–2022-12-29 | 245 |
| outer_2024 | 2007-10-16–2023-12-29 | 3972 | 2024-01-01–2024-12-31 | 246 |
| outer_2025 | 2007-10-16–2024-12-31 | 4218 | 2025-01-01–2025-12-31 | 249 |

The first training window exceeds the predeclared 756-row minimum and supports K=5 after the Task 2 feature warm-up. The final outer fold has 4,218 training rows. No fold uses the partial 2026 block.

## Inner construction

For outer training length `N`, validation endpoints are `floor(linspace(630, N, 3))`. For endpoint `e`, training is rows `[0:e-126]` and validation is rows `[e-126:e]`. Training therefore has at least 504 rows, validation always 126, and validation ends no later than outer training. Validation blocks are nonoverlapping; later inner training expands through earlier observations.

The frozen 2012 inner folds illustrate the rule:

| Inner fold | Train dates | Train rows | Validation dates | Validation rows |
|---|---|---:|---|---:|
| outer_2012_inner_01 | 2007-10-16–2009-11-11 | 504 | 2009-11-12–2010-05-19 | 126 |
| outer_2012_inner_02 | 2007-10-16–2010-08-31 | 704 | 2010-09-01–2011-03-03 | 126 |
| outer_2012_inner_03 | 2007-10-16–2011-06-21 | 904 | 2011-06-22–2011-12-30 | 126 |

All 42 inner-fold boundary records are in `provenance/task4_fold_design_v1_0_0.json`, SHA-256 `09fea0230b86fa1ad132651591e4a597a4fed54e511534a5aae0997308615502`.

## Leakage controls

1. `evaluate_inner_fold` reads only outer-training slices; the outer-test block is not passed to candidate fitting or selection.
2. `TrainingTransform.fit` sees only the relevant inner/outer training frame. Validation/test values cannot change its mean, scale, or log-Jacobian.
3. Each candidate must satisfy the same convergence, occupancy, and complete-inner coverage rules. Unsuccessful attempts remain visible.
4. Selection uses Task 2 `SelectionScore` chronology checks and deterministic selection only after complete-seed eligibility is established.
5. Raw-space density conversion uses the training scale; candidates in one validation block must satisfy Task 2 comparability contracts.
6. The final outer model is refit only after selection. OOS filtering starts from its final training log-alpha and uses no future rows for earlier probabilities.
7. Alignment receives only training-filtered probabilities and training raw features.
8. Executable tests mutate outer observations and require byte-identical inner fit/selection records, mutate validation while requiring identical fitted parameters, and mutate future OOS rows while requiring unchanged filtered prefixes.

## Reporting boundaries

Training likelihood, inner-validation density, and outer-test density are separate fields. Outer density is held-out descriptive evaluation, never a selection objective. Annual repeated observations are not treated as independent samples; no significance claim is made from repeated candidates or overlapping training windows.

The annual design supports fold-to-fold descriptive sensitivity only. No alternative shifted annual boundary was frozen, so no shifted-boundary sensitivity result may be claimed.
