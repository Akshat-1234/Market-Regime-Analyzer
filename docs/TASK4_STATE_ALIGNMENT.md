# Task 4 — Training-Only State Identity and Alignment

## Local identity rule

State IDs are always local to one fitted model (`local_0`, …). They carry no semantic ordering and are never compared directly across folds. Original probability columns remain in local order in `outer_filtered.csv`; mappings are stored separately, and a separate hard aligned-ID column never rewrites those probabilities.

## Training profiles

For each selected outer model, Task 2 `posterior_weighted_characteristics` computes training-filtered posterior-weighted means of raw `daily_return` and `volatility_20` for every local state. These are contemporaneous feature profiles, not forward-return profiles. Training occupancy uses Task 2 `summarize_occupancy`, with rare defined by hard count <100 or hard fraction <0.05. Effective sample size is `(sum w)^2/sum(w^2)` from training posterior weights.

## Distance and matching

For adjacent accepted folds `r` and `c`, each feature is scaled by:

`scale_j = sqrt((variance_r,j + variance_c,j) / 2)`,

using only the two training frames with `ddof=0`. The current-to-reference profile distance is Euclidean distance in this two-dimensional scaled space. `scipy.optimize.linear_sum_assignment` minimizes total distance over a rectangular matrix, yielding at most `min(K_r,K_c)` proposed one-to-one matches.

A proposed match is accepted only when:

- distance ≤ 2.0;
- the minimum row/column alternative margin is ≥0.25;
- the reference local state has an inheritable aligned ID.

Confidence is reported descriptively as `1/(1+distance)`. Agreement is accepted matches divided by `min(K_r,K_c)`. Unmatched frequency is the fraction of current states not accepted. These thresholds are fixed before results and are not stability significance tests.

## Unmatched and ambiguous states

- Extra states in a rectangular match, excessively distant states, or broken identity chains receive `new_unmatched` and a new fold/local structure ID. This records non-correspondence rather than forcing equality.
- A proposed pair with acceptable distance but insufficient margin is `ambiguous` and receives no aligned ID. It is not forced into a persistent identity.
- The first accepted fold, or a restart after an inconclusive fold, uses `initial_unaligned` fold/local structure IDs. These are bookkeeping identifiers, not bull/bear/etc. labels.
- The next alignment can inherit only an existing non-null reference aligned ID. Raw local IDs and proposed reference IDs remain in every record.

## Stability measurements

For accepted adjacent matches only, diagnostics compare:

- training profile distance;
- absolute self-transition difference;
- absolute implied expected-duration difference;
- absolute training posterior-occupancy difference;
- absolute mean empirical hard-episode-duration difference.

Implied duration `1/(1-A_jj)` is geometric-model persistence, not observed persistence. Empirical hard episodes are sensitive to posterior uncertainty and arbitrary local labels; the two are reported side by side rather than conflated. Alignment agreement itself does not prove economic similarity.

## Leakage and tests

The alignment API has no outer-test probabilities, outer-test features, returns, or density inputs. Tests cover label permutation invariance, rectangular unmatched states, ambiguous pairs, distant states, and initialization without outer data. Temporal tests independently establish that outer mutation cannot alter inner selection and that filtered prefixes are causal.

Task 2's existing hard-contingency alignment is retained for equal-K contract users. Discovery uses Task 2 profile/occupancy primitives with a separate documented rectangular profile method because selected K may differ across folds.
