# Task 1 discrepancy register

**Policy:** preserve, identify, and defer; do not silently normalize, overwrite, backfill, or promote historical claims. These discrepancies were checked at the exact f10 and 1c commits. “Recorded” is not “resolved.” Full machine evidence and path lists are in `provenance/dataset_artifact_verification.json`.

| ID | Status | Verified finding | Task 1 treatment / later impact |
| --- | --- | --- | --- |
| T1-D01 | **Recorded; not an integrity failure** | f10 canonical CSV is CRLF with SHA-256 `ea6dfffb…`; 1c root CSV is LF with SHA-256 `cf384a63…`. Their parsed rows are identical, and CRLF→LF normalization makes the bytes identical. | Keep f10's canonical bytes unchanged. Do not claim the two raw hashes are identical or silently rewrite either historical file. |
| T1-D02 | **Recorded** | 1c `backend/nifty_index.csv` has 4,682 rows and ends 2026-10-16; canonical input has 4,684 rows through 2026-10-22. | Do not use the backend variant as the canonical research input. No file was replaced in Task 1. |
| T1-D03 | **Recorded** | The exact 1c tracked platform tree has only `.gitkeep` and `README.md` under `data/raw/`, only `.gitkeep` under `results/`, and no tracked `runs/` files, despite older documentation describing populated paths. | Treat clean-checkout availability as limited. Historical bytes recoverable by hash from the preserved ZIP are not silently promoted into the active tree. |
| T1-D04 | **Recorded** | 1c's 313-entry `MANIFEST.sha256` matches the older archive, not the newer 1c tree: 110 matches, four mismatches, 199 missing, and 98 tracked-but-unlisted paths (excluding the manifest itself). | The new complete 278-record 1c inventory is the Task 1 tracked-tree authority. Do not “repair” the historical manifest or use it as complete newer-source provenance. |
| T1-D05 | **Recorded** | In the historical Arena ZIP, the main run `run_20261030_081436_12ea5b` lacks checked tables/status/freeze (`signals.csv`, `daily_backtests.csv`, `performance.csv`, `run_status.json`, `holdout_freeze.json`). The preliminary run has those checked files. | Do not describe the main run as complete or its dashboard as usable from a clean 1c checkout. Preserve the archive unchanged. |
| T1-D06 | **Recorded; prospective validation remains blocked** | Freeze source `11094a40…` does not match exact 1c source `643edb36…`; the canonical last observation 2026-10-22 precedes the freeze decision boundary 2026-10-30. | No prospective evaluation or relabeling of retrospective periods. A future freeze/protocol is a separate task. |
| T1-D07 | **Recorded** | All three 1c study manifests declare canonical data hash `ea6dff…`, but none has a top-level content-addressed source-snapshot field. | Exact 1c Git commit plus the new inventory provides source identity now; historical manifests were not amended. Reproduction requirements remain a later gate. |
| T1-D08 | **Recorded; Task 0 chronology retained** | f10's older research log says no E7 protocol was found. Task 0's later audit locates an ambiguous proposed E7 in 1c §10.8. | The later Task 0 decision record governs. This is not proof that a fully preregistered executable E7 exists; clarification remains deferred. |
| T1-D09 | **Recorded; stale historical hash text** | 1c reports call `abe195ac…` the current core-source hash. Exact-tip Git recomputation and direct execution of 1c's `core_source_sha256()` both produce `643edb36962597432f16e0ad553e38715a3d52040491186e6d9930e0ee4f6846`. | Use the exact recomputed value for the verified tip. Do not edit historical reports. The archived freeze remains mismatched under either current-hash claim. |

## External matters that remain unverified

- Yahoo/`^NSEI` vendor accuracy, historical revisions, redistribution rights, and licensing.
- Total-return interpretation, dividends, complete exchange calendar, and execution-price realism.
- Historical Open quality beyond the limited structural checks run here.
- Independent reproduction or methodological correctness of any model, strategy, forecast, or allocation result.

## Task 0 research issues carried forward, not re-audited

The attached Task 0 audit remains the decision record for the 1c target-maturity boundary, cross-dimensional density comparison, global/nonjoint selection, state-occupancy alignment, convergence fallback, control inference, duration semantics, dashboard/artifact mismatch, and E7 ambiguity. Task 1 did not rerun those experiments or adjudicate their numerical impact. No issue above is evidence that a different model or strategy would perform better.

## Task 1 closure rule

None of these discrepancies invalidates the Git fast-forward or content-addressed source preservation. They do block stronger provenance, reproduction, prospective, dashboard, or research claims. Task 2 may consider only explicitly approved selective integration and must carry the relevant discrepancy forward rather than resolving it by silence.
