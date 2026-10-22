
from pathlib import Path

import pandas as pd
import matplotlib.pyplot as plt

from backend.backtest import Backtester


# ==========================================
# 1. LOAD HISTORICAL NIFTY DATA
# ==========================================

PROJECT_DIR = Path(__file__).resolve().parent
CSV_FILE = PROJECT_DIR / "nifty_index.csv"

if not CSV_FILE.exists():
    raise FileNotFoundError(
        f"CSV file not found: {CSV_FILE}\n"
        "Place nifty_index.csv in the project root."
    )

df = pd.read_csv(CSV_FILE, parse_dates=["Date"])

df["Close"] = pd.to_numeric(df["Close"], errors="coerce")

df = df.dropna(subset=["Date", "Close"])
df = df[df["Close"] > 0]
df = df.sort_values("Date")
df = df.drop_duplicates(subset=["Date"], keep="last")
df = df.reset_index(drop=True)

if len(df) < 22:
    raise ValueError("Not enough historical data for these strategies.")

initial_date = df["Date"].iloc[0]


# ==========================================
# 2. CALCULATE MARKET RETURNS AND INDICATORS
# ==========================================

df["Returns"] = df["Close"].pct_change()

# Cumulative return over the previous 20 trading days.
df["MomentumReturn20"] = (
    (1 + df["Returns"])
    .rolling(window=20)
    .apply(lambda x: x.prod(), raw=True)
    - 1
)

# 20-day moving average for Mean Reversion.
df["MA20"] = df["Close"].rolling(window=20).mean()

# Entry condition: price is at least 2% below MA20.
df["BelowLowerBand"] = df["Close"] < (df["MA20"] * 0.98)

# Remove first row because it has no daily return.
df = df.dropna(subset=["Returns"]).reset_index(drop=True)

daily_returns = df["Returns"]


# ==========================================
# 3. STRATEGY A: BUY AND HOLD
# ==========================================

# Always invested.
buy_hold_positions = [1] * len(df)


# ==========================================
# 4. STRATEGY B: 20-DAY MOMENTUM
# ==========================================

# Positive past 20-day cumulative return = invested.
# Otherwise, stay in cash.
# Shift one day to avoid using today's return to
# decide today's position.
momentum_positions = (
    (df["MomentumReturn20"] > 0)
    .shift(1)
    .fillna(False)
    .astype(int)
    .tolist()
)


# ==========================================
# 5. STRATEGY C: MEAN REVERSION
# ==========================================

# Enter when price falls at least 2% below MA20.
# Stay invested until price returns to or exceeds MA20.

mean_reversion_signal = []
in_market = False

for i in range(len(df)):
    close = df.loc[i, "Close"]
    ma20 = df.loc[i, "MA20"]

    if pd.isna(ma20):
        in_market = False

    elif not in_market and close < ma20 * 0.98:
        in_market = True

    elif in_market and close >= ma20:
        in_market = False

    mean_reversion_signal.append(int(in_market))

# Execute using the previous day's completed signal.
mean_reversion_positions = (
    pd.Series(mean_reversion_signal)
    .shift(1)
    .fillna(0)
    .astype(int)
    .tolist()
)


# ==========================================
# 6. RUN THE BACKTESTS
# ==========================================

def run_strategy(name, positions):
    bt = Backtester(
        initial_capital=1000,
        transaction_costs=0.001,
        risk_free_rate=0.065,
        trading_days=252,
    )

    portfolio = bt.run(daily_returns, positions)

    metrics = bt.evaluate()

    print(f"\n========== {name} ==========")

    for metric, value in metrics.items():
        print(f"{metric}: {value:.6f}")

    print(
        f"Days invested: {sum(positions)} / {len(positions)} "
        f"({100 * sum(positions) / len(positions):.2f}%)"
    )

    return portfolio, bt


buy_hold_portfolio, buy_hold_bt = run_strategy(
    "BUY AND HOLD",
    buy_hold_positions,
)

momentum_portfolio, momentum_bt = run_strategy(
    "20-DAY MOMENTUM",
    momentum_positions,
)

mean_reversion_portfolio, mean_reversion_bt = run_strategy(
    "MEAN REVERSION",
    mean_reversion_positions,
)


# ==========================================
# 7. VALIDATE PORTFOLIO LENGTHS
# ==========================================

assert len(buy_hold_portfolio) == len(df) + 1
assert len(momentum_portfolio) == len(df) + 1
assert len(mean_reversion_portfolio) == len(df) + 1

print("\n========== DATA CHECK ==========")
print("Daily return observations:", len(df))
print("First date:", initial_date.date())
print("Last date:", df["Date"].iloc[-1].date())


# ==========================================
# 8. PLOT ALL THREE EQUITY CURVES
# ==========================================

# Include initial capital on the first date.
plot_dates = [initial_date] + df["Date"].tolist()

plt.figure(figsize=(14, 7))

plt.plot(
    plot_dates,
    buy_hold_portfolio.to_numpy(),
    label="Buy and Hold",
)

plt.plot(
    plot_dates,
    momentum_portfolio.to_numpy(),
    label="20-Day Momentum",
)

plt.plot(
    plot_dates,
    mean_reversion_portfolio.to_numpy(),
    label="Mean Reversion (20-Day MA)",
)

plt.title("Nifty Strategy Comparison")
plt.xlabel("Date")
plt.ylabel("Portfolio Value (Starting Capital = 1000)")
plt.legend()
plt.grid(True, alpha=0.3)
plt.tight_layout()
plt.show()


# ==========================================
# 9. PERFORMANCE COMPARISON TABLE
# ==========================================

results = pd.DataFrame({
    "Buy and Hold": buy_hold_bt.evaluate(),
    "Momentum": momentum_bt.evaluate(),
    "Mean Reversion": mean_reversion_bt.evaluate(),
})

print("\n========== PERFORMANCE COMPARISON ==========")
print(results.round(4).to_string())


# ==========================================
# 10. RANK STRATEGIES BY SHARPE RATIO
# ==========================================

print("\n========== SHARPE RANKING ==========")

sharpe_ranking = results.loc["Annualized Sharpe"].sort_values(
    ascending=False
)

print(sharpe_ranking.round(4).to_string())
