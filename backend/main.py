
from pathlib import Path
import math

import numpy as np
import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from backtest import Backtester


# --------------------------------------------------
# App setup
# --------------------------------------------------

app = FastAPI(
    title="Quant Backtester API",
    description="Backtest baseline trading strategies on historical Nifty data.",
    version="1.0.0",
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


# --------------------------------------------------
# Request schema
# --------------------------------------------------

class BacktestRequest(BaseModel):
    strategy: str = "buy_hold"
    initial_capital: float = Field(default=10000, gt=0)
    transaction_costs: float = Field(default=0.001, ge=0, lt=1)
    risk_free_rate: float = Field(default=0.065, ge=0, lt=1)
    lookback: int = Field(default=20, ge=2, le=252)


# --------------------------------------------------
# Load historical data
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


# --------------------------------------------------
# Strategy signals
# --------------------------------------------------

def generate_positions(df, strategy, lookback):
    close = df["Close"]

    if strategy == "buy_hold":
        raw_positions = pd.Series(1.0, index=df.index)

    elif strategy == "momentum":
        # Invest when today's close is above the close
        # from 'lookback' trading days ago.
        raw_positions = (
            close > close.shift(lookback)
        ).astype(float)

    elif strategy == "mean_reversion":
        # Invest when price is below its moving average.
        moving_average = close.rolling(
            window=lookback,
            min_periods=lookback,
        ).mean()

        raw_positions = (
            close < moving_average
        ).astype(float)

    else:
        raise ValueError(
            "Unknown strategy. Use buy_hold, momentum, or mean_reversion."
        )

    # Execute using the previous day's signal.
    # This avoids trading on a signal before its closing
    # price was known.
    return raw_positions.shift(1)


# --------------------------------------------------
# API routes
# --------------------------------------------------

@app.get("/")
def home():
    return {
        "message": "Quant Backtester API is running",
        "docs": "/docs",
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


@app.post("/api/backtest")
def run_backtest(request: BacktestRequest):
    allowed_strategies = {
        "buy_hold",
        "momentum",
        "mean_reversion",
    }

    if request.strategy not in allowed_strategies:
        raise HTTPException(
            status_code=400,
            detail=f"Choose one of: {', '.join(sorted(allowed_strategies))}",
        )

    try:
        df = load_data()
        positions = generate_positions(
            df,
            request.strategy,
            request.lookback,
        )

        # Each return is paired with the position decided
        # using information available before that return.
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

        raw_metrics = backtester.evaluate()

        # Convert NumPy values and non-finite values into
        # JSON-safe Python values.
        metrics = {}
        for key, value in raw_metrics.items():
            number = float(value)
            metrics[key] = (
                number if math.isfinite(number) else None
            )

        # Portfolio contains one initial value plus one
        # value for every tested daily return.
        chart_dates = [
            test["Date"].iloc[0].strftime("%Y-%m-%d")
        ] + [
            date.strftime("%Y-%m-%d")
            for date in test["Date"]
        ]

        # Use the same length for the chart's dates and values.
        # The initial point is shown at the first tested date.
        chart = [
            {
                "date": date,
                "value": float(value),
            }
            for date, value in zip(
                chart_dates,
                portfolio.tolist(),
            )
        ]

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
            "equity_curve": chart,
        }

    except (ValueError, FileNotFoundError) as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Backtest failed: {exc}",
        )
