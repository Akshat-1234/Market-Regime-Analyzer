# Task 3 — Deliverable and Verification Manifest

## 1. Scope

Task 3 adds exactly 30 files: ten HMM engine modules, seven focused test files, one parity script, six governance documents, three verbatim 1c source files, two machine-readable Task 3 manifests (migration and parity), and this root report. Existing Task 2 contracts, backend, frontend, datasets, and historical artifacts are unchanged. Canonical input identity is embedded in the migration manifest. The smoke's fitted model and logs are external verification evidence, not large generated Git artifacts.

## 2. File groups

| Group | Paths | Purpose |
|---|---|---|
| Engine | `research/hmm/{__init__,config,parameters,emissions,forward_backward,em,inference,adapter,serialization,smoke}.py` | Numerical engine, contracts, persistence, canonical integration |
| Focused tests | `tests/hmm/conftest.py`, `test_emissions.py`, `test_forward_backward.py`, `test_em.py`, `test_inference.py`, `test_reference_parity.py`, `test_serialization.py` | 79 tests covering formulas, algorithms, causality, EM, failures, parity, references, and persistence |
| Parity tooling | `scripts/verify_task3_parity.py` | Rebuild exact-original and `hmmlearn` evidence |
| Governance | `docs/TASK3_{SPEC,PROVENANCE,MANIFEST,VERIFICATION,COUNCIL,RISKS}.md` | Acceptance, lineage, file map, commands, review, and risks |
| Preserved references | `provenance/source/1c-c46541e/{emhmm,discovery}.py`; `provenance/source/1c-c46541e-manifests/study_manifest.json` | Verbatim tracked 1c blobs |
| Machine manifests | `provenance/task3_migration_manifest.json`, `provenance/task3_parity.json` | Source classification, inline canonical-input identity, module map/hashes, and measured parity |
| Root report | `TASK3_REPORT.md` | Outcome, evidence index, limitations, next-task recommendation |

The 30-file arithmetic is `10 + 7 + 1 + 6 + 3 + 2 + 1`. `git status` and the staged name-status list are authoritative for the exact additive scope.

## 3. External evidence bundle

The regenerated evidence directory is `/home/user/mra-task3-evidence-20261106` (outside Git). It contains:

- `task3-hmm-final.log` / `.xml`: focused suite;
- `task3-task2-final.log` / `.xml`: Task 2 contracts and regressions;
- `task3-full-final.log` / `.xml`: complete repository suite;
- `task3-parity-final.log` and `task3-smoke-final.log`;
- `smoke/summary.json` and `smoke/model.json`;
- `task3-pip-freeze.txt`, `task3-pip-check.log`;
- source/status/scope snapshots and `SHA256SUMS`;
- `task3_closure.json`, written only after the normal commit/push and remote/local checks.

The repository does not embed its own final commit hash self-referentially. External closure evidence records the post-commit/push identity and branch state.

## 4. Reproduction commands

Run from the repository root in the recorded environment. The exact immutable 1c/f10 commits must be available as Git objects; fetching those objects does not change the integration branch.

```bash
python -m pytest -q tests/hmm
python -m pytest -q tests/contracts tests/regression
python -m pytest -q
python scripts/verify_task3_parity.py --output provenance/task3_parity.json
python -m research.hmm.smoke \
  --data research/data/nifty_index.csv \
  --output-dir /tmp/task3-smoke-reproduction
```

Use an empty output directory because parity and smoke artifacts intentionally fail on overwrite. The parity script adds the repository root to `sys.path`; direct module execution handles imports normally. `Date` remains a column until Task 2 `validate_ohlc_frame` performs OHLC validation.

## 5. Current artifact identities

| Artifact | SHA-256 |
|---|---|
| Canonical CSV | `ea6dfffb93e5eabd8b6a2f96cd40d6b3ec5c7f47f2f9e6c0cbd3ca9a5f2ac5e4` |
| Original `emhmm.py` | `181d251fb8b3b78c907c6518a1714898041dbcb048275f82bd5dd308c2d1f6c9` |
| Original `discovery.py` | `c80ff9130f18106f2e354ed2a5c34d34111ad1d78d2682d0bab828518824fe27` |
| Original study manifest | `c59d7e8d9119e4b23ef988b70e55e6b4c4fdd3f3593b2742412b55321844de6b` |
| Migration manifest (includes canonical-input identity) | `45ea24c9eb7dfb49fea21817d4ec6b04c8796190574cdac754b10f1a3daa8535` |
| Parity evidence | `ba9f8112b0b5137b1ec243824c9ce434102b52c72aa7259946c71dce32bbd130` |
| Smoke summary (external copy) | `9aacb029776efe3fd81be200ed26b3e26e67e72b38306243ece980967c0cb7ee` |
| Smoke model (external copy) | `dcf51ecd808ea82d2ae6a07fa20a3fc520d5e9d6b9b55eadb80e67bcb5cd6ba2` |

The two smoke hashes refer to the regenerated external run at `/tmp/task3-smoke-20261106`, preserved under the evidence bundle. Absolute output paths are recorded inside the JSON; numerical results are environment/pin specific.

## 6. Verification result summary

- Focused HMM: **79 passed**.
- Task 2 contracts/regressions: **72 passed**.
- Full suite: **164 passed, 1 skipped, 1 warning**. The skip is the pre-existing optional frontend-built-assets test (`Frontend has not been built`); the warning is the pre-existing Starlette/httpx deprecation.
- Exact original parity: all supported cases bitwise equal; independent `hmmlearn` within tolerance.
- Canonical smoke: accepted/converged, 11 iterations, no fallback, zero regularization events, causal prefix verified.

Detailed commands, outputs, failure taxonomy, and residual risks are in `TASK3_VERIFICATION.md`, `TASK3_COUNCIL.md`, and `TASK3_RISKS.md`.
