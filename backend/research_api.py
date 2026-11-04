"""Read-only API for the separately preserved reproduction and analysis."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path

import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / 'research/experiments/baseline_20261104'
ANALYSIS = ROOT / 'research/experiments/characterization_20261104/analysis.json'
GRID = ROOT / 'research/experiments/model_grid_20261104'
FORECAST = ROOT / 'research/experiments/forecast_20261104'
MANIFEST = ROOT / 'research/experiments/artifact_manifest.json'
FRONTEND_DIST = ROOT / 'frontend/dist'
app = FastAPI(title='Market regime research artifacts', version='0.1.0')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def records(path):
    df = pd.read_csv(path).astype(object).where(lambda x: pd.notna(x), None)
    return df.to_dict(orient='records')


def check():
    try:
        manifest = json.loads(MANIFEST.read_text())
        for relative, expected in manifest.items():
            if sha(ROOT / 'research/experiments' / relative) != expected:
                raise ValueError(f'Artifact hash mismatch: {relative}')
        a = json.loads(ANALYSIS.read_text())
        meta = json.loads((RUN / 'metadata.json').read_text())
        if (sha(RUN/'inputs/prices.csv') != a['provenance']['data_sha256'] or
            sha(RUN/'signals.csv') != a['provenance']['signals_sha256'] or
            sha(ROOT/'research/analysis/characterize.py') != a['provenance']['analysis_source_sha256'] or
            meta['data_source']['sha256'] != a['provenance']['data_sha256']):
            raise ValueError('Artifact provenance mismatch')
        for folder, script in ((GRID, 'model_grid.py'), (FORECAST, 'forecast.py')):
            if folder.exists():
                config = json.loads((folder/'config.json').read_text())
                if config['data_sha256'] != a['provenance']['data_sha256'] or sha(ROOT/'research/analysis'/script) != config['source_sha256']:
                    raise ValueError(f'Experiment provenance mismatch: {folder.name}')
                if folder == FORECAST and config['signals_sha256'] != a['provenance']['signals_sha256']:
                    raise ValueError('Forecast signals do not match baseline')
        return a, meta
    except (OSError, ValueError, KeyError) as exc:
        raise HTTPException(503, f'Research artifacts missing or inconsistent: {exc}') from exc


@app.get('/api/research')
def research():
    analysis, meta = check()
    curves = pd.read_csv(RUN/'equity_curves.csv')
    # Keep endpoints bounded without constructing fictitious observations.
    curves = curves.iloc[sorted(set(range(0,len(curves),10)) | {len(curves)-1})]
    grid = records(GRID/'fold_scores.csv') if (GRID/'fold_scores.csv').exists() else None
    return {'experiment_id':'baseline_20261104', 'metadata':meta,
            'analysis':analysis, 'performance':records(RUN/'performance.csv'),
            'bootstrap':records(RUN/'bootstrap.csv'), 'curves':curves.to_dict(orient='records'),
            'forecast_metrics': records(FORECAST/'metrics.csv') if (FORECAST/'metrics.csv').exists() else None,
            'forecast_intervals': records(FORECAST/'simultaneous_intervals.csv') if (FORECAST/'simultaneous_intervals.csv').exists() else None,
            'grid':grid, 'grid_config':json.loads((GRID/'config.json').read_text()) if grid is not None else None,
            'limitations':[
                'Retrospective, previously inspected data; no prospective validation.',
                'Local ranks are not stable state identities across annual refits.',
                'Forward outcomes overlap and are descriptive, without adjusted inference.',
                'Fully matched-control study, comprehensive forecasting, strategy selection and E7 remain incomplete.',
                'Index prices exclude dividends, taxes, impact and real-world investability.',
                'OHLC source needs vendor verification, particularly opening prices.' ]}


ARTIFACTS = {'config':'run_config.yaml', 'fits':'fits.csv', 'signals':'signals.csv',
             'performance':'performance.csv', 'bootstrap':'bootstrap.csv',
             'daily-backtests':'daily_backtests.csv', 'transitions':'train_transition_matrices.csv',
             'data-quality':'data_quality.csv', 'report':'report.md', 'metadata':'metadata.json'}

@app.get('/api/artifacts/{name}')
def artifact(name: str):
    check()
    if name == 'characterization':
        return FileResponse(ANALYSIS, filename='analysis.json')
    if name in {'forecast-metrics', 'forecast-intervals', 'forecast-predictions', 'forecast-config'}:
        names = {'forecast-metrics':'metrics.csv', 'forecast-intervals':'simultaneous_intervals.csv', 'forecast-predictions':'predictions.csv', 'forecast-config':'config.json'}
        path = FORECAST / names[name]
        if not path.exists():
            raise HTTPException(404, 'Forecast artifact unavailable')
        return FileResponse(path, filename=path.name)
    if name in {'grid-folds', 'grid-fits', 'grid-config'}:
        names = {'grid-folds': 'fold_scores.csv', 'grid-fits': 'fits.csv', 'grid-config': 'config.json'}
        path = GRID / names[name]
        if not path.exists():
            raise HTTPException(404, 'Grid artifact unavailable')
        return FileResponse(path, filename=path.name)
    if name not in ARTIFACTS:
        raise HTTPException(404, 'Unknown artifact')
    return FileResponse(RUN/ARTIFACTS[name], filename=ARTIFACTS[name])


@app.api_route('/api/download', methods=['GET', 'HEAD'])
def download_project():
    archive = ROOT / 'Market-Regime-Research.zip'
    if not archive.is_file():
        raise HTTPException(404, 'Project archive has not been created')
    return FileResponse(archive, media_type='application/zip', filename=archive.name)


# Serve the production dashboard on the same origin as its API. The Vite dev
# server remains available separately for frontend development.
app.mount('/assets', StaticFiles(directory=FRONTEND_DIST / 'assets', check_dir=False), name='frontend-assets')


@app.get('/{path:path}', include_in_schema=False)
def dashboard(path: str):
    # Do not turn missing API endpoints into misleading HTML responses.
    if path not in {'', 'regimes', 'strategies', 'validation'}:
        raise HTTPException(404, 'Unknown route')
    index = FRONTEND_DIST / 'index.html'
    if not index.is_file():
        raise HTTPException(503, 'Dashboard build missing: run npm ci and npm run build in frontend')
    return FileResponse(index)
