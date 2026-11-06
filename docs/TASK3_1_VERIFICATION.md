# Task 3.1 — Verification and Acceptance Gate

## Gate result

**PASS.** Every Task 3.1 acceptance condition passed before Task 4 implementation began.

| Check | Executed result |
|---|---|
| Baseline focused HMM before edits | 79 passed in 2.28s |
| Baseline Task 2 before edits | 72 passed in 1.90s |
| Hardened focused HMM | **94 passed in 2.04s** |
| Task 2 contracts/regressions after edits | **72 passed in 1.71s** |
| Full repository suite after edits | **179 passed, 1 skipped, 1 warning in 4.42s** |
| Original Task 3 parity script | All original cases bitwise equal; independent reference within tolerance |
| New Task 3.1 parity with initialization capture | All original cases bitwise equal; independent reference within tolerance |
| Canonical smoke | Accepted/converged at iteration 11; exact Task 3 likelihoods; causal prefix true |
| Dependency consistency | `pip check`: No broken requirements found |

The full-suite skip is `test_dashboard_build_assets_when_available` because the frontend has not been built. The warning is the pre-existing Starlette/httpx deprecation. Neither is a new HMM failure.

## Commands

```bash
python -m pytest -q tests/hmm
python -m pytest -q tests/contracts tests/regression
python -m pytest -q
python scripts/verify_task3_parity.py \
  --output /home/user/mra-task4-evidence-20261106/task31-original-parity-regression.json
python scripts/verify_task3_1_parity.py \
  --output provenance/task3_1_parity.json
python -m research.hmm.smoke \
  --data research/data/nifty_index.csv --output-dir /tmp/task31-smoke
python -m pip freeze
python -m pip check
```

The interpreter was `/home/user/mra-task4-venv/bin/python`. Logs and JUnit XML are under `/home/user/mra-task4-evidence-20261106`; pytest commands used shell `pipefail` and generated JUnit directly.

## Numerical parity

`provenance/task3_1_parity.json` SHA-256 is `333b821e0d685b1fabfb9850e27f76491f2026108fb2766636d4669b34d1e5f8`.

For Gaussian diagonal, Gaussian full, and Student-t diagonal, the new evidence captures and compares original initialization arrays at the first emission/forward calls, then compares EM parameters/history, emissions, filtering, predictive densities, final continuation state, chunked OOS filtering, log-beta, and smoothing. Every original valid-input comparison is bitwise equal at `rtol=atol=0`.

The independent `hmmlearn` Gaussian-full likelihood difference remains 0.0 and maximum smoothed difference remains `1.354472090042691e-14`, within predeclared tolerances. The historical Task 3 script also passed unchanged; no tolerance was relaxed.

## Canonical smoke regression

- Training scaled log-likelihood: `-1268.0326484796867`.
- OOS scaled-density sum: `-104.6545315416222`.
- Iterations: 11; accepted/converged; no fallback; causal prefix verified.
- All four detailed regularization counters and the legacy aggregate are zero.
- Summary SHA-256: `4fc9d5333d7f96c0b987951228be155544e28cd48feff5cb2c3d5724be674138`.
- V2 model SHA-256: `576be79ad4dedd66258d5a5b58ca75653b4192a17a55481355b284346507ad72`.

This is an integration regression, not research evidence.

## Serialization and diagnostics evidence

The focused suite increased from 79 to 94 tests. New tests include valid-hash semantic attacks, valid initial/fitted Student-t dof differences, strict v1 compatibility, full/diagonal detailed-counter round trips, and independent matrices with and without eigenvalue clipping. Two initial development failures were caused by a Student-t fixture lacking fitted metadata; after correcting the fixture, the complete suite passed. No numerical assertion failed.

## Freeze and preservation

`provenance/task3_1_engine_freeze.json` SHA-256 is `53f61c24e75ddda81e374ce4629cb88cf1fb521a5dc8c1d91d1a68ce95cd0ea9`. It records engine/schema/source identities, all engine-file hashes, parity, and verification results. Task 4 must not modify these engine files.

Canonical CSV remains SHA-256 `ea6dfffb93e5eabd8b6a2f96cd40d6b3ec5c7f47f2f9e6c0cbd3ca9a5f2ac5e4`. Preserved 1c `emhmm.py` remains `181d251fb8b3b78c907c6518a1714898041dbcb048275f82bd5dd308c2d1f6c9`; `discovery.py` remains `c80ff9130f18106f2e354ed2a5c34d34111ad1d78d2682d0bab828518824fe27`. No Task 2 contract, original source, dataset, backend, or frontend file changed.

The Task 3.1 commit identity and remote closure are recorded externally after its separate normal commit/push; they are not embedded self-referentially in this document.
