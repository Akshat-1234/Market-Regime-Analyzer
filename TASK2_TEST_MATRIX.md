# Task 2 Test Matrix

**Focused result at implementation review:** 72 passed, 0 failed, 0 skipped (62 contract tests, including parameterized cases, and 10 historical regression tests).
**Existing suite at implementation review:** 13 passed, 1 skipped; the skip is the pre-existing unbuilt-frontend check.
**Scope:** deterministic synthetic fixtures, canonical byte inspection, exact f10 formula parity, and immutable 1c source behavior/dataflow. No NIFTY model refit or research reproduction was run.

## Contract tests

| ID | Contract / failure risk | Fixture and meaningful assertion | Test node(s) |
| --- | --- | --- | --- |
| C-DATA-01 | Canonical NIFTY identity | Verify exact raw hash, parsed fingerprint shape, 4,684 rows, dates, order, CRLF | `test_data_contract.py::test_canonical_nifty_raw_identity_schema_and_dates` |
| C-DATA-02 | CRLF/LF conflation | Same parsed rows/fingerprint, deliberately different raw hashes | `test_line_ending_changes_raw_identity_but_not_parsed_identity` |
| C-DATA-03 | Defensive parsing | Valid synthetic data becomes date-indexed copy; source mutation cannot alter it | `test_synthetic_ohlc_validator_returns_defensive_date_indexed_copy` |
| C-DATA-04 | Missing/nonnumeric fields | Four parameterized OHLC columns must reject text/missing data | `test_synthetic_missing_or_nonnumeric_ohlc_is_rejected` (4 cases) |
| C-DATA-05 | Duplicate/unsorted dates | Both date defects raise | `test_synthetic_duplicate_or_unsorted_dates_are_rejected` |
| C-DATA-06 | Impossible OHLC envelope | High below close and low above close raise separately | `test_synthetic_invalid_ohlc_envelope_is_rejected` |
| C-DATA-07 | Nonpositive/nonfinite prices | Zero and infinity raise with distinct reasons | `test_synthetic_nonpositive_or_infinite_prices_are_rejected` |
| C-DATA-08 | Schema/hash substitution | Reordered canonical columns and incorrect raw hash raise | `test_canonical_order_and_raw_hash_mismatch_are_rejected` |
| C-DATA-09 | Invalid calendar/schema | Impossible date and omitted Open raise | `test_invalid_calendar_date_and_missing_column_are_rejected` |
| C-FEAT-01 | RV formula/warm-up | Hand-calculated simple returns and 20-return sample volatility; first valid row 20 | `test_feature_contract.py::test_daily_return_and_sample_volatility_match_hand_calculation` |
| C-FEAT-02 | Drift from f10 | Exact value parity against actual f10 feature implementation for RV and RVD columns | `test_contract_features_match_actual_f10_formulas_for_rv_and_rvd` |
| C-FEAT-03 | RVD semantics | Hand-calculated trailing-252 drawdown and all first-valid positions | `test_rvd_drawdown_warmup_and_hand_calculation` |
| C-FEAT-04 | Feature look-ahead | Future close mutation leaves the entire earlier feature prefix unchanged | `test_feature_prefix_is_invariant_to_future_close_mutation` |
| C-FEAT-05 | Silent imputation | Internal missing feature rows remain missing and fitting trim rejects them | `test_feature_gaps_are_not_imputed_and_internal_gap_is_rejected` |
| C-FEAT-06 | Incorrect trimming | Only 20 common RV warm-up rows are removed | `test_complete_feature_rows_trims_only_leading_warmup` |
| C-FEAT-07 | Version/feature-family drift | Manifest fixes version, columns, ddof and gap policy; new family rejected | `test_feature_manifest_is_versioned_and_rejects_new_family` |
| C-TIME-01 | Ambiguous forward targets | Hand value and explicit decision/outcome-end dates; no fabricated trailing labels | `test_temporal_contract.py::test_forward_labels_have_explicit_outcome_end_and_hand_value` |
| C-TIME-02 | Target maturity boundary | `decision < test_start` and `outcome_end < test_start`; equality excluded | `test_maturity_is_strict_for_decision_and_outcome_end` |
| C-TIME-03 | Raw future-price leakage | Future mutations cannot change matured label prefix, while unpurged labels can change | `test_future_price_mutation_cannot_change_matured_prefix_labels` |
| C-TIME-04 | Crossing horizon | Decision inside training with outcome after test start is excluded | `test_boundary_crossing_label_is_excluded_even_when_decision_is_in_training` |
| C-TIME-05 | Filter look-ahead | Full and prefix runs of a deterministic fake recursive filter agree under future mutation | `test_fake_recursive_filter_full_and_prefix_agree_under_future_mutation` |
| C-TIME-06 | Fold chronology | Annual folds expand and satisfy train end before test start | `test_annual_folds_are_expanding_ordered_and_refit_at_test_start` |
| C-TIME-07 | Execution gap | Delayed execution and next-return date must be strictly ordered | `test_execution_timing_preserves_delayed_first_return_gap` |
| C-TIME-08 | Invalid temporal inputs | Nonpositive horizon/outcome ordering and empty schedules fail | `test_invalid_label_or_empty_fold_schedule_is_rejected` |
| C-MODEL-01 | Probability semantics | K=4 plus all four inference kinds; only smoothed is noncausal | `test_model_contract.py::test_probability_block_distinguishes_inference_kinds_for_variable_k` |
| C-MODEL-02 | Invalid probabilities | Five parameterized shape/range/sum/finite failures | `test_invalid_probability_shapes_and_values_are_rejected` (5 cases) |
| C-MODEL-03 | Date/state alignment | Length, duplicate IDs, and duplicate dates raise | `test_probability_dates_and_state_ids_must_align` |
| C-MODEL-04 | Accepted-fit disposition | Accepted fit requires convergence, parameters, no fallback | `test_accepted_fit_requires_convergence_parameters_and_no_fallback` |
| C-MODEL-05 | Convergence fallback | Nonconverged fallback is explicit and never supplies usable OOS output | `test_nonconverged_fallback_is_explicit_but_never_usable` |
| C-MODEL-06 | Rejection/failure | Rejected and failed fits need distinct reasons | `test_rejected_and_failed_fits_require_reasons_and_cannot_supply_oos` |
| C-MODEL-07 | Training-output confusion | Training dates/assignments and inference kinds are validated | `test_training_assignments_and_block_dates_are_explicit` |
| C-MODEL-08 | Likelihood comparability | Same raw vectors accepted; dimension, scaled-space, Jacobian, date mismatches rejected | `test_density_comparison_requires_identical_raw_features_dates_and_jacobian` |
| C-MODEL-09 | Inner selection | Only outer-specific inner scores; deterministic tie break | `test_inner_selection_uses_only_pre_outer_validation_and_deterministic_ties` |
| C-MODEL-10 | Future/global selection | Crossing evidence raises; unrelated later fold cannot change earlier decision | `test_future_fold_or_global_selection_evidence_is_rejected` |
| C-MODEL-11 | Fit/OOS consistency | Probability K and OOS start must match model/training | `test_fit_probability_state_count_and_oos_boundary_match_model_and_training` |
| C-MODEL-12 | Model configuration | Single-state and unversioned specifications rejected | `test_model_spec_rejects_single_state_and_unversioned_configuration` |
| C-STATE-01 | Label switching | Hungarian mapping restores permuted training probabilities | `test_state_contract.py::test_state_alignment_is_permutation_invariant_and_uses_explicit_mapping` |
| C-STATE-02 | Double permutation | Occupancy is computed exactly once after permutation | `test_occupancy_tracks_permuted_columns_exactly_once` |
| C-STATE-03 | Rare/zero/K variability | Four states, rare state, zero count, and posterior mass remain explicit | `test_rare_and_zero_occupancy_states_are_explicit_for_variable_k` |
| C-STATE-04 | Empty-state descriptions | Zero-weight means are null, not fabricated zero | `test_zero_weight_characteristics_are_null_not_fake_zero` |
| C-STATE-05 | Look-ahead alignment | Smoothed, OOS, and generic filtered inputs rejected for training alignment | `test_alignment_rejects_smoothed_or_oos_inputs` |
| C-STATE-06 | Adjacent refit overlap | Shifted training windows align only on three shared dates; later row excluded | `test_alignment_uses_only_overlap_of_adjacent_expanding_training_windows` |
| C-STATE-07 | Invalid alignment | No overlap and different K fail | `test_alignment_requires_overlapping_dates_and_state_count` |
| C-PROV-01 | Complete provenance | Immutable directory verifies without creating LATEST | `test_experiment_contract.py::test_complete_manifest_creates_immutable_verifiable_directory_without_latest` |
| C-PROV-02 | Incomplete identity | Missing source/dataset and feature/model mismatch rejected | `test_incomplete_source_or_feature_model_identity_is_rejected` |
| C-PROV-03 | Hash/fold validation | Malformed data hash and leaking fold boundary rejected | `test_manifest_hashes_and_fold_order_are_machine_checked` |
| C-PROV-04 | Output collision | Second create raises and original manifest bytes remain unchanged | `test_output_collision_is_never_overwritten` |
| C-PROV-05 | Artifact completeness | Missing declaration/payload, pre-write hash mismatch, and deleted artifact detected | `test_undeclared_missing_or_hash_mismatched_artifacts_are_rejected` |
| C-PROV-06 | Unrecorded/modified output | Extra file and modified payload detected | `test_unrecorded_output_and_modified_artifact_are_detected` |
| C-PROV-07 | Identity/path safety | Traversal and LATEST as identity rejected | `test_path_traversal_and_latest_identity_are_rejected` |
| C-PROV-08 | Failure recording | Failure remains failed; accepted nonconverged record rejected | `test_failure_recording_does_not_become_success` |
| C-PROV-09 | Rejected-fit record | Reason and completed-run warning required | `test_rejected_fit_is_explicit_and_completed_run_carries_warning` |
| C-CONTROL-01 | Mean/median mislabel | `[.01,.02,.90]` yields mean `.31`, median `.02` | `test_controls_contract.py::test_exposure_ks_mean_and_median_are_not_conflated` |
| C-CONTROL-02 | Incomplete matching claim | Named KS statistic, turnover and volatility thresholds all enforced | `test_matching_claim_uses_named_statistic_and_all_dimensions` |
| C-CONTROL-03 | Noncausal control | Matching fails closed despite distribution match | `test_noncausal_control_fails_closed_even_when_distribution_matches` |

## Historical regression tests

All exact 1c blobs are read with `git show c46541e9…:<path>` and checked against Task 1's recorded raw SHA-256 before use. These tests do not change the historical modules.

| ID | Known 1c risk | Evidence and limitation | Test node |
| --- | --- | --- | --- |
| R-1C-01 | Target maturity | Execute exact `expanding_oos`; mutating a row-3 target whose outcome ends at row 6 changes first forecast at row 4. Contract purge excludes it. This reproduces the implementation defect, not its historical numerical impact. | `test_1c_temporal_regression.py::test_exact_1c_expanding_oos_uses_immature_boundary_target` |
| R-1C-02 | Raw future mutation | Matured label set is invariant even when full unpurged label set changes | `test_maturity_guard_keeps_only_labels_unchanged_by_raw_future_mutation` |
| R-1C-03 | Convergence fallback | Exact `fit_spec_fold` with deterministic nonconverged `HMMFit` reports and uses fallback; new fit contract refuses OOS use | `test_1c_model_regression.py::test_exact_1c_nonconverged_fallback_is_used_when_no_fit_converged` |
| R-1C-04 | Double occupancy permutation | Verify exact source ordering and synthetic mismatch between returned and correct per-state occupancy | `test_exact_1c_double_permuted_occupancy_reproduction` |
| R-1C-05 | Future-fold/global selection | AST/source proves `best_k` selected after full sweep and reused by downstream `run_all`; no historical rerun or impact estimate | `test_exact_1c_selection_is_global_after_all_folds_not_joint_nested` |
| R-1C-06 | Cross-dimensional likelihood | Exact source uses scaled-space mean density and ranks feature sets of dimensions 2 and 3 without a Jacobian; no repaired ranking claimed | `test_exact_1c_scaled_density_is_compared_across_different_dimensions` |
| R-1C-07 | Incomplete provenance | Actual preserved study manifest fails new schema for missing source/artifact/version fields; old file untouched | `test_1c_provenance_controls_regression.py::test_exact_1c_reference_manifest_fails_new_provenance_contract` |
| R-1C-08 | Matching-statistic mislabel | Exact source computes `np.mean` under `median_exposure_ks`; corrected summary distinguishes mean/median | `test_exact_1c_median_exposure_key_computes_mean` |
| R-1C-09 | Circular-control causality | Exact `phase_shift` wraps late exposures into early positions; marginal preservation is not causal evidence | `test_exact_1c_phase_shift_wraps_future_into_past` |
| R-1C-10 | Dataset raw/parsed lineage | Exact 1c LF root CSV has its recorded distinct raw hash but identical parsed rows/fingerprint to canonical CRLF CSV | `test_source_lineage_regression.py::test_1c_csv_is_lf_raw_distinct_but_parsed_equivalent` |

## Existing tests and intentional non-execution

| Suite | Result / meaning |
| --- | --- |
| `tests/test_historical_archive.py` | 2 passed: original ZIP members/hashes and Arena archive hash unchanged |
| `tests/test_research_platform.py` | 11 passed, 1 skipped: synthetic platform/API checks; skip reason `Frontend has not been built` |
| Frontend/browser | Not executed; outside Task 2 and frontend was not built |
| Historical model fitting, study reranking, allocation simulation, prospective validation | Not executed; explicitly outside Task 2 |

A regression test passing means the documented historical behavior was reproduced or the new guard rejected it. It does not mean the historical defect has been repaired.
