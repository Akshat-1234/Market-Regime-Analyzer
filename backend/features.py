
import numpy as np
import pandas as pd


def create_features(df):
    df = df.copy()

    required_columns = ["Date", "Open", "High", "Low", "Close"]
    missing_columns = [
        col for col in required_columns if col not in df.columns
    ]

    if missing_columns:
        raise ValueError(
            f"Missing required columns: {missing_columns}"
        )

    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")

    for col in ["Open", "High", "Low", "Close"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df = (
        df.dropna(subset=required_columns)
        .sort_values("Date")
        .drop_duplicates("Date", keep="last")
        .reset_index(drop=True)
    )

    if (df["Close"] <= 0).any():
        raise ValueError("Closing prices must be positive.")

    if (df["Open"] <= 0).any():
        raise ValueError("Opening prices must be positive.")

    if (df["High"] <= 0).any() or (df["Low"] <= 0).any():
        raise ValueError("High and Low prices must be positive.")

    close = df["Close"]
    daily_return = close.pct_change()

    # 1. Daily return (retained for backtesting)
    df["daily_return"] = daily_return

    # 2-4. Multi-period returns
    df["return_5"] = close.pct_change(5)
    df["return_20"] = close.pct_change(20)
    df["return_60"] = close.pct_change(60)

    # 5-7. Rolling volatility
    df["volatility_5"] = daily_return.rolling(5).std()
    df["volatility_20"] = daily_return.rolling(20).std()
    df["volatility_60"] = daily_return.rolling(60).std()

    # 8. Day-over-day absolute change in 20-day volatility
    df["volatility_change"] = df["volatility_20"].diff()

    # 9-11. Moving average distance
    for period in [20, 50, 200]:
        moving_average = close.rolling(period).mean()
        df[f"ma_distance_{period}"] = (
            close / moving_average - 1
        )

    # 12. High-low range percentage
    df["high_low_range"] = (
        df["High"] - df["Low"]
    ) / close

    # 13. Close-to-open return
    df["close_open_return"] = (
        close - df["Open"]
    ) / df["Open"]

    # Features supplied to the HMM
    features = [
        "return_5",
        "return_20",
        "return_60",
        "volatility_5",
        "volatility_20",
        "volatility_60",
        "volatility_change",
        "ma_distance_20",
        "ma_distance_50",
        "ma_distance_200",
        "high_low_range",
        "close_open_return",
    ]

    df = df.replace([np.inf, -np.inf], np.nan)
    df = df.dropna(
        subset=["daily_return"] + features
    ).reset_index(drop=True)

    return df, features
