"""Local artifact-backed research dashboard API.

The API never invents observations. Raw, immutable run outputs are cached by
file modification time, while filtered statistics are recomputed from daily
returns. Writes are limited to launching the fixed research CLI locally.
"""
from __future__ import annotations

from datetime import date, datetime, timezone
from functools import lru_cache
import json
import math
import os
from pathlib import Path
import re
import subprocess
import sys
import threading
import uuid

import numpy as np
import pandas as pd
import yaml
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field, field_validator

from regime_backtester.research_metrics import evaluate_window
from regime_backtester.experiment_tracking import config_sha256

ROOT = Path(__file__).resolve().parents[1]
RUNS_DIR = Path(os.environ.get("REGIME_RUNS_DIR", ROOT / "runs")).resolve()
DATA_PATH = (ROOT / "data/raw/nifty_index.csv").resolve()
app = FastAPI(title="PROFNITT Quant Club Research API", version="1.0.0")

# Only explicitly enumerated artifacts can be downloaded. No arbitrary paths.
EXPORTS = {
    "performance", "daily_returns", "equity_curves", "daily_backtests", "signals",
    "attribution", "attribution_bootstrap", "attribution_simulations", "attribution_periods", "attribution_control_daily_means",
    "fold_metrics", "fold_aggregate", "stress_periods", "holdout_retrospective", "cash_sensitivity",
    "regime_summary", "regime_strategy_sharpe", "empirical_transitions", "fits", "model_diagnostics",
    "model_occupancy", "train_state_calibration", "train_transition_matrices", "state_stability",
    "state_cross_model_matching", "state_allocation_diagnostics", "data_quality", "data_quality_annual",
    "data_quality_flags", "data_quality_weekday_candidates", "pca_variance", "pca_loadings",
    "feature_correlations", "feature_distributions", "rbi_aligned_rates",
}
REPORTS = {"overall", "hmm_attribution", "walk_forward", "stress_periods", "data_quality",
           "model_diagnostics", "strategy_comparison", "holdout"}


def _run_path(run_id: str, *, completed: bool = True) -> Path:
    if not re.fullmatch(r"run_[A-Za-z0-9_-]+", run_id):
        raise HTTPException(404, "Run not found")
    path = (RUNS_DIR / run_id).resolve()
    if path.parent != RUNS_DIR or not path.is_dir():
        raise HTTPException(404, "Run not found")
    status_path = path / "run_status.json"
    if not status_path.is_file():
        raise HTTPException(404, "Run metadata not found")
    if completed and _json(status_path).get("status") != "completed":
        raise HTTPException(409, "Run is not completed yet; inspect run status")
    return path


@lru_cache(maxsize=256)
def _cached_csv(path: str, modified_ns: int, size: int) -> pd.DataFrame:
    try:
        return pd.read_csv(path)
    except pd.errors.EmptyDataError:
        return pd.DataFrame()


def _csv(path: Path) -> pd.DataFrame:
    if not path.is_file():
        raise HTTPException(404, f"Artifact not available: {path.name}")
    stat = path.stat()
    return _cached_csv(str(path), stat.st_mtime_ns, stat.st_size)


@lru_cache(maxsize=128)
def _cached_json(path: str, modified_ns: int, size: int) -> dict:
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def _json(path: Path) -> dict:
    if not path.is_file():
        raise HTTPException(404, f"Artifact not available: {path.name}")
    stat = path.stat()
    return _cached_json(str(path), stat.st_mtime_ns, stat.st_size)


def _config(path: Path) -> dict:
    with (path / "config.yaml").open(encoding="utf-8") as f:
        return yaml.safe_load(f)


def _records(frame: pd.DataFrame) -> list[dict]:
    # Pandas converts NaN, inf and datetime scalars to JSON-compatible values.
    return json.loads(frame.to_json(orient="records", date_format="iso", double_precision=12))


def _clean(obj):
    if isinstance(obj, dict):
        return {str(k): _clean(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_clean(v) for v in obj]
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating, float)):
        return float(obj) if math.isfinite(obj) else None
    if isinstance(obj, (pd.Timestamp, date, datetime)):
        return obj.isoformat()
    return obj


def _validate_range(start: str | None, end: str | None) -> tuple[str | None, str | None]:
    try:
        if start: date.fromisoformat(start)
        if end: date.fromisoformat(end)
    except ValueError:
        raise HTTPException(422, "Dates must use YYYY-MM-DD")
    if start and end and start > end:
        raise HTTPException(422, "Start date must not be after end date")
    return start, end


def _slice(df: pd.DataFrame, column: str, start: str | None, end: str | None) -> pd.DataFrame:
    dates = df[column].astype(str).str[:10]
    mask = pd.Series(True, index=df.index)
    if start: mask &= dates >= start
    if end: mask &= dates <= end
    return df.loc[mask].copy()


def _sample(df: pd.DataFrame, max_points: int) -> pd.DataFrame:
    if len(df) <= max_points:
        return df
    return df.iloc[np.unique(np.linspace(0, len(df)-1, max_points, dtype=int))]


@app.get("/")
def root():
    return {"service":"PROFNITT research API", "health":"/api/health", "docs":"/docs", "mode":"historical only"}


@app.get("/api/health")
def health():
    return {"status": "ok", "mode": "historical artifacts only", "runs_directory_exists": RUNS_DIR.exists()}


@app.get("/api/runs")
def runs():
    result = []
    for p in sorted(RUNS_DIR.glob("run_*"), reverse=True) if RUNS_DIR.exists() else []:
        try:
            status = _json(p / "run_status.json")
            row = dict(status)
            if (p / "metadata.json").is_file():
                meta = _json(p / "metadata.json")
                row.update({k: meta.get(k) for k in ["data_start", "data_end", "first_return_date", "last_return_date", "return_observations"]})
            row["has_research_artifacts"] = (p / "attribution.csv").is_file()
            result.append(_clean(row))
        except (HTTPException, ValueError, OSError, json.JSONDecodeError):
            continue
    return {"runs": result}


@app.get("/api/runs/{run_id}/overview")
def overview(run_id: str):
    path = _run_path(run_id)
    config = _config(path)
    return _clean({
        "status": _json(path/"run_status.json"),
        "metadata": _json(path/"metadata.json"),
        "data_manifest": _json(path/"data_manifest.json"),
        "holdout": _json(path/"holdout_freeze.json"),
        "backtest": config["backtest"],
        "performance": _records(_csv(path/"performance.csv")),
        "regime_summary": _records(_csv(path/"regime_summary.csv")),
        "bootstrap": _records(_csv(path/"attribution_bootstrap.csv")),
        "strategies": _csv(path/"performance.csv")["strategy"].tolist(),
        "models": [x["name"] for x in config["hmm"]["models"]],
    })


@app.get("/api/runs/{run_id}/series")
def series(run_id: str, start: str | None = None, end: str | None = None,
           strategies: str = "Buy & Hold,Trend 50,HMM + Trend", max_points: int = Query(650, ge=20, le=3000)):
    path = _run_path(run_id)
    start, end = _validate_range(start, end)
    names = list(dict.fromkeys([s.strip() for s in strategies.split(",") if s.strip()]))
    available = _csv(path/"performance.csv")["strategy"].tolist()
    if not names or len(names)>len(available) or any(s not in available for s in names):
        raise HTTPException(422, "Unknown or empty strategy selection")
    returns = _slice(_csv(path/"daily_returns.csv"), "Date", start, end)
    if returns.empty:
        raise HTTPException(422, "No returns in selected period")
    chosen = returns[["Date", *names]].copy()
    values = (1 + chosen[names].astype(float)).cumprod()
    # Include wealth 1 before the first slice return in running peaks.
    dd = values.divide(values.cummax().clip(lower=1.0))-1
    equity = pd.concat([chosen[["Date"]].reset_index(drop=True), (values*100).reset_index(drop=True)], axis=1)
    drawdown = pd.concat([chosen[["Date"]].reset_index(drop=True), dd.reset_index(drop=True)], axis=1)
    full = _slice(_csv(path/"daily_backtests.csv"), "Date", start, end)
    backtest = _config(path)["backtest"]
    stats=[]
    for name in names:
        block = full.loc[full.strategy == name]
        if len(block) != len(chosen):
            raise HTTPException(500, "Run artifacts have inconsistent return calendars")
        stats.append({"strategy":name, **evaluate_window(block, backtest["annual_risk_free_rate"], backtest["trading_days_per_year"])})
    return _clean({"start": str(chosen.Date.iloc[0])[:10], "end": str(chosen.Date.iloc[-1])[:10],
                   "observations": len(chosen), "sampled_points": min(len(chosen), max_points),
                   "equity": _records(_sample(equity,max_points)), "drawdown": _records(_sample(drawdown,max_points)),
                   "stats": stats, "basis": "rebased to 100; inherited holdings and original fees, no artificial liquidation"})


@app.get("/api/runs/{run_id}/regime")
def regime(run_id: str, model: str | None = None, start: str | None = None, end: str | None = None,
           max_points: int = Query(700, ge=20, le=3000)):
    path = _run_path(run_id)
    start, end = _validate_range(start,end)
    config = _config(path)
    models = [x["name"] for x in config["hmm"]["models"]]
    model = model or config["hmm"]["primary_model"]
    if model not in models:
        raise HTTPException(422, "Unknown model")
    signals = _slice(_csv(path/"signals.csv"),"decision_date",start,end)
    if signals.empty: raise HTTPException(422, "No signals in selected period")
    state_col=f"model_regime__{model}"
    prob_cols=[c for c in signals if c.startswith(f"model_probability__{model}__")]
    exp_col=f"model_exposure_{model}"
    if state_col not in signals or not prob_cols or exp_col not in signals:
        raise HTTPException(404, "Model probability artifacts are unavailable in this run")
    selected=signals[["decision_date",state_col,exp_col,*prob_cols]].copy()
    selected=selected.rename(columns={"decision_date":"Date",state_col:"state",exp_col:"exposure",
                                      **{c:f"p{c.rsplit('__',1)[-1]}" for c in prob_cols}})
    raw = _csv(path/"inputs/prices.csv")
    date_col = config["data"]["date_column"]; price_col = config["data"]["price_column"]
    if date_col in raw and price_col in raw:
        raw = raw[[date_col,price_col]].rename(columns={date_col:"Date", price_col:"close"})
        raw["Date"] = raw.Date.astype(str).str[:10]
        selected["Date"] = selected.Date.astype(str).str[:10]
        selected=selected.merge(raw,on="Date",how="left",validate="many_to_one")
    counts=selected.state.value_counts().sort_index()
    occupancy=[{"state":int(i),"days":int(n),"occupancy":float(n/len(selected))} for i,n in counts.items()]
    return _clean({"model":model,"states":len(prob_cols),"observations":len(selected),"models":models,
                   "occupancy":occupancy,"points":_records(_sample(selected,max_points)),
                   "note":"Decision-date filtered probabilities. State numbers are within-model training-volatility ranks; identities may change at refits."})


@app.get("/api/runs/{run_id}/attribution")
def attribution(run_id: str):
    path = _run_path(run_id)
    return _clean({"status":_json(path/"run_status.json"),
                   "summary":_records(_csv(path/"attribution.csv")),
                   "bootstrap":_records(_csv(path/"attribution_bootstrap.csv")),
                   "simulations":_records(_csv(path/"attribution_simulations.csv")),
                   "periods":_records(_csv(path/"attribution_periods.csv")),
                   "note":"Full run sample only. Simulation quantiles and descriptive ranks are not p-values or market-performance confidence intervals."})


@app.get("/api/runs/{run_id}/validation")
def validation(run_id: str):
    p = _run_path(run_id)
    return _clean({"folds":_records(_csv(p/"fold_metrics.csv")), "aggregate":_records(_csv(p/"fold_aggregate.csv")),
                   "stress":_records(_csv(p/"stress_periods.csv")), "retrospective":_records(_csv(p/"holdout_retrospective.csv")),
                   "freeze":_json(p/"holdout_freeze.json"), "cash":_records(_csv(p/"cash_sensitivity.csv")),
                   "fits":_records(_csv(p/"fits.csv")), "occupancy":_records(_csv(p/"model_occupancy.csv")),
                   "model_diagnostics":_records(_csv(p/"model_diagnostics.csv")),
                   "state_stability":_records(_csv(p/"state_stability.csv")),
                   "transitions":_records(_csv(p/"empirical_transitions.csv"))})


@app.get("/api/runs/{run_id}/quality")
def quality(run_id: str):
    p = _run_path(run_id)
    return _clean({"summary":_json(p/"data_quality_summary.json"), "annual":_records(_csv(p/"data_quality_annual.csv")),
                   "flags":_records(_csv(p/"data_quality_flags.csv")), "pca":_records(_csv(p/"pca_variance.csv")),
                   "loadings":_records(_csv(p/"pca_loadings.csv")), "features":_records(_csv(p/"feature_distributions.csv")),
                   "models":_records(_csv(p/"model_diagnostics.csv")), "manifest":_json(p/"data_manifest.json")})


@app.get("/api/runs/{run_id}/export/{artifact}")
def export_artifact(run_id: str, artifact: str):
    if artifact not in EXPORTS: raise HTTPException(404,"Unknown export")
    path = _run_path(run_id) / f"{artifact}.csv"
    if not path.is_file(): raise HTTPException(404,"Artifact not available")
    return FileResponse(path,media_type="text/csv",filename=f"{run_id}_{artifact}.csv")


@app.get("/api/runs/{run_id}/report/{report}")
def report(run_id: str, report: str):
    if report not in REPORTS: raise HTTPException(404,"Unknown report")
    path = _run_path(run_id) / "reports" / f"{report}.md"
    if not path.is_file(): raise HTTPException(404,"Report not available")
    return FileResponse(path,media_type="text/markdown",filename=f"{run_id}_{report}.md")


@app.get("/api/compare-runs")
def compare_runs(run_ids: str):
    ids = list(dict.fromkeys(s.strip() for s in run_ids.split(",") if s.strip()))
    if len(ids) < 2 or len(ids) > 5:
        raise HTTPException(422,"Select 2 to 5 distinct completed research runs")
    entries=[]
    for rid in ids:
        p=_run_path(rid)
        status=_json(p/"run_status.json"); meta=_json(p/"metadata.json"); cfg=_config(p)
        performance=_csv(p/"performance.csv").set_index("strategy")
        attrib=_csv(p/"attribution.csv").set_index("control")
        try:
            real=performance.loc["HMM + Trend"]; trend=performance.loc[f"Trend {cfg['backtest']['trend_window']}"]
            matched=attrib.loc["Trend + Exposure/turnover-matched random"]
        except KeyError:
            raise HTTPException(404,"Run does not contain comparable attribution artifacts")
        entries.append({"run_id":rid,"data_sha256":status.get("data_sha256"),"source_sha256":status.get("source_code_sha256"),
                        "config_sha256":config_sha256(cfg),"first_return_date":meta.get("first_return_date"),
                        "last_return_date":meta.get("last_return_date"),"execution_delay":cfg["backtest"]["execution_delay_sessions"],
                        "cost_bps":cfg["backtest"]["transaction_cost_bps"],"cash_rate":cfg["backtest"]["annual_risk_free_rate"],
                        "control_history_sessions":status.get("control_history_sessions"),
                        "simulation_count":status.get("simulation_count_per_control"),
                        "real_sharpe":real.sharpe,"trend_sharpe":trend.sharpe,"real_cagr":real.cagr,
                        "real_max_drawdown":real.max_drawdown,"matched_median_sharpe":matched.sharpe,
                        "matched_median_ks":matched.median_hmm_exposure_ks})
    def differs(key): return len({str(e[key]) for e in entries})>1
    warnings=[]
    for key,message in [("data_sha256","Input data hashes differ."),("config_sha256","Frozen strategy configurations differ."),
                        ("first_return_date","Return start dates differ."),("last_return_date","Return end dates differ."),
                        ("source_sha256","Core source code hashes differ; use each run's snapshot to reproduce it."),
                        ("control_history_sessions","Control lookbacks differ, so the random-control distributions are different sensitivity experiments."),
                        ("simulation_count","Simulation counts differ.")]:
        if differs(key): warnings.append(message)
    return _clean({"runs":entries,"strictly_comparable":not warnings,"warnings":warnings,
                   "note":"Matching dates, data, configuration and code are necessary for a direct comparison; matching statistics alone do not establish equivalence."})


class ResearchRequest(BaseModel):
    start: date = date(2012,1,1)
    execution_delay: int = Field(1, ge=0, le=1)
    simulations: int = Field(200, ge=2, le=1000)
    bootstrap_samples: int = Field(1000, ge=2, le=5000)
    seed: int = Field(1701, ge=0, le=2**32-1)
    block_length: int = Field(20, ge=1, le=252)
    control_history: int = Field(63, ge=0, le=5000)

    @field_validator("control_history")
    @classmethod
    def valid_history(cls, value):
        if value == 1: raise ValueError("Use 0 for all history or at least 2 sessions")
        return value


_job_lock = threading.Lock()
_job: dict | None = None


@app.get("/api/job")
def job_status():
    with _job_lock:
        if not _job: return {"status":"idle"}
        code = _job["process"].poll()
        return {"job_id":_job["id"], "created_utc":_job["created_utc"],
                "status":"running" if code is None else ("completed" if code == 0 else "failed"),
                "exit_code":code, "request":_job["request"]}


@app.post("/api/job", status_code=202)
def start_job(req: ResearchRequest):
    global _job
    with _job_lock:
        if _job and _job["process"].poll() is None:
            raise HTTPException(409,"A research run is already running")
        if not DATA_PATH.is_file(): raise HTTPException(503,"Configured dataset is missing")
        # Fixed module and dataset, argument list only: no shell or user-controlled paths.
        args=[sys.executable,"-m","regime_backtester.research_run","--csv",str(DATA_PATH),"--runs-dir",str(RUNS_DIR),
              "--start",req.start.isoformat(),"--execution-delay",str(req.execution_delay),"--simulations",str(req.simulations),
              "--bootstrap-samples",str(req.bootstrap_samples),"--seed",str(req.seed),"--block-length",str(req.block_length),
              "--control-history",str(req.control_history)]
        try:
            proc=subprocess.Popen(args,cwd=str(ROOT),stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        except OSError as exc:
            raise HTTPException(503,f"Could not launch research process: {exc}")
        _job={"id":uuid.uuid4().hex[:12],"process":proc,"created_utc":datetime.now(timezone.utc).isoformat(),
              "request":req.model_dump(mode="json")}
        return {"job_id":_job["id"],"status":"running","message":"A new uniquely named run is being computed. Check Runs for status and logs."}
