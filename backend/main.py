
from pathlib import Path
import math

import numpy as np
import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from backend.backtest import Backtester
from backend.adaptive_backtest import run_adaptive_backtest


# --------------------------------------------------
# App setup
# --------------------------------------------------

app = FastAPI(
    title="Quant Backtester API",
    description=(
        "Backtest baseline trading strategies and an "
        "HMM regime-based adaptive strategy on NIFTY data."
    ),
    version="1.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DATA_FILE = Path(__file__).resolve().parent / "nifty_index.csv"

BASELINE_STRATEGIES = {
    "buy_hold",
    "momentum",
    "mean_reversion",
    "ma_crossover",
    "rsi_mean_reversion",
}


# --------------------------------------------------
# Request schema
# --------------------------------------------------

class BacktestRequest(BaseModel):
    strategy: str = "buy_hold"
    initial_capital: float = Field(default=10000, gt=0)
    transaction_costs: float = Field(default=0.001, ge=0, lt=1)
    risk_free_rate: float = Field(default=0.065, ge=0, lt=1)
    lookback: int = Field(default=20, ge=2, le=252)


class AdaptiveBacktestRequest(BaseModel):
    initial_capital: float = Field(default=10000, gt=0)
    transaction_costs: float = Field(default=0.001, ge=0, lt=1)
    risk_free_rate: float = Field(default=0.065, ge=0, lt=1)
    training_fraction: float = Field(default=0.8, ge=0.5, lt=1)


# --------------------------------------------------
# Data helpers
# --------------------------------------------------

def load_data():
    if not DATA_FILE.exists():
        raise FileNotFoundError(
            f"Historical CSV not found at {DATA_FILE}"
        )

    df = pd.read_csv(DATA_FILE)

    required_columns = {"Date", "Close"}
    if not required_columns.issubset(df.columns):
        raise ValueError(
            "CSV must contain Date and Close columns."
        )

    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    df["Close"] = pd.to_numeric(df["Close"], errors="coerce")

    df = (
        df.dropna(subset=["Date", "Close"])
        .sort_values("Date")
        .drop_duplicates(subset=["Date"], keep="last")
        .reset_index(drop=True)
    )

    if len(df) < 3:
        raise ValueError("Not enough valid historical price data.")

    if (df["Close"] <= 0).any():
        raise ValueError("Closing prices must be positive.")

    df["Returns"] = df["Close"].pct_change()

    return df


def json_number(value):
    """Convert numeric values into JSON-safe Python values."""
    number = float(value)
    return number if math.isfinite(number) else None


def serialize_metrics(metrics):
    return {
        str(key): json_number(value)
        for key, value in metrics.items()
    }


def make_equity_curve(dates, portfolio):
    """
    Backtester returns an initial value plus one value per
    tested return. Use the day before the first test return
    for the initial portfolio point.
    """
    dates = pd.to_datetime(pd.Series(dates)).reset_index(drop=True)
    values = list(portfolio)

    if not len(values):
        return []

    first_date = dates.iloc[0]
    initial_date = first_date - pd.Timedelta(days=1)

    chart_dates = [initial_date] + list(dates)

    return [
        {
            "date": pd.Timestamp(date).strftime("%Y-%m-%d"),
            "value": json_number(value),
        }
        for date, value in zip(chart_dates, values)
    ]


# --------------------------------------------------
# Baseline strategy signals
# --------------------------------------------------

def generate_positions(df, strategy, lookback):
    close = df["Close"]

    if strategy == "buy_hold":
        raw_positions = pd.Series(1.0, index=df.index)

    elif strategy == "momentum":
        raw_positions = (
            close > close.shift(lookback)
        ).astype(float)

    elif strategy == "mean_reversion":
        moving_average = close.rolling(
            window=lookback,
            min_periods=lookback,
        ).mean()

        raw_positions = (
            close < moving_average
        ).astype(float)

    elif strategy == "ma_crossover":
        short_ma = close.rolling(
            window=20,
            min_periods=20,
        ).mean()

        long_ma = close.rolling(
            window=50,
            min_periods=50,
        ).mean()

        raw_positions = (
            short_ma > long_ma
        ).astype(float)

    elif strategy == "rsi_mean_reversion":
        delta = close.diff()
        gains = delta.clip(lower=0)
        losses = -delta.clip(upper=0)

        avg_gain = gains.ewm(
            alpha=1 / 14,
            min_periods=14,
            adjust=False,
        ).mean()

        avg_loss = losses.ewm(
            alpha=1 / 14,
            min_periods=14,
            adjust=False,
        ).mean()

        relative_strength = (
            avg_gain / avg_loss.replace(0, np.nan)
        )

        rsi = 100 - (100 / (1 + relative_strength))
        rsi = rsi.mask(
            (avg_loss == 0) & (avg_gain > 0),
            100,
        )

        raw_positions = (
            rsi < 30
        ).astype(float)

    else:
        raise ValueError(f"Unknown strategy: {strategy}")

    # Use yesterday's signal for today's return.
    return raw_positions.shift(1)


# --------------------------------------------------
# API routes
# --------------------------------------------------

@app.get("/")
def home():
    return {
        "message": "Quant Backtester API is running",
        "docs": "/docs",
        "baseline_endpoint": "/api/backtest",
        "adaptive_endpoint": "/api/adaptive-backtest",
    }


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/api/health")
def api_health():
    return {"status": "ok"}


@app.get("/api/strategies")
def list_strategies():
    return {
        "strategies": [
            {
                "id": "buy_hold",
                "name": "Buy and Hold",
                "description": "Stay invested throughout the test period.",
            },
            {
                "id": "momentum",
                "name": "Momentum",
                "description": "Invest when price is above its lookback-period price.",
            },
            {
                "id": "mean_reversion",
                "name": "Mean Reversion",
                "description": "Invest when price is below its moving average.",
            },
            {
                "id": "ma_crossover",
                "name": "Moving Average Crossover",
                "description": "Invest when the 20-day moving average is above the 50-day average.",
            },
            {
                "id": "rsi_mean_reversion",
                "name": "RSI Mean Reversion",
                "description": "Invest when the 14-day RSI falls below 30.",
            },
            {
                "id": "hmm_adaptive",
                "name": "HMM Adaptive",
                "description": "Select a strategy using HMM-inferred market regimes.",
            },
        ]
    }


@app.get("/api/data-info")
def data_info():
    try:
        df = load_data()
    except (ValueError, FileNotFoundError) as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    return {
        "rows": len(df),
        "first_date": df["Date"].iloc[0].strftime("%Y-%m-%d"),
        "last_date": df["Date"].iloc[-1].strftime("%Y-%m-%d"),
    }


# --------------------------------------------------
# Baseline backtest endpoint
# --------------------------------------------------

@app.post("/api/backtest")
def run_backtest(request: BacktestRequest):
    if request.strategy not in BASELINE_STRATEGIES:
        raise HTTPException(
            status_code=400,
            detail=(
                "Choose a baseline strategy from: "
                + ", ".join(sorted(BASELINE_STRATEGIES))
                + ". Use /api/adaptive-backtest for HMM Adaptive."
            ),
        )

    try:
        df = load_data()

        positions = generate_positions(
            df,
            request.strategy,
            request.lookback,
        )

        test = df.copy()
        test["Position"] = positions

        test = test.dropna(
            subset=["Returns", "Position"]
        ).reset_index(drop=True)

        if test.empty:
            raise ValueError("Not enough data for this strategy.")

        backtester = Backtester(
            initial_capital=request.initial_capital,
            transaction_costs=request.transaction_costs,
            risk_free_rate=request.risk_free_rate,
        )

        portfolio = backtester.run(
            test["Returns"],
            test["Position"],
        )

        metrics = serialize_metrics(backtester.evaluate())

        return {
            "strategy": request.strategy,
            "parameters": {
                "initial_capital": request.initial_capital,
                "transaction_costs": request.transaction_costs,
                "risk_free_rate": request.risk_free_rate,
                "lookback": request.lookback,
            },
            "period": {
                "start": test["Date"].iloc[0].strftime("%Y-%m-%d"),
                "end": test["Date"].iloc[-1].strftime("%Y-%m-%d"),
            },
            "trading_days": len(test),
            "metrics": metrics,
            "equity_curve": make_equity_curve(
                test["Date"],
                portfolio,
            ),
        }

    except (ValueError, FileNotFoundError) as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Backtest failed: {exc}",
        )


# --------------------------------------------------
# HMM adaptive backtest endpoint
# --------------------------------------------------

@app.post("/api/adaptive-backtest")
def run_hmm_adaptive_backtest(
    request: AdaptiveBacktestRequest,
):
    try:
        result = run_adaptive_backtest(
            initial_capital=request.initial_capital,
            transaction_costs=request.transaction_costs,
            risk_free_rate=request.risk_free_rate,
            training_fraction=request.training_fraction,
        )

        test = result["test"]
        metrics_df = result["metrics"]

        strategy_metrics = {
            strategy: serialize_metrics(
                metrics_df.loc[strategy].to_dict()
            )
            for strategy in metrics_df.index
        }

        equity_curves = {
            strategy: make_equity_curve(
                test["Date"],
                values,
            )
            for strategy, values in result["equity_curves"].items()
        }

        regime_rows = []
        for regime in sorted(
            int(value)
            for value in test["regime"].unique()
        ):
            regime_data = test[test["regime"] == regime]

            regime_rows.append({
                "regime": regime,
                "observations": int(len(regime_data)),
                "mean_daily_return": json_number(
                    regime_data["daily_return"].mean()
                ),
                "mean_volatility": json_number(
                    regime_data["volatility_20"].mean()
                ),
                "mean_trend": json_number(
                    regime_data["trend_strength"].mean()
                ),
                "mean_confidence": json_number(
                    regime_data["regime_confidence"].mean()
                ),
                "selected_strategy": result[
                    "regime_strategy"
                ].get(regime, "buy_hold"),
            })

        selected_counts = {
            str(key): int(value)
            for key, value in test[
                "selected_strategy"
            ].value_counts().items()
        }

        training_scores = (
            result["training_scores"]
            .replace([np.inf, -np.inf], np.nan)
            .astype(object)
            .where(pd.notna(result["training_scores"]), None)
            .to_dict(orient="records")
        )

        return {
            "strategy": "hmm_adaptive",
            "parameters": {
                "initial_capital": request.initial_capital,
                "transaction_costs": request.transaction_costs,
                "risk_free_rate": request.risk_free_rate,
                "training_fraction": request.training_fraction,
                "hidden_states": 3,
                "features": [
                    "daily_return",
                    "volatility_20",
                    "trend_strength",
                    "sign_persistence",
                ],
            },
            "period": {
                "start": test["Date"].iloc[0].strftime("%Y-%m-%d"),
                "end": test["Date"].iloc[-1].strftime("%Y-%m-%d"),
            },
            "trading_days": int(len(test)),
            "training_observations": int(len(result["train"])),
            "model_converged": bool(
                result["model"].monitor_.converged
            ),
            "regime_strategy_mapping": {
                str(key): value
                for key, value in result["regime_strategy"].items()
            },
            "selected_strategy_counts": selected_counts,
            "regimes": regime_rows,
            "training_scores": training_scores,
            "metrics": strategy_metrics,
            "equity_curves": equity_curves,
            "adaptive_equity_curve": equity_curves.get(
                "hmm_adaptive", []
            ),
            "test_observations": (
                test[
                    [
                        "Date",
                        "daily_return",
                        "regime",
                        "regime_confidence",
                        "selected_strategy",
                        "adaptive_position",
                    ]
                ]
                .assign(
                    Date=lambda frame: frame["Date"].dt.strftime(
                        "%Y-%m-%d"
                    )
                )
                .to_dict(orient="records")
            ),
        }

    except (ValueError, FileNotFoundError) as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Adaptive backtest failed: {exc}",
        )
