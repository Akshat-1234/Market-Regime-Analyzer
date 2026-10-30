# Executed verification report

All results below refer to this workspace on 30 October 2026. Tests are reported as actually run, not inferred from code. Runtime: Python 3.13.16; Node 20.20.2/npm 10.8.2; Linux. The exact test counts may change when users add tests.

## Original preservation and research

- Before platform modifications: original **21 pytest tests passed**. The original delayed baseline was rerun end-to-end with 1,000 bootstrap samples. Every saved performance field matched at CSV precision and the signal CSV was byte-identical. The original supplied CSV hash was verified; all 37 archived result files, three `data/raw/` files and nine aggregate independent-validation files were also compared byte-for-byte with the supplied prior ZIP and matched. See [BASELINE_AUDIT.md](BASELINE_AUDIT.md).
- Two complete new delayed research runs were executed: 200 simulations per control × 3 controls in each run, plus 1,000 paired bootstrap samples per comparison. The first used all prior exposure history; after inspecting its approximate-match diagnostics, the second used a 63-session rolling history. Both are retained, with their distinct source snapshots. The base performance and aggregate fold metrics exactly match the archived baseline.
- Prospective evaluation was not run on fabricated future data: the recorded freeze is pending. A unit test confirms the same original dataset is rejected as an extension without post-freeze dates.
- A real API-launched isolated smoke run was executed using the user dataset, `start=2026-01-01`, two simulations per control, 20 bootstrap samples and 63-session history. It completed with six control paths and its API artifacts were verified. This was a **smoke test**, not a substitute for the 200-simulation findings. Its temporary/isolated workspace is not mixed with the two reference runs.

## Automated tests

| Test | Command | Last result |
| --- | --- | --- |
| Research and FastAPI | `python -m pytest -q` | **46 passed**, one Starlette/httpx deprecation warning |
| React/Vitest | `cd frontend && npm test` | **6 passed** |
| Browser/end-to-end | `cd frontend && npm run test:e2e` | **7 passed** in Chromium |
| TypeScript/Vite production build | `cd frontend && npm run build` | **Passed**; bundle-size advisory (>500 kB before gzip) |
| Launcher prerequisites | `python run_dashboard.py --check` | **Passed** |
| Actual launcher and proxy | `python run_dashboard.py --backend-port 18100 --frontend-port 15173` | Both servers started; frontend, backend health and proxied health returned HTTP 200; shutdown closed both alternate ports |

Python tests cover causal controls across rolling and full history, mutation/truncation, timing, fixed and lagged cash alignment, Sortino, drawdown/recovery, stress boundaries, source/config/freeze validation, real run artifacts, API errors and filter calculations. Browser tests exercise all five sections, strategy and date filters, two-state labels, validation and run comparisons, exports, modal behavior, run switching and mobile layout. A prior Playwright attempt initially failed due to missing Linux Chromium shared libraries; installing the system libraries resolved it. Some initial browser assertions had overly broad selectors and were corrected; the final run above passed.

A separate clean-checkout simulation omitting the Git-ignored raw dataset, runs and results produced **39 passed, 7 skipped**; artifact-dependent checks correctly skip when the private reference files are absent. The actual dashboard and API were also started at ports **5173** and **8000** and checked against live artifacts. The frontend proxies `/api` to the backend; no browser-side cross-host localhost request is used.

The packaged ZIP was independently extracted and its complete SHA-256 file manifest verified. From the extracted copy, the Python suite again passed 46 tests; a fresh `npm ci` followed by Vitest and a production build also passed. The extraction reused the installed Python dependencies.

## Limitations of verification

Windows PowerShell commands are supplied but were **not executed on Windows** in this Linux environment. Browser checks used desktop Chromium and a mobile-sized viewport, not a physical device or a full browser matrix. The performance study is one historical dataset and is not a prospective result. The API is a local unauthenticated research service, not security-hardened public infrastructure. Python package resolution and OS/BLAS differences may affect exact numerical results.
