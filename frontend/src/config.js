export const API = import.meta.env.VITE_API_URL ?? "http://127.0.0.1:8000";

export const DEFAULT_STRATEGIES = [
  { value: "buy_hold", label: "Buy & Hold" },
  { value: "momentum", label: "Momentum" },
  { value: "mean_reversion", label: "Mean Reversion" },
];

export const DEFAULT_FORM = {
  strategy: "buy_hold",
  capital: "10000",
  costs: "0.001",
  riskFreeRate: "0.065",
  lookback: "20",
};
