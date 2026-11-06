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
TASK4_RUN = ROOT / 'research/experiments/task4_v1_0_0_recovery1'
TASK4_ANALYSIS = ROOT / 'research/experiments/task4_v1_0_0_analysis'
TASK4_FAILED_RUN = ROOT / 'research/experiments/task4_v1_0_0/FAILED_RUN.json'
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


def json_lines(path):
    return [json.loads(line) for line in path.read_text().splitlines() if line]


def task4_check():
    """Verify the complete immutable inventories before reading compact display records."""
    try:
        run = json.loads((TASK4_RUN/'run_manifest.json').read_text())
        analysis = json.loads((TASK4_ANALYSIS/'analysis_manifest.json').read_text())
        if run['schema'] != 'task4-discovery-run-v1' or run['status'] != 'completed':
            raise ValueError('Task 4 recovery run is not complete')
        if analysis['schema'] != 'task4-analysis-manifest-v1' or analysis['status'] != 'completed':
            raise ValueError('Task 4 analysis is not complete')
        if run['protocol_version'] != analysis['protocol_version'] or run['protocol_version'] != 'task4-rv-nested-v1.0.0':
            raise ValueError('Task 4 protocol version mismatch')
        if sha(TASK4_RUN/'run_manifest.json') != analysis['source_run_manifest_sha256']:
            raise ValueError('Task 4 analysis does not reference the recovery manifest')
        for folder, manifest in ((TASK4_RUN, run), (TASK4_ANALYSIS, analysis)):
            for relative, expected in manifest['artifacts'].items():
                path = folder/relative
                if not path.is_file() or sha(path) != expected:
                    raise ValueError(f'Task 4 artifact hash mismatch: {relative}')
        coverage = json.loads((TASK4_ANALYSIS/'coverage_verification.json').read_text())
        aggregate = json.loads((TASK4_RUN/'aggregate_results.json').read_text())
        stability = json.loads((TASK4_ANALYSIS/'stability_analysis.json').read_text())
        reproducibility = json.loads((TASK4_ANALYSIS/'reproducibility_comparison.json').read_text())
        if not coverage['verified'] or coverage['actual_attempts'] != coverage['expected_attempts']:
            raise ValueError('Task 4 attempt coverage is incomplete')
        if (run['candidate_attempts'] != coverage['actual_attempts'] or
            run['folds'] != coverage['outer_folds'] or
            aggregate['fold_counts']['total'] != run['folds'] or
            stability['schema'] != 'task4-stability-analysis-v1' or
            reproducibility['schema'] != 'task4-reproducibility-comparison-v1'):
            raise ValueError('Task 4 summary records are inconsistent')
        ranking_groups = {}
        for row in records(TASK4_ANALYSIS/'candidate_rankings.csv'):
            ranking_groups.setdefault(row['fold_id'], []).append(row)
        margins = []
        for fold_id, rows in sorted(ranking_groups.items()):
            ordered = sorted(rows, key=lambda row:row['rank'])
            if len(ordered) < 2 or [ordered[0]['rank'], ordered[1]['rank']] != [1, 2]:
                raise ValueError(f'Task 4 candidate ranks are incomplete: {fold_id}')
            best, runner_up = ordered[:2]
            gap = float(best['mean_inner_raw_log_density_per_observation'] - runner_up['mean_inner_raw_log_density_per_observation'])
            if gap < 0:
                raise ValueError(f'Task 4 candidate ranks have the wrong score order: {fold_id}')
            margins.append({'fold_id':fold_id, 'best_candidate_id':best['candidate_id'],
                            'runner_up_candidate_id':runner_up['candidate_id'],
                            'best_score':best['mean_inner_raw_log_density_per_observation'],
                            'runner_up_score':runner_up['mean_inner_raw_log_density_per_observation'],
                            'score_gap':gap, 'near_tie':gap < 0.005})
        seed_sensitivity = records(TASK4_ANALYSIS/'seed_sensitivity.csv')
        if len(margins) != run['folds'] or len(seed_sensitivity) != run['folds'] * 3:
            raise ValueError('Task 4 ranking or seed-sensitivity coverage is inconsistent')
        selection_diagnostics = {
            'margin_threshold':0.005, 'near_tie_folds':sum(row['near_tie'] for row in margins),
            'fold_count':len(margins), 'margins':margins, 'seed_sensitivity':seed_sensitivity,
            'single_seed_winner_match_count':stability['model_path']['single_seed_winner_match_count'],
            'single_seed_winner_match_denominator':stability['model_path']['single_seed_winner_match_denominator'],
            'folds_where_all_single_seed_winners_agree':stability['model_path']['folds_where_all_single_seed_winners_agree']}
        return {'run':run, 'analysis':analysis, 'coverage':coverage, 'aggregate':aggregate,
                'stability':stability, 'reproducibility':reproducibility,
                'selection_diagnostics':selection_diagnostics}
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise HTTPException(503, f'Task 4 artifacts missing or inconsistent: {exc}') from exc


@app.get('/api/research')
def research():
    analysis, meta = check()
    saved_curves = pd.read_csv(RUN/'equity_curves.csv')
    # Sample saved observations only; never synthesize an initial point or interpolate new values.
    curves = saved_curves.iloc[sorted(set(range(0,len(saved_curves),10)) | {len(saved_curves)-1})]
    curve_sampling = {'stride':10, 'final_observation_included':True,
                      'saved_rows':int(len(saved_curves)), 'displayed_rows':int(len(curves)),
                      'start_date':str(saved_curves['Date'].iloc[0]), 'end_date':str(saved_curves['Date'].iloc[-1]),
                      'initial_capital_assumption':1000, 'value_column_unit':'account equity'}
    grid = records(GRID/'fold_scores.csv') if (GRID/'fold_scores.csv').exists() else None
    return {'experiment_id':'baseline_20261104', 'metadata':meta,
            'analysis':analysis, 'performance':records(RUN/'performance.csv'),
            'bootstrap':records(RUN/'bootstrap.csv'), 'curves':curves.to_dict(orient='records'),
            'curve_sampling':curve_sampling,
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


@app.get('/api/task4/discovery')
def task4_discovery():
    verified = task4_check()
    run, analysis = verified['run'], verified['analysis']
    coverage, aggregate = verified['coverage'], verified['aggregate']
    stability, reproducibility = verified['stability'], verified['reproducibility']
    occupancy = [row for row in records(TASK4_ANALYSIS/'state_occupancy.csv') if row['sample'] == 'outer_test']
    selected = records(TASK4_ANALYSIS/'selected_model_path.csv')
    alignments = {row['current_fold_id']:row for row in json_lines(TASK4_RUN/'state_alignments.jsonl')}
    folds = []
    for row in selected:
        alignment = alignments[row['fold_id']]
        status_counts = {}
        for state in alignment['records']:
            status_counts[state['status']] = status_counts.get(state['status'], 0) + 1
        folds.append({**row, 'reference_fold_id':alignment['reference_fold_id'],
                      'alignment_agreement':alignment['agreement'],
                      'alignment_unmatched_frequency':alignment['unmatched_frequency'],
                      'alignment_status_counts':status_counts,
                      'outer_test_used_for_alignment':alignment['outer_test_used']})
    core = reproducibility['core_artifact_comparisons']
    global_objects = reproducibility['global_fold_object_comparisons']
    try:
        initial_failure = json.loads(TASK4_FAILED_RUN.read_text())
        if (initial_failure['schema'] != 'task4-failed-run-v1' or
            initial_failure['protocol_version'] != run['protocol_version']):
            raise ValueError('Task 4 initial-failure record is inconsistent')
    except (OSError, ValueError, KeyError) as exc:
        raise HTTPException(503, f'Task 4 initial-failure record unavailable or inconsistent: {exc}') from exc
    empty_years = len({row['fold_id'] for row in occupancy if row['hard_count'] == 0})
    years = sorted(int(row['fold_id'].replace('outer_', '')) for row in selected)
    return {
        'experiment_id':TASK4_RUN.name, 'protocol_version':run['protocol_version'],
        'summary':{
            'outer_folds':coverage['outer_folds'], 'outer_year_start':years[0], 'outer_year_end':years[-1],
            'inner_candidate_attempts':coverage['actual_inner_attempts'],
            'selected_outer_refits':coverage['actual_outer_refit_attempts'],
            'total_retained_attempts':coverage['actual_attempts'],
            'selected_state_count_frequency':aggregate['selected_state_count_frequency'],
            'selected_candidate_frequency':aggregate['selected_candidate_frequency'],
            'selected_seed_frequency':aggregate['selected_seed_frequency'],
            'fit_status_counts':coverage['candidate_fit_status_counts'],
            'accepted_attempts':coverage['candidate_fit_status_counts'].get('accepted', 0),
            'converged_attempts':coverage['converged_counts'].get('True', 0),
            'rejected_attempts':coverage['candidate_fit_status_counts'].get('rejected', 0),
            'failed_attempts':coverage['candidate_fit_status_counts'].get('failed', 0),
            'nonconverged_attempts':coverage['actual_attempts'] - coverage['converged_counts'].get('True', 0)},
        'selection_diagnostics':verified['selection_diagnostics'],
        'occupancy':{
            'fold_state_observations':stability['outer_occupancy']['fold_state_rows'],
            'zero_hard_assignments':stability['outer_occupancy']['zero_hard_assignment_fold_state_rows'],
            'years_with_empty_state':empty_years,
            'rare_fold_states':stability['outer_occupancy']['rare_fold_state_rows'],
            'rare_rule':stability['outer_occupancy']['rare_rule'], 'rows':occupancy},
        'stability':{
            'alignment_counts':stability['alignment']['subsequent_state_status_counts'],
            'subsequent_fold_pairs':stability['alignment']['subsequent_fold_pairs'],
            'candidate_changes':stability['model_path']['candidate_changes'],
            'candidate_change_fraction':stability['model_path']['candidate_change_fraction_of_adjacent_pairs'],
            'seed_changes':stability['model_path']['seed_changes'],
            'folds':folds},
        'reproducibility':{
            'core_artifacts_matched':sum(bool(row['byte_identical']) for row in core),
            'core_artifacts_total':len(core),
            'global_fold_objects_matched':sum(bool(row['object_identical']) for row in global_objects),
            'global_fold_objects_total':len(global_objects),
            'all_core_artifacts_byte_identical':reproducibility['all_core_artifacts_byte_identical'],
            'all_global_fold_objects_identical':reproducibility['all_global_fold_objects_identical'],
            'candidate_attempt_comparison_available':reproducibility['candidate_attempt_comparison_available'],
            'candidate_attempt_comparison_note':reproducibility['candidate_attempt_comparison_note'],
            'initial_failure':initial_failure},
        'provenance':{
            'run_source_commit':run['source_commit'], 'analysis_source_commit':analysis['source_commit'],
            'run_manifest_sha256':sha(TASK4_RUN/'run_manifest.json'),
            'analysis_manifest_sha256':sha(TASK4_ANALYSIS/'analysis_manifest.json'),
            'protocol_manifest_sha256':run['artifacts']['protocol_manifest.json'],
            'dataset_sha256':run['dataset_sha256'], 'feature_sha256':run['feature_sha256'],
            'engine_freeze_sha256':run['engine_freeze_sha256']},
        'distributions':aggregate['distributions'],
        'conclusion':('Although K=5 was selected in every outer fold, the resulting states were not consistently occupied '
                      'or reliably aligned across years. The experiment supports a recurring five-component density '
                      'preference under this protocol, but does not establish five stable, identifiable economic market regimes.'),
        'nonclaims':['Task 4 did not test forecasting, allocation, strategy performance or prospective investment usefulness.',
                     'Historical baseline strategy results were not produced by Task 4.',
                     'Local and aligned state IDs are not semantic economic regime labels.']}


ARTIFACTS = {'config':'run_config.yaml', 'fits':'fits.csv', 'signals':'signals.csv',
             'performance':'performance.csv', 'bootstrap':'bootstrap.csv',
             'daily-backtests':'daily_backtests.csv', 'transitions':'train_transition_matrices.csv',
             'data-quality':'data_quality.csv', 'report':'report.md', 'metadata':'metadata.json'}
TASK4_RUN_ARTIFACTS = {'task4-aggregate':'aggregate_results.json', 'task4-alignments':'state_alignments.jsonl',
                       'task4-run-manifest':'run_manifest.json', 'task4-protocol':'protocol_manifest.json'}
TASK4_ANALYSIS_ARTIFACTS = {'task4-coverage':'coverage_verification.json', 'task4-stability':'stability_analysis.json',
                            'task4-occupancy':'state_occupancy.csv', 'task4-model-path':'selected_model_path.csv',
                            'task4-candidate-rankings':'candidate_rankings.csv', 'task4-seed-sensitivity':'seed_sensitivity.csv',
                            'task4-reproducibility':'reproducibility_comparison.json',
                            'task4-analysis-manifest':'analysis_manifest.json'}

@app.get('/api/artifacts/{name}')
def artifact(name: str):
    if name in TASK4_RUN_ARTIFACTS or name in TASK4_ANALYSIS_ARTIFACTS:
        task4_check()
        if name in TASK4_RUN_ARTIFACTS:
            path = TASK4_RUN/TASK4_RUN_ARTIFACTS[name]
        else:
            path = TASK4_ANALYSIS/TASK4_ANALYSIS_ARTIFACTS[name]
        return FileResponse(path, filename=path.name)
    if name == 'task4-results-report':
        task4_check()
        path = ROOT/'docs/TASK4_RESULTS.md'
        if not path.is_file():
            raise HTTPException(404, 'Task 4 results report unavailable')
        return FileResponse(path, filename='TASK4_RESULTS.md')
    if name == 'task4-failed-run':
        task4_check()
        if not TASK4_FAILED_RUN.is_file():
            raise HTTPException(404, 'Task 4 initial-failure record unavailable')
        return FileResponse(TASK4_FAILED_RUN, filename=TASK4_FAILED_RUN.name)
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


# Serve the production dashboard on the same origin as its API. The Vite dev
# server remains available separately for frontend development.
app.mount('/assets', StaticFiles(directory=FRONTEND_DIST / 'assets', check_dir=False), name='frontend-assets')


@app.get('/{path:path}', include_in_schema=False)
def dashboard(path: str):
    # Do not turn missing API endpoints into misleading HTML responses.
    if path not in {'', 'regimes', 'task4', 'strategies', 'validation'}:
        raise HTTPException(404, 'Unknown route')
    index = FRONTEND_DIST / 'index.html'
    if not index.is_file():
        raise HTTPException(503, 'Dashboard build missing: run npm ci and npm run build in frontend')
    return FileResponse(index)
