# Task 3 — Risk Register and Unverified Claims

| ID | Risk/limitation | Current mitigation | Residual status |
|---|---|---|---|
| T3-R01 | Refactor changes original numerics | Immutable source fixture and bitwise parity for every supported original comparison | Low for tested valid inputs; not proof for every possible input |
| T3-R02 | Invalid covariance is silently repaired | Public validation rejects negative/nonfinite/non-PD/nonsymmetric inputs; original EM regularization remains explicit | Controlled; event counts must remain visible to callers |
| T3-R03 | Full-covariance EM projection hides instability | `regularization_events` records updates/eigenvalue clips; parity case exposes 14 events | Open modeling risk; no “stable” claim solely from convergence |
| T3-R04 | Student-t full covariance is unsupported | Reject at emission/config/fit layers | Explicit exclusion; do not infer support from Gaussian-full support |
| T3-R05 | Lookahead through smoothing | Separate smoothing API and inference kinds; future-mutation tests | Controlled at engine boundary; future callers must not relabel smoothed output |
| T3-R06 | Nonconverged/failed fit produces OOS | Adapter returns no OOS block/density unless accepted converged | Controlled; original discovery fallback deliberately excluded |
| T3-R07 | Rare/empty states make labels unstable | Empty posterior raises; optional hard training occupancy rejection; occupancy diagnostics retained | Rare states still require later model-selection/stability review |
| T3-R08 | Scaled density compared as raw density | Explicit space, units, and Jacobian-included fields | Caller must not compare incompatible spaces without transformation |
| T3-R09 | Artifact corruption or version drift | Canonical payload hash, strict schema/engine/source/dependency/dimension/type validation | Integrity only; not a digital signature or external trust root |
| T3-R10 | Environment differences change floating-point results | Direct pins, full freeze, exact operation-order parity, independent tolerances | Bitwise parity is environment-specific; use declared tolerances across new environments |
| T3-R11 | Mutable source or missing source objects | Full commit IDs, Task 1 inventory hashes, exact-object fetch | Controlled; clean clones must fetch immutable objects before parity tests |
| T3-R12 | Canonical data quality overclaimed | Raw/parsed hashes and structural OHLC checks; source lineage recorded | Vendor accuracy, corporate actions, total return, calendar completeness, and licensing unverified |
| T3-R13 | One smoke interpreted as model validation | Fixed split/configuration and explicit no-performance scope | No predictive, economic, allocation, or prospective claim |
| T3-R14 | Original discovery defects migrate accidentally | Discovery source preserved only for boundary audit; fallback excluded | No discovery behavior migrated or endorsed |
| T3-R15 | Historical manifests treated as complete | Verbatim study manifest plus new separate migration metadata | Historical manifest limitations remain; no silent repair |
| T3-R16 | Workspace recovery hides lost evidence | All current logs/artifacts regenerated; historical values used only as regression targets | Deleted pre-reset artifacts are not available for independent inspection |
| T3-R17 | Scope or remote closure differs from report | Exact 30-file staged review, normal commit/push, full local/remote hash checks | Open until external closure JSON is written after push |

## Explicitly unverified or out of scope

- Forecast accuracy, regime persistence usefulness, economic significance, allocation benefit, execution quality, and dashboard behavior.
- Task 4 forecasting/allocation/backtesting/E7/prospective validation and any model recommendation.
- Model selection across K, emissions, features, seeds, dates, or covariance families beyond the bounded tests/smoke.
- Unsupported Student-t full covariance and any approximation that would pretend to support it.
- Historical study result reproduction or endorsement.
- Vendor/corporate-action/calendar/total-return/licensing validation of the canonical NIFTY CSV.
- Independent human review or a cryptographic signature on artifacts.

Task 4 must be separately authorized and must preserve training/OOS chronology, filtering/smoothing labels, density spaces, and fail-closed fit states.
