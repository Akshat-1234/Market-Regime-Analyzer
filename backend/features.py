
import numpy as np
import pandas as pd


def create_features(df):
    df = df.copy()

    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    df["Close"] = pd.to_numeric(df["Close"], errors="coerce")

    df = (
        df.dropna(subset=["Date", "Close"])
        .sort_values("Date")
        .drop_duplicates("Date", keep="last")
        .reset_index(drop=True)
    )

    if (df["Close"] <= 0).any():
        raise ValueError("Closing prices must be positive.")

    close = df["Close"]

    # 1. Daily return
    df["daily_return"] = close.pct_change()

    # 2. Rolling 20-day volatility
    df["volatility_20"] = df["daily_return"].rolling(20).std()

    # 3. 20-day trend strength
    df["trend_strength"] = close / close.shift(20) - 1

    # 4. Sign persistence
    signs = np.sign(df["daily_return"])
    same_sign = signs.eq(signs.shift(1)).astype(float)
    same_sign[signs.isna() | signs.shift(1).isna()] = np.nan

    df["sign_persistence"] = same_sign.rolling(20).mean()

    features = [
        "daily_return",
        "volatility_20",
        "trend_strength",
        "sign_persistence",
    ]

    df = df.replace([np.inf, -np.inf], np.nan)
    df = df.dropna(subset=features).reset_index(drop=True)

    return df, features
