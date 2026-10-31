from pathlib import Path

import numpy as np
import pandas as pd
from scipy.special import logsumexp
from sklearn.preprocessing import StandardScaler
from hmmlearn.hmm import GaussianHMM

from backend.backtest import Backtester
from backend.features import create_features


DATA_FILE = Path(__file__).resolve().parent / "nifty_index.csv"

STRATEGIES = [
    "buy_hold",
    "momentum",
    "mean_reversion",
    "ma_crossover",
    "rsi_mean_reversion",
    "donchian_breakout",
    "adx_trend",
    "atr_targeting",
]


def generate_positions(df):
    """Generate causal long-only positions for all eight strategies."""

    close = df["Close"]
    high = df["High"]
    low = df["Low"]
    positions = pd.DataFrame(index=df.index, dtype=float)

    # 1. Buy and hold.
    positions["buy_hold"] = 1.0

    # 2. Momentum: invest when the previous day's 20-day return is positive.
    positions["momentum"] = (
        (close / close.shift(20) - 1 > 0)
        .shift(1)
        .fillna(False)
        .astype(float)
    )

    # 3. Mean reversion: enter below -3% over five days,
    # exit after the five-day return becomes positive.
    five_day_return = close.pct_change(5)
    mr_signal = pd.Series(np.nan, index=df.index, dtype=float)
    mr_signal.loc[five_day_return < -0.03] = 1.0
    mr_signal.loc[five_day_return > 0] = 0.0

    positions["mean_reversion"] = (
        mr_signal.ffill()
        .fillna(0.0)
        .shift(1)
        .fillna(0.0)
    )

    # 4. Moving-average crossover.
    ma20 = close.rolling(20, min_periods=20).mean()
    ma50 = close.rolling(50, min_periods=50).mean()
    positions["ma_crossover"] = (
        (ma20 > ma50)
        .shift(1)
        .fillna(False)
        .astype(float)
    )

    # 5. RSI mean reversion.
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(14).mean()
    avg_loss = loss.rolling(14).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100 - 100 / (1 + rs)

    rsi_signal = pd.Series(np.nan, index=df.index, dtype=float)
    rsi_signal.loc[rsi < 30] = 1.0
    rsi_signal.loc[rsi > 50] = 0.0
    positions["rsi_mean_reversion"] = (
        rsi_signal.ffill()
        .fillna(0.0)
        .shift(1)
        .fillna(0.0)
    )

    # 6. Donchian Channel Breakout: enter above the prior 20-day high,
    # exit below the prior 10-day low. The final shift means today's
    # return is never acted on using today's closing signal.
    upper_channel = high.rolling(20, min_periods=20).max().shift(1)
    lower_channel = low.rolling(10, min_periods=10).min().shift(1)
    donchian_raw = pd.Series(0.0, index=df.index)
    invested = 0.0

    for i in range(len(df)):
        upper = upper_channel.iloc[i]
        lower = lower_channel.iloc[i]
        current_close = close.iloc[i]

        if pd.notna(upper) and current_close > upper:
            invested = 1.0
        elif pd.notna(lower) and current_close < lower:
            invested = 0.0

        donchian_raw.iloc[i] = invested

    positions["donchian_breakout"] = (
        donchian_raw.shift(1).fillna(0.0)
    )

    # Shared true-range calculation for ADX and ATR strategies.
    previous_close = close.shift(1)
    true_range = pd.concat(
        [
            high - low,
            (high - previous_close).abs(),
            (low - previous_close).abs(),
        ],
        axis=1,
    ).max(axis=1)

    # 7. ADX + Directional Movement.
    upward_move = high.diff()
    downward_move = -low.diff()

    positive_dm = pd.Series(
        np.where(
            (upward_move > downward_move) & (upward_move > 0),
            upward_move,
            0.0,
        ),
        index=df.index,
    )
    negative_dm = pd.Series(
        np.where(
            (downward_move > upward_move) & (downward_move > 0),
            downward_move,
            0.0,
        ),
        index=df.index,
    )

    atr = true_range.ewm(
        alpha=1 / 14,
        min_periods=14,
        adjust=False,
    ).mean()

    positive_di = (
        100
        * positive_dm.ewm(
            alpha=1 / 14,
            min_periods=14,
            adjust=False,
        ).mean()
        / atr.replace(0, np.nan)
    )
    negative_di = (
        100
        * negative_dm.ewm(
            alpha=1 / 14,
            min_periods=14,
            adjust=False,
        ).mean()
        / atr.replace(0, np.nan)
    )

    di_sum = positive_di + negative_di
    dx = (
        100
        * (positive_di - negative_di).abs()
        / di_sum.replace(0, np.nan)
    )
    adx = dx.ewm(
        alpha=1 / 14,
        min_periods=14,
        adjust=False,
    ).mean()

    adx_raw = (
        (adx >= 25) & (positive_di > negative_di)
    ).astype(float)
    positions["adx_trend"] = (
        adx_raw.shift(1).fillna(0.0)
    )

    # 8. ATR-based volatility targeting. ATR / close is used as a
    # daily range-based volatility proxy; exposure is capped at 100%.
    daily_range_volatility = atr / close
    annualized_range_volatility = (
        daily_range_volatility * np.sqrt(252)
    )
    target_annualized_volatility = 0.15

    atr_raw = (
        target_annualized_volatility
        / annualized_range_volatility.replace(0, np.nan)
    ).clip(lower=0.0, upper=1.0)

    positions["atr_targeting"] = (
        atr_raw.shift(1).fillna(0.0)
    )

    positions = positions[STRATEGIES].astype(float)

    if not np.isfinite(positions.to_numpy()).all():
        raise ValueError("Generated strategy positions contain non-finite values.")

    if ((positions < 0) | (positions > 1)).any().any():
        raise ValueError("Strategy positions must be between 0 and 1.")

    return positions


def forward_filter_probabilities(model, X):
    """Compute causal HMM state probabilities without future observations."""

    means = model.means_
    variances = np.asarray(model.covars_)

    if variances.ndim == 3:
        variances = np.diagonal(variances, axis1=1, axis2=2)

    variances = np.maximum(variances, 1e-9)

    log_start = np.log(np.maximum(model.startprob_, 1e-300))
    log_transition = np.log(np.maximum(model.transmat_, 1e-300))

    def emission_log_prob(observation):
        difference = observation - means
        return -0.5 * np.sum(
            np.log(2 * np.pi * variances)
            + difference**2 / variances,
            axis=1,
        )

    log_alpha = None
    probabilities = []

    for observation in X:
        emission = emission_log_prob(observation)

        if log_alpha is None:
            log_alpha = log_start + emission
        else:
            log_alpha = (
                logsumexp(
                    log_alpha[:, None] + log_transition,
                    axis=0,
                )
                + emission
            )

        log_alpha -= logsumexp(log_alpha)
        probabilities.append(np.exp(log_alpha))

    return np.asarray(probabilities)


def calculate_net_returns(
    daily_returns,
    positions,
    transaction_costs,
    initial_position=0.0,
):
    """Calculate portfolio returns with proportional turnover costs."""

    daily_returns = np.asarray(daily_returns, dtype=float)
    positions = np.asarray(positions, dtype=float)

    if len(daily_returns) != len(positions):
        raise ValueError("Returns and positions must have equal lengths.")

    if not np.isfinite(daily_returns).all() or not np.isfinite(positions).all():
        raise ValueError("Returns and positions must contain finite values.")

    if ((positions < 0) | (positions > 1)).any():
        raise ValueError("Positions must be between 0 and 1.")

    previous_positions = np.concatenate(
        ([float(initial_position)], positions[:-1])
    )
    turnover = np.abs(positions - previous_positions)

    net_returns = (
        (1 + positions * daily_returns)
        * (1 - transaction_costs * turnover)
        - 1
    )

    return net_returns


def select_strategy_by_regime(
    train,
    train_regimes,
    train_positions,
    transaction_costs,
):
    """Learn one strategy per regime using training data only."""

    scores = []
    selection = {}
    returns = train["daily_return"].to_numpy()

    strategy_returns = {}
    for strategy in STRATEGIES:
        strategy_returns[strategy] = calculate_net_returns(
            returns,
            train_positions[strategy].to_numpy(dtype=float),
            transaction_costs,
        )

    for regime in sorted(np.unique(train_regimes)):
        mask = train_regimes == regime
        regime_scores = []
        observations = int(mask.sum())

        for strategy in STRATEGIES:
            score = (
                float(strategy_returns[strategy][mask].mean())
                if observations >= 30
                else np.nan
            )
            row = {
                "regime": int(regime),
                "strategy": strategy,
                "observations": observations,
                "mean_daily_net_return": score,
            }
            scores.append(row)

            if np.isfinite(score):
                regime_scores.append(row)

        if regime_scores:
            best = max(
                regime_scores,
                key=lambda row: row["mean_daily_net_return"],
            )
            selection[int(regime)] = best["strategy"]
        else:
            selection[int(regime)] = "buy_hold"

    return selection, pd.DataFrame(scores)


def run_adaptive_backtest(
    initial_capital=1000,
    transaction_costs=0.001,
    risk_free_rate=0.065,
    training_fraction=0.8,
):
    if not 0.5 <= training_fraction < 1:
        raise ValueError("training_fraction must be >= 0.5 and < 1.")

    if not DATA_FILE.exists():
        raise FileNotFoundError(f"NIFTY CSV not found at: {DATA_FILE}")

    df = pd.read_csv(DATA_FILE)
    df, feature_columns = create_features(df)

    # Generate all strategy signals before splitting so rolling indicators
    # and stateful signals carry their legitimate historical context.
    all_positions = generate_positions(df)

    split = int(len(df) * training_fraction)
    train = df.iloc[:split].copy().reset_index(drop=True)
    test = df.iloc[split:].copy().reset_index(drop=True)
    train_positions = all_positions.iloc[:split].copy().reset_index(drop=True)
    test_positions = all_positions.iloc[split:].copy().reset_index(drop=True)

    if len(train) < 100 or len(test) < 30:
        raise ValueError("Insufficient observations for training or testing.")

    # Fit preprocessing on training data only.
    scaler = StandardScaler()
    X_train = scaler.fit_transform(train[feature_columns])
    X_test = scaler.transform(test[feature_columns])

    if not (np.isfinite(X_train).all() and np.isfinite(X_test).all()):
        raise ValueError("Feature data contains non-finite values.")

    # Preserve the current three-state HMM baseline.
    model = GaussianHMM(
        n_components=3,
        covariance_type="diag",
        n_iter=200,
        random_state=42,
    )
    model.fit(X_train)

    if not model.monitor_.converged:
        raise RuntimeError("HMM did not converge. Inspect the model fit.")

    # Causal filtering: train/test state probabilities use only prefixes.
    train_probabilities = forward_filter_probabilities(model, X_train)
    test_probabilities = forward_filter_probabilities(
        model, np.vstack([X_train, X_test])
    )[len(X_train):]

    train_regimes = np.argmax(train_probabilities, axis=1)
    test_regimes = np.argmax(test_probabilities, axis=1)

    regime_strategy, training_scores = select_strategy_by_regime(
        train,
        train_regimes,
        train_positions,
        transaction_costs,
    )

    # Select the precomputed position of the strategy mapped to each regime.
    adaptive_positions = np.array(
        [
            test_positions.loc[i, regime_strategy[int(regime)]]
            for i, regime in enumerate(test_regimes)
        ],
        dtype=float,
    )

    test["regime"] = test_regimes
    test["regime_confidence"] = test_probabilities.max(axis=1)
    test["selected_strategy"] = [
        regime_strategy[int(regime)] for regime in test_regimes
    ]
    test["adaptive_position"] = adaptive_positions

    # Evaluate all eight baseline strategies on identical test dates.
    metrics = {}
    equity_curves = {}

    for strategy in STRATEGIES:
        tester = Backtester(
            initial_capital=initial_capital,
            transaction_costs=transaction_costs,
            risk_free_rate=risk_free_rate,
        )
        equity_curves[strategy] = tester.run(
            test["daily_return"],
            test_positions[strategy].to_numpy(dtype=float),
        ).to_numpy()
        metrics[strategy] = tester.evaluate()

    # Evaluate the HMM-selected adaptive portfolio.
    adaptive_tester = Backtester(
        initial_capital=initial_capital,
        transaction_costs=transaction_costs,
        risk_free_rate=risk_free_rate,
    )
    equity_curves["hmm_adaptive"] = adaptive_tester.run(
        test["daily_return"],
        adaptive_positions,
    ).to_numpy()
    metrics["hmm_adaptive"] = adaptive_tester.evaluate()

    metrics_df = pd.DataFrame(metrics).T
    metrics_df.index.name = "strategy"

    return {
        "model": model,
        "scaler": scaler,
        "feature_columns": feature_columns,
        "train": train,
        "test": test,
        "train_regimes": train_regimes,
        "train_regime_probabilities": train_probabilities,
        "regime_strategy": regime_strategy,
        "training_scores": training_scores,
        "metrics": metrics_df,
        "equity_curves": equity_curves,
    }


if __name__ == "__main__":
    output = run_adaptive_backtest()

    print("\n" + "=" * 70)
    print("CAUSAL HMM REGIME-BASED ADAPTIVE BACKTEST")
    print("=" * 70)

    print("\nStrategies evaluated:")
    for strategy in STRATEGIES:
        print(f"- {strategy}")

    print("\nStrategy selected for each training regime:")
    for regime, strategy in output["regime_strategy"].items():
        print(f"Regime {regime}: {strategy}")

    print("\nTraining-period strategy scores:")
    print(output["training_scores"].to_string(index=False))

    print("\nOut-of-sample metrics:")
    print(output["metrics"].round(4).to_string())

    print("\nTest regime counts:")
    print(output["test"]["regime"].value_counts().sort_index())

    print("\nSelected strategies on test period:")
    print(output["test"]["selected_strategy"].value_counts())

    print("\nEquity curves returned:", len(output["equity_curves"]))
    print("Adaptive backtest complete.")
