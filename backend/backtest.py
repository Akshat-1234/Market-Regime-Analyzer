
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt


class Backtester:
    def __init__(
        self,
        initial_capital=1000,
        transaction_costs=0.001,
        risk_free_rate=0.065,
        trading_days=252,
    ):
        if not np.isfinite(initial_capital) or initial_capital <= 0:
            raise ValueError("Initial capital must be positive.")

        if (
            not np.isfinite(transaction_costs)
            or not 0 <= transaction_costs < 1
        ):
            raise ValueError(
                "Transaction costs must be in [0, 1)."
            )

        if not np.isfinite(risk_free_rate) or risk_free_rate <= -1:
            raise ValueError(
                "Risk-free rate must be finite and greater than -100%."
            )

        if (
            not isinstance(trading_days, (int, np.integer))
            or isinstance(trading_days, bool)
            or trading_days <= 0
        ):
            raise ValueError("Trading days must be a positive integer.")

        self.initial_capital = float(initial_capital)
        self.transaction_costs = float(transaction_costs)
        self.risk_free_rate = float(risk_free_rate)
        self.trading_days = int(trading_days)

        self.portfolio = None
        self.strategy_returns = None
        self.positions = None

    def run(self, daily_returns, positions):
        daily_returns = pd.Series(
            daily_returns, dtype=float
        ).reset_index(drop=True)

        positions = pd.Series(
            positions, dtype=float
        ).reset_index(drop=True)

        if len(daily_returns) != len(positions):
            raise ValueError(
                "Daily returns and positions must have the same length."
            )

        if len(daily_returns) == 0:
            raise ValueError("At least one daily return is required.")

        if daily_returns.isna().any() or positions.isna().any():
            raise ValueError("Inputs must not contain missing values.")

        if not np.isfinite(daily_returns).all():
            raise ValueError("Returns must contain finite values.")

        if not np.isfinite(positions).all():
            raise ValueError("Positions must contain finite values.")

        if not positions.isin([0, 1]).all():
            raise ValueError(
                "Positions must be 0 (cash) or 1 (invested)."
            )

        if (daily_returns < -1).any():
            raise ValueError(
                "Daily returns cannot be below -100%."
            )

        portfolio = [self.initial_capital]
        previous_position = 0

        for market_return, position in zip(
            daily_returns, positions
        ):
            # Apply the position to the day's market return.
            current_value = portfolio[-1] * (
                1 + position * market_return
            )

            # Charge transaction costs on entries and exits.
            if position != previous_position:
                current_value *= (
                    1 - self.transaction_costs
                )

            portfolio.append(current_value)
            previous_position = position

        self.portfolio = pd.Series(
            portfolio, dtype=float
        )

        self.strategy_returns = (
            self.portfolio.pct_change().dropna().reset_index(drop=True)
        )

        self.positions = positions.copy()

        return self.portfolio

    def drawdown(self):
        if self.portfolio is None:
            raise RuntimeError(
                "Run a backtest before calculating drawdown."
            )

        running_peak = self.portfolio.cummax()

        drawdowns = (
            running_peak - self.portfolio
        ) / running_peak

        return drawdowns, float(drawdowns.max())

    def sharpe(self):
        if self.strategy_returns is None:
            raise RuntimeError(
                "Run a backtest before calculating Sharpe."
            )

        daily_rf = (
            (1 + self.risk_free_rate)
            ** (1 / self.trading_days)
            - 1
        )

        excess_returns = self.strategy_returns - daily_rf
        std = excess_returns.std()

        if (
            len(excess_returns) < 2
            or std == 0
            or not np.isfinite(std)
        ):
            return np.nan

        return float(
            np.sqrt(self.trading_days)
            * excess_returns.mean()
            / std
        )

    def evaluate(self):
        if self.portfolio is None:
            raise RuntimeError(
                "Run a backtest before evaluating it."
            )

        n = len(self.strategy_returns)

        initial = float(self.portfolio.iloc[0])
        final = float(self.portfolio.iloc[-1])

        total_return = final / initial - 1
        years = n / self.trading_days

        cagr = (
            (final / initial) ** (1 / years) - 1
            if years > 0 and final > 0
            else np.nan
        )

        volatility = (
            self.strategy_returns.std()
            * np.sqrt(self.trading_days)
            if n >= 2
            else np.nan
        )

        _, max_drawdown = self.drawdown()

        return {
            "Initial Capital": initial,
            "Final Portfolio Value": final,
            "Total Return": float(total_return),
            "CAGR": float(cagr),
            "Annualized Volatility": float(volatility),
            "Annualized Sharpe": self.sharpe(),
            "Maximum Drawdown": max_drawdown,
        }


if __name__ == "__main__":
    backtester = Backtester(
        initial_capital=1000,
        transaction_costs=0.001,
        risk_free_rate=0.065,
    )

    test_returns = [0, 0, 0, 0, 0]
    positions = [0, 0, 1, 1, 0]

    portfolio = backtester.run(
        test_returns,
        positions,
    )

    print(backtester.evaluate())

    portfolio.plot(title="Portfolio Equity Curve")
    plt.show()

    drawdowns, max_drawdown = backtester.drawdown()

    print("Maximum drawdown:", max_drawdown)

    drawdowns.plot(title="Portfolio Drawdown")
    plt.show()
