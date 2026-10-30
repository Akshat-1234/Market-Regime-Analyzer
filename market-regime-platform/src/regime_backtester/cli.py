"""Command-line entry points. Run `python run.py --help` for the main command."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from .config import load_config
from .data import download_yahoo, load_price_csv, sha256_bytes, synthetic_prices
from .pipeline import run_pipeline
from .reporting import write_results


def make_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="regime-bt", description="Walk-forward HMM regime research (not trading advice).")
    subs = parser.add_subparsers(dest="command", required=True)
    run = subs.add_parser("run", help="Run a walk-forward backtest")
    inputs = run.add_mutually_exclusive_group()
    inputs.add_argument("--csv", help="Input CSV with Date and Close")
    inputs.add_argument("--synthetic", action="store_true", help="Use reproducible FAKE prices (not NIFTY)")
    run.add_argument("--config", help="YAML override, e.g. config/pca_example.yaml")
    run.add_argument("--output", help="New empty output directory; default creates a unique runs/ directory")
    run.add_argument("--source-url", help="Optional URL to record as data provenance (no download)")
    run.add_argument("--start", help="First permitted OOS signal date, YYYY-MM-DD")
    run.add_argument("--end", help="Last included input date, YYYY-MM-DD (inclusive)")
    run.add_argument("--execution-delay", type=int, help="Extra sessions after decision close before execution")
    run.add_argument("--cost-bps", type=float, help="One-way transaction cost in basis points")
    run.add_argument("--risk-free", type=float, help="Annualized cash/risk-free rate, decimal e.g. 0.065")
    run.add_argument("--bootstrap-samples", type=int, help="Number of paired block bootstrap samples")
    run.add_argument("--quiet", action="store_true", help="Suppress refit progress")
    dl = subs.add_parser("download", help="Download daily Yahoo prices (end date exclusive)")
    dl.add_argument("--ticker", default="^NSEI")
    dl.add_argument("--start", default="2007-01-01")
    dl.add_argument("--end", help="Exclusive end date; omit for latest available")
    dl.add_argument("--output", default="data/raw/nifty_index.csv")
    sample = subs.add_parser("sample", help="Write an explicitly marked synthetic sample CSV")
    sample.add_argument("--output", default="data/sample/synthetic_ohlc.csv")
    sample.add_argument("--rows", type=int, default=2200)
    sample.add_argument("--seed", type=int, default=314159)
    return parser


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    # Preserve the convenient previous-style invocation: python run.py --csv ...
    if not argv or argv[0].startswith("-"):
        argv.insert(0, "run")
    args = make_parser().parse_args(argv)
    try:
        if args.command == "download":
            path = download_yahoo(args.ticker, args.start, args.end, args.output)
            print(f"Saved {args.ticker} daily prices: {path}")
            return 0
        if args.command == "sample":
            sample = synthetic_prices(args.rows, args.seed)
            sample["Data_Source"] = "SYNTHETIC"
            path = Path(args.output).expanduser()
            path.parent.mkdir(parents=True, exist_ok=True)
            sample.to_csv(path, index_label="Date")
            print(f"Saved FAKE sample data: {path}")
            return 0
        overrides: dict = {}
        if args.csv:
            overrides.setdefault("data", {})["csv"] = args.csv
        if args.output:
            overrides.setdefault("output", {})["directory"] = args.output
        if args.start:
            overrides.setdefault("walkforward", {})["start_date"] = args.start
        if args.end:
            overrides.setdefault("walkforward", {})["end_date"] = args.end
        if args.execution_delay is not None:
            overrides.setdefault("backtest", {})["execution_delay_sessions"] = args.execution_delay
        if args.cost_bps is not None:
            overrides.setdefault("backtest", {})["transaction_cost_bps"] = args.cost_bps
        if args.risk_free is not None:
            overrides.setdefault("backtest", {})["annual_risk_free_rate"] = args.risk_free
        if args.bootstrap_samples is not None:
            overrides.setdefault("bootstrap", {})["samples"] = args.bootstrap_samples
        default_file = Path("config/default.yaml")
        config_path = args.config or (str(default_file) if default_file.is_file() else None)
        config = load_config(config_path, overrides)
        # Never overwrite existing research. The tracked research command adds
        # richer artifacts; legacy runs still get a unique folder by default.
        if args.output is None and config["output"]["directory"] == "results/run":
            from .experiment_tracking import create_run
            config["output"]["directory"] = str(create_run(Path("runs")))
        else:
            output_path = Path(config["output"]["directory"]).expanduser()
            if output_path.exists() and any(output_path.iterdir()):
                raise ValueError(f"Output directory is not empty: {output_path}; choose a new directory")
        if args.synthetic:
            prices = synthetic_prices()
            source = {"kind": "synthetic", "path": "generated in memory (seed=314159, n=2200)",
                      "sha256": sha256_bytes(prices.to_csv(index_label="Date").encode("utf-8"))}
            print("SYNTHETIC DATA — not NIFTY; results are only a software demonstration.")
        else:
            prices, source = load_price_csv(config["data"]["csv"], config["data"]["date_column"], config["data"]["price_column"])
            if source["kind"] == "synthetic":
                print("SYNTHETIC DATA — sample CSV is not a market series.")
        if args.source_url:
            source["url"] = args.source_url
        if config["backtest"]["execution_delay_sessions"] == 0:
            print("Timing warning: signals use the closing price and assume a same-close fill; test --execution-delay 1 too.")
        result = run_pipeline(prices, config, source, None if args.quiet else print)
        target = write_results(result, config["output"]["directory"])
        from .experiment_tracking import snapshot_inputs_and_source
        snapshot_inputs_and_source(target, None if args.synthetic else config["data"]["csv"])
        if args.synthetic:
            synthetic_snapshot = prices.copy(); synthetic_snapshot["Data_Source"] = "SYNTHETIC"
            synthetic_snapshot.to_csv(target / "inputs" / "prices.csv", index_label="Date")
        (target / "config.yaml").write_text(__import__("yaml").safe_dump(config,sort_keys=False),encoding="utf-8")
        (target / "data_manifest.json").write_text(json.dumps({"input":source,"input_snapshot":"inputs/prices.csv"},indent=2)+"\n",encoding="utf-8")
        (target / "run_status.json").write_text(json.dumps({"run_id":target.name,"status":"completed","kind":"legacy_pipeline", "data_sha256":source.get("sha256"),"source_code_sha256":result.metadata["core_source_sha256"]},indent=2)+"\n",encoding="utf-8")
        print("\nPerformance (CAGR, annual Sharpe, max drawdown):")
        print(result.performance[["cagr", "sharpe", "max_drawdown"]].round(4).to_string())
        print(f"\nSaved report and tables to: {target}")
        return 0
    except (FileNotFoundError, ValueError, RuntimeError, OSError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("Interrupted; no completed report was written.", file=sys.stderr)
        return 130
