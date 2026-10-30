.PHONY: install test frontend-test frontend-build e2e dashboard demo clean
install:
	python -m pip install -e '.[dev,dashboard,download]'
	cd frontend && npm ci
test:
	python -m pytest -q
frontend-test:
	cd frontend && npm test
frontend-build:
	cd frontend && npm run build
e2e:
	cd frontend && npm run test:e2e
dashboard:
	python run_dashboard.py
demo:
	python run.py --synthetic
# Only remove regenerable caches/builds. Never delete archived data or research runs.
clean:
	rm -rf frontend/dist frontend/test-results frontend/playwright-report .pytest_cache
