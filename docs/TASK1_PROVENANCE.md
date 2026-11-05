# Task 1 provenance record

**Scope:** integration workspace establishment only. This document records source identity, preservation, inventories, and historical-data/artifact checks. It does not validate a model, strategy, forecast, dashboard, or prospective claim.

## 1. Handoff and immutable references

The supplied Task 0 combined audit was read from `/tmp/arena-coding-uploads/Phase-0-Integration-Audit.md` and preserved byte-for-byte at `historical/task0/Phase-0-Integration-Audit.md`.

- Handoff SHA-256: `cb6a1314d2b33868705ac81b7d577c2306ca5fcbaf5f27daaaeba270dce5b00b`
- Bytes: 121,570
- Integrity command: `cd historical/task0 && sha256sum -c SHA256SUMS`
- Result: `Phase-0-Integration-Audit.md: OK`; `cmp` against the attachment also succeeded.

The current checkout initially contained no tracked Task 0 report. The f10 research records were therefore read directly from exact f10 Git blobs as older source history, while the supplied Task 0 audit remains the binding integration decision record.

| Identity | Ref | Exact commit | Exact tree |
| --- | --- | --- | --- |
| f10 source | `refs/heads/arena/f10f6e2d-market-regime-analyzer` | `9bb7f92d5785462462971d0479595c1d4166868c` | `86d56f5564f51ca5e0cbd7554e6d9018baf168ff` |
| 1c source | `refs/heads/arena/1c6dd054-market-regime-analyzer` | `c46541e9ab8611330489a920c46cdb00342931d5` | `7150991d675831f9659138b664a2f7bd813833fe` |
| Shared merge base | not a branch pointer | `f1602c5c95c14e4bd7795433ca6ecfd3d98794d6` | `dca29c590d19e7a20ba446a05c21cf34f21d6bef` |
| Fixed branch initial HEAD | `refs/heads/arena/6b4913f3-market-regime-analyzer` | `31902b7cdec9409f805784d9634d3bfd5f25c03f` | `711fba357bf6be52bc0072c1ac5c5978f78cd54b` |

`git ls-remote` and the GitHub refs API independently returned the exact f10 and 1c commits before any object fetch. No local source branch was created or moved. The full before/after values are machine-recorded in `provenance/source_branches.json`.

## 2. Independent ancestry verification

Exact source objects and sufficient history were fetched without a destination refspec:

```bash
git fetch --no-tags --deepen=100 origin \
  9bb7f92d5785462462971d0479595c1d4166868c \
  c46541e9ab8611330489a920c46cdb00342931d5
```

Only `FETCH_HEAD` was updated by that command. Verification produced:

```text
git merge-base --all <f10> <1c>
f1602c5c95c14e4bd7795433ca6ecfd3d98794d6

GitHub compare <f10>...<1c>
merge_base=f1602c5c95c14e4bd7795433ca6ecfd3d98794d6
status=diverged  ahead_by=2  behind_by=12

f10 is ancestor of 1c: no
1c is ancestor of f10: no
```

The merge-base commit is an ancestor of both tips. Local `git ls-tree` found 107 f10 blobs and 278 1c blobs, matching Task 0. The compare counts and the nine-commit workspace fast-forward count use different endpoints and are not contradictory.

## 3. Authorized fixed-branch fallback

The preferred `integration/market-regime-platform` branch was **not created**, because this Arena session is fixed to `arena/6b4913f3-market-regime-analyzer`. The authorized fallback was used only after Council Checkpoint A verified:

1. the fixed branch is distinct from f10 and 1c;
2. its worktree was clean;
3. its HEAD `31902b7cdec9409f805784d9634d3bfd5f25c03f` was an ancestor of exact f10;
4. `git rev-list --left-right --count 31902b7…...9bb7f92…` returned `0 9`, so no fixed-branch-only commit would be lost; and
5. both source pointers had been independently verified and could be checked again afterward.

The only workspace-establishment command was:

```bash
git merge --ff-only 9bb7f92d5785462462971d0479595c1d4166868c
```

It fast-forwarded nine commits. Immediately afterward, the fixed branch HEAD was exactly `9bb7f92d5785462462971d0479595c1d4166868c`, its tree was exactly `86d56f5564f51ca5e0cbd7554e6d9018baf168ff`, and the worktree was clean. Both remote source refs still resolved to their original commits. No reset, rebase, force-push, branch switch, branch rename, or source-ref update occurred.

The subsequent Task 1 documentation commit is intentionally a descendant of that exact base. “Based on exact f10” means f10 is the integration base and every original f10 blob remains unchanged; it does not mean the final documentation commit has the same SHA as f10.

## 4. Separate content-addressed inventories

The inventories under `provenance/inventory/` were generated from `git ls-tree -rz` and `git cat-file`, not from a checkout or archive file listing.

| Source | Records | Raw source bytes | Inventory file | Inventory SHA-256 |
| --- | ---: | ---: | --- | --- |
| f10 | 107 | 31,703,381 | `f10-9bb7f92-tracked-blobs.jsonl` | `263098e0f78ea4522a8ec0e9ffc6b408848e84fc96ef3b9c0ad9b6c043a2d3da` |
| 1c | 278 | 28,281,675 | `1c-c46541e-tracked-blobs.jsonl` | `0930c823258af150972d06379dc618fb3bcc4e10f81304baa47601bb29de09f1` |

Each record binds a path, Git mode, Git blob ID, raw byte length, and raw-content SHA-256. `index.json` binds the inventories to full commits and trees. Both `sha256sum -c SHA256SUMS` checks passed. An independent reread then verified all 385 paths, Git identities, sizes, and raw hashes against the exact commits.

These are complete tracked-tree inventories. They do not pretend ignored or absent files exist, and they do not retroactively repair historical manifests.

## 5. Dataset provenance and observed quality

The detailed evidence is in `provenance/dataset_artifact_verification.json` (SHA-256 at the evidence cut-off: `e743a65d259ce5727c28d299484e2ab5f25125633a8b658931859c8a1320b01b`). The checks used Python's standard library on exact Git blobs and existing archives.

| Dataset | SHA-256 / relationship | Observed structure | Status |
| --- | --- | --- | --- |
| f10 `research/data/nifty_index.csv` | `ea6dfffb93e5eabd8b6a2f96cd40d6b3ec5c7f47f2f9e6c0cbd3ca9a5f2ac5e4` | 4,684 rows; 2007-09-17 through 2026-10-22; CRLF | **Verified bytes and structure** |
| f10 baseline `inputs/prices.csv` | byte-identical to f10 canonical file and Arena archive raw file | same | **Verified** |
| 1c root `nifty_index.csv` | `cf384a63c9137ec9b7f73d398c7ec5fc55ccdcccf89a514b824ad5341f409e59` | 4,684 rows; LF | **Verified distinct bytes, identical parsed rows** |
| 1c `backend/nifty_index.csv` | `af910f00995930925f7bb30efeaf00e4e7cc8737d3b0d7d36c807f7abcda0416` | 4,682 rows; ends 2026-10-16 | **Verified stale variant; not canonical** |

Normalizing only f10's CRLF line endings to LF produces the 1c root file exactly. All parsed CSV rows, including the header `Date, Close, High, Low, Open`, are equal. Canonical dates are strictly increasing with no duplicates. Standard-library checks observed no empty cells, nonfinite OHLC values, nonpositive Open/Close values, `High < Low`, `High` below Open/Close, or `Low` above Open/Close. These limited structural checks are **not** vendor certification, stale-price analysis, corporate-action validation, exchange-calendar validation, or a total-return confirmation.

Historical documentation attributes the user-supplied series to Yahoo Finance `^NSEI`. Independent vendor accuracy and redistribution/license rights remain **unverified**. No external data was downloaded and no discrepancy was normalized away.

## 6. Historical archive and f10 artifact verification

Thirty explicit provenance assertions ran successfully; zero assertion checks failed. Key results:

- `historical/original-project-31902b7.zip`: SHA-256 `cb9e89db36e9114f47424eb3b64a1165c2958baeaf612c848e5215128c779e01`; 68 members; ZIP CRC passed. Its path set exactly equals both its preservation manifest and the original `31902b7…` Git tree excluding the separate Arena ZIP. Every member matches its declared SHA-256 and its original Git blob byte-for-byte.
- `historical/arena-market-regime-platform.zip`: SHA-256 `bdf7b9136f8fd9b52dc6eedd34fd916c74f8baaaccc8815b3bd170dfc948d4b1`; 1,351 members; ZIP CRC passed. It is byte-identical at f10, 1c, the original `31902b7…` commit, and the integration working tree. It contains the historical raw dataset and older run artifacts, including a bundled environment; presence is not approval to execute that environment.
- All 12 paths in f10's `research/experiments/artifact_manifest.json` match both exact f10 Git blobs and clean working-tree bytes.
- The f10 baseline input snapshot, data manifest, and metadata agree on canonical hash `ea6dff…`, row count, and dates.
- The saved baseline source snapshot and `research/legacy/src/regime_backtester/` are byte-identical over 24 Python files. Recomputing the source hash for either yields the declared `c163aa675d12902f42957722320db88f94e6038679b36c3d128a52202c445a3e`.
- Characterization, model-grid, and forecast source/data/signal hashes match their declared provenance. This validates linkage and integrity, not methodological correctness or predictive value.

The focused command `python -m pytest -q tests/test_historical_archive.py` could not start because pytest is not installed. No pytest test was collected or passed. The independent checks above were actually executed and cover the same archive relationships plus Git-blob comparison; the unavailable runner remains explicitly recorded rather than hidden.

## 7. 1c tracked-tree and historical-manifest reconciliation

The 1c `MANIFEST.sha256` is byte-identical to the older Arena archive's manifest. Against the exact newer 1c tracked tree:

- 313 entries are declared;
- 110 are present with matching raw hashes;
- four are present with different hashes (`.github/workflows/tests.yml`, `README.md`, `src/regime_backtester/features.py`, and `tests/test_api.py`);
- 199 are absent from the tracked tree: 1 under `data/`, 36 under `results/`, and 162 under `runs/`; and
- 98 tracked paths other than the manifest itself are not listed, including newer research code and study outputs.

The exact 1c tree has only `data/raw/.gitkeep`, `data/raw/README.md`, and `results/.gitkeep` in those locations, and no tracked `runs/` files. Its three study manifests declare canonical data hash `ea6dff…`; `research_outputs/LATEST` resolves to `study_20261030T111521Z`. Their manifests do not contain a top-level content-addressed source-snapshot field. The exact commit and new inventory preserve the source tree without rewriting those historical manifests.

The archived preliminary run contains the checked table/status/freeze files. The archived main run lacks `signals.csv`, `daily_backtests.csv`, `performance.csv`, `run_status.json`, and `holdout_freeze.json`. These are preserved as historical discrepancies, not treated as complete evidence.

## 8. Prospective status is not established

The archived freeze declares source hash `11094a4003ab033719771e6e9cbd2da4370b28de74b14d8010d9806935e1c69f` and a decision boundary strictly after 2026-10-30. The canonical data ends 2026-10-22. No qualifying post-freeze observation exists in that dataset, and no prospective evaluation was run.

Independent Git-blob recomputation and direct execution of the exact 1c `core_source_sha256()` both produce `643edb36962597432f16e0ad553e38715a3d52040491186e6d9930e0ee4f6846` over 29 Python files. This differs from the freeze and from the `abe195ac…` value called “current” in older 1c reports. The stale report hash is logged as a discrepancy; the conclusion that the freeze does not match the exact 1c source remains unchanged.

No predictive, profitable, causal, or prospective claim is authorized by any integrity check in this document.
