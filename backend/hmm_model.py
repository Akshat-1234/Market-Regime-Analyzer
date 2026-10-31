
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler
from hmmlearn.hmm import GaussianHMM

from backend.features import create_features


DATA_FILE = Path(__file__).resolve().parent / "nifty_index.csv"


def causal_regime_predictions(model, X_train, X_test):
    """
    Infer each test-day regime using observations available
    only up to that day.

    The model is fitted on training data only.
    """

    history = X_train.copy()
    predictions = []
    probabilities = []

    for observation in X_test:
        history = np.vstack([history, observation])

        posterior = model.predict_proba(history)[-1]

        probabilities.append(posterior)
        predictions.append(int(np.argmax(posterior)))

    return np.array(predictions), np.array(probabilities)


def train_hmm():
    # 1. Load data
    if not DATA_FILE.exists():
        raise FileNotFoundError(
            f"NIFTY CSV not found at: {DATA_FILE}"
        )

    df = pd.read_csv(DATA_FILE)

    # 2. Generate features
    df, feature_columns = create_features(df)

    if len(df) < 100:
        raise ValueError(
            "Not enough observations to train the HMM."
        )

    # 3. Chronological split: first 80% for training
    split = int(len(df) * 0.8)

    train = df.iloc[:split].copy().reset_index(drop=True)
    test = df.iloc[split:].copy().reset_index(drop=True)

    if train.empty or test.empty:
        raise ValueError(
            "Training and test datasets must both contain data."
        )

    # 4. Standardize features using training data only
    scaler = StandardScaler()

    X_train = scaler.fit_transform(
        train[feature_columns]
    )

    X_test = scaler.transform(
        test[feature_columns]
    )

    if not (
        np.isfinite(X_train).all()
        and np.isfinite(X_test).all()
    ):
        raise ValueError(
            "Feature data contains non-finite values."
        )

    # 5. Fit the three-state Gaussian HMM
    model = GaussianHMM(
        n_components=3,
        covariance_type="diag",
        n_iter=200,
        random_state=42,
    )

    model.fit(X_train)

    if not model.monitor_.converged:
        print(
            "\nWARNING: HMM did not converge. "
            "Interpret the results cautiously."
        )

    # 6. Descriptive training state assignments
    train["regime"] = model.predict(X_train)

    # 7. Causal test-period state predictions
    test_states, test_probabilities = (
        causal_regime_predictions(
            model,
            X_train,
            X_test,
        )
    )

    test["regime"] = test_states
    test["regime_confidence"] = (
        test_probabilities.max(axis=1)
    )

    # 8. Training regime summary
    regime_summary = (
        train.groupby("regime")
        .agg(
            mean_daily_return=("daily_return", "mean"),
            mean_volatility=("volatility_20", "mean"),
            mean_trend=("return_20", "mean"),
            observations=("Close", "size"),
        )
        .round(6)
    )

    return model, scaler, train, test, regime_summary


if __name__ == "__main__":
    model, scaler, train, test, summary = train_hmm()

    print("\n" + "=" * 55)
    print("NIFTY 50 - HMM MARKET REGIME ANALYSIS")
    print("=" * 55)

    print("\nHMM INPUT FEATURES:")
    for feature in scaler.feature_names_in_:
        print("-", feature)

    print("\nModel configuration:")
    print("Model: GaussianHMM")
    print("Hidden states:", model.n_components)
    print("Covariance type:", model.covariance_type)
    print("Training converged:", model.monitor_.converged)

    print("\nTRAINING REGIME SUMMARY")
    print(summary)

    print("\nTraining observations:", len(train))
    print("Test observations:", len(test))

    print("\nTEST REGIME COUNTS")
    print(
        test["regime"]
        .value_counts()
        .sort_index()
    )

    print("\nTEST REGIME CONFIDENCE")
    print(
        test.groupby("regime")["regime_confidence"]
        .agg(["mean", "median", "count"])
        .round(4)
    )

    print("\nFIRST 20 TEST OBSERVATIONS")
    columns_to_show = [
        "Date",
        "daily_return",
        "return_20",
        "volatility_20",
        "ma_distance_200",
        "regime",
        "regime_confidence",
    ]

    print(
        test[columns_to_show]
        .head(20)
        .to_string(index=False)
    )

    print("\nTRANSITION COUNTS")
    transitions = pd.crosstab(
        test["regime"].shift(1),
        test["regime"],
        rownames=["Previous regime"],
        colnames=["Current regime"],
    )

    print(transitions)

    print("\nMODEL ANALYSIS COMPLETE")
