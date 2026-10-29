
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
]

FEATURE_COLUMNS = [
    "daily_return",
    "volatility_20",
    "trend_strength",
    "sign_persistence",
]


def generate_positions(df):
    """Generate causal 0/1 positions on the full dataset."""

    close = df["Close"]
    positions = pd.DataFrame(index=df.index)

    # 1. Buy and hold
    positions["buy_hold"] = 1

    # 2. Momentum: positive 20-day return.
    positions["momentum"] = (
        (close / close.shift(20) - 1 > 0)
        .shift(1)
        .fillna(False)
        .astype(int)
    )

    # 3. Mean reversion: enter below -3% over five days,
    # exit after the five-day return becomes positive.
    five_day_return = close.pct_change(5)

    mr_signal = pd.Series(
        np.nan, index=df.index, dtype=float
    )
    mr_signal.loc[five_day_return < -0.03] = 1
    mr_signal.loc[five_day_return > 0] = 0

    positions["mean_reversion"] = (
        mr_signal.ffill()
        .fillna(0)
        .shift(1)
        .fillna(0)
        .astype(int)
    )

    # 4. Moving-average crossover.
    ma20 = close.rolling(20).mean()
    ma50 = close.rolling(50).mean()

    positions["ma_crossover"] = (
        (ma20 > ma50)
        .shift(1)
        .fillna(False)
        .astype(int)
    )

    # 5. RSI mean reversion.
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.rolling(14).mean()
    avg_loss = loss.rolling(14).mean()

    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100 - 100 / (1 + rs)

    rsi_signal = pd.Series(
        np.nan, index=df.index, dtype=float
    )
    rsi_signal.loc[rsi < 30] = 1
    rsi_signal.loc[rsi > 50] = 0

    positions["rsi_mean_reversion"] = (
        rsi_signal.ffill()
        .fillna(0)
        .shift(1)
        .fillna(0)
        .astype(int)
    )

    return positions[STRATEGIES]


def forward_filter_probabilities(model, X):
    """
    Compute causal HMM state probabilities.

    Each observation is filtered using only the observations
    up to and including that observation. No smoothing or
    future observations are used for state assignments.
    """

    means = model.means_
    variances = np.asarray(model.covars_)

    if variances.ndim == 3:
        variances = np.diagonal(
            variances, axis1=1, axis2=2
        )

    variances = np.maximum(variances, 1e-9)

    log_start = np.log(
        np.maximum(model.startprob_, 1e-300)
    )
    log_transition = np.log(
        np.maximum(model.transmat_, 1e-300)
    )

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
    initial_position=0,
):
    """
    Apply market returns and transaction costs.

    A cost is charged when the position changes, including
    entering or exiting the market.
    """

    daily_returns = np.asarray(daily_returns, dtype=float)
    positions = np.asarray(positions, dtype=int)

    if len(daily_returns) != len(positions):
        raise ValueError(
            "Returns and positions must have equal lengths."
        )

    previous_positions = np.concatenate(
        ([initial_position], positions[:-1])
    )

    turnover = (
        positions != previous_positions
    ).astype(float)

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
    """
    Learn one strategy per regime from training observations.

    Strategy rankings use mean daily net return. The mapping
    is frozen before the test period begins.
    """

    scores = []
    selection = {}

    returns = train["daily_return"].to_numpy()

    # Calculate each strategy's training returns once.
    strategy_returns = {}

    for strategy in STRATEGIES:
        strategy_returns[strategy] = calculate_net_returns(
            returns,
            train_positions[strategy].to_numpy(),
            transaction_costs,
        )

    for regime in sorted(np.unique(train_regimes)):
        mask = train_regimes == regime
        regime_scores = []

        for strategy in STRATEGIES:
            observations = int(mask.sum())

            # Require enough regime observations.
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
        raise ValueError(
            "training_fraction must be >= 0.5 and < 1."
        )

    if not DATA_FILE.exists():
        raise FileNotFoundError(
            f"NIFTY CSV not found at: {DATA_FILE}"
        )

    # Prepare features and preserve chronological order.
    df = pd.read_csv(DATA_FILE)
    df, feature_columns = create_features(df)

    # Generate signals BEFORE splitting, so stateful signals
    # continue naturally across the training/test boundary.
    all_positions = generate_positions(df)

    split = int(len(df) * training_fraction)

    train = df.iloc[:split].copy().reset_index(drop=True)
    test = df.iloc[split:].copy().reset_index(drop=True)

    train_positions = (
        all_positions.iloc[:split].copy().reset_index(drop=True)
    )
    test_positions = (
        all_positions.iloc[split:].copy().reset_index(drop=True)
    )

    if len(train) < 100 or len(test) < 30:
        raise ValueError(
            "Insufficient observations for training or testing."
        )

    # Fit preprocessing using training data only.
    scaler = StandardScaler()

    X_train = scaler.fit_transform(
        train[feature_columns]
    )
    X_test = scaler.transform(
        test[feature_columns]
    )

    # Fit HMM parameters on training data only.
    model = GaussianHMM(
        n_components=3,
        covariance_type="diag",
        n_iter=200,
        random_state=42,
    )

    model.fit(X_train)

    if not model.monitor_.converged:
        raise RuntimeError(
            "HMM did not converge. Inspect the model fit."
        )

    # Filter training and test observations causally.
    # The HMM parameters are fitted on the training period;
    # each filtered state probability uses only the prefix
    # of observations available up to that date.
    train_probabilities = forward_filter_probabilities(
        model, X_train
    )
    test_probabilities = forward_filter_probabilities(
        model, np.vstack([X_train, X_test])
    )[len(X_train):]

    train_regimes = np.argmax(
        train_probabilities, axis=1
    )
    test_regimes = np.argmax(
        test_probabilities, axis=1
    )

    # Learn the regime-to-strategy mapping on training data.
    regime_strategy, training_scores = (
        select_strategy_by_regime(
            train,
            train_regimes,
            train_positions,
            transaction_costs,
        )
    )

    # Freeze the mapping and apply it to the held-out period.
    adaptive_positions = np.array([
        test_positions.loc[i, regime_strategy[int(regime)]]
        for i, regime in enumerate(test_regimes)
    ], dtype=int)

    test["regime"] = test_regimes
    test["regime_confidence"] = test_probabilities.max(axis=1)
    test["selected_strategy"] = [
        regime_strategy[int(regime)]
        for regime in test_regimes
    ]
    test["adaptive_position"] = adaptive_positions

    # Evaluate every strategy on identical test dates.
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
            test_positions[strategy],
        ).to_numpy()

        metrics[strategy] = tester.evaluate()

    adaptive_tester = Backtester(
        initial_capital=initial_capital,
        transaction_costs=transaction_costs,
        risk_free_rate=risk_free_rate,
    )

    equity_curves["hmm_adaptive"] = (
        adaptive_tester.run(
            test["daily_return"],
            adaptive_positions,
        ).to_numpy()
    )

    metrics["hmm_adaptive"] = adaptive_tester.evaluate()

    metrics_df = pd.DataFrame(metrics).T
    metrics_df.index.name = "strategy"

    return {
        "model": model,
        "scaler": scaler,
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

    print("\n" + "=" * 65)
    print("CAUSAL HMM REGIME-BASED ADAPTIVE BACKTEST")
    print("=" * 65)

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

    print("\nAdaptive backtest complete.")
