# Test and validation report

## Executed in this workspace, 2026-11-04

- Baseline: ran the archived engine end-to-end on the supplied data, delayed, 1,000 block bootstrap draws, 15 annual folds; headline metrics reproduce to displayed precision, but signals are not byte-identical. Output and package versions are recorded under `research/experiments/baseline_20261104`.
- Archived project tests from an extracted ZIP: **39 passed, 7 skipped**. The skips include missing purported main-run artifacts, comparison run and freeze/simulation artifacts. One Starlette TestClient deprecation warning. These are archival tests, not evidence the missing outputs exist.
- New backend/research tests: `python -m pytest -q tests` — **9 passed**; one Starlette TestClient deprecation warning. Tests cover future mutation/truncation of filter and features, conditional predictive density, next-close execution timing, within-refit transition boundaries, probability weighting, real artifact/API responses, tampered-file rejection, forecast label maturity, and baseline timing/metrics.
- Frontend: clean `npm ci` and `npm run build` passed using Node 22.22.3. Initial `npm ci` reported 4 vulnerabilities; React Router and Vite were upgraded. A subsequent clean `npm ci`, production build and `npm audit` passed with zero reported vulnerabilities at that time. This is not a security audit.
- Integration: FastAPI TestClient loads actual artifacts and checks provenance; Vite proxy `/api/research` returned 200, all four SPA routes returned 200, and grid/forecast artifact routes returned 200. Both servers bind to 0.0.0.0 and frontend uses relative API URLs. This is a smoke/integration check, not browser automation.

## Not yet verified

No Playwright/browser end-to-end run, visual accessibility audit, mobile device test, Windows setup test, production security audit or clean-room installation beyond the new venv and npm ci. Historical archived test counts and ZIP README statements are not substituted for current checks. More temporal-leakage tests, failure-injection, statistical simulation validation and external dataset verification are needed. Research acceptance criteria including corrected E7, forecasting, matched-control tests and prospective validation remain unsatisfied. No release tag is warranted yet.

## Port 8000 preview repair

The built dashboard is now served by the research API on port 8000, with `/api` remaining same-origin. After rebuilding, all four dashboard routes, the JavaScript asset, and `/api/research` returned 200 using a preview-style Host header; unknown API routes returned 404. The updated backend suite passed **11 tests**, including the missing-build response and same-origin dashboard routes. This was an HTTP smoke test, not browser automation.
