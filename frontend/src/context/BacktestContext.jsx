import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";

import { DEFAULT_FORM, DEFAULT_STRATEGIES } from "../config.js";

import {
  getDataInfo,
  getHealth,
  getStrategies,
  runBacktest as runBacktestRequest,
} from "../api/client.js";

import { getCurve, normaliseStrategies } from "../utils/normalise.js";

const BacktestContext = createContext(null);

export function BacktestProvider({ children }) {
  const [strategies, setStrategies] = useState(DEFAULT_STRATEGIES);
  const [form, setForm] = useState(DEFAULT_FORM);
  const [dataInfo, setDataInfo] = useState(null);
  const [apiStatus, setApiStatus] = useState("connecting");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState(null);
  const [ranWith, setRanWith] = useState(null);

  const updateField = useCallback((name, value) => {
    setForm((prev) => ({ ...prev, [name]: value }));
  }, []);

  const connect = useCallback(async () => {
    setApiStatus("connecting");

    try {
      const [health, strategyRes, dataRes] = await Promise.all([
        getHealth(),
        getStrategies().catch(() => null),
        getDataInfo().catch(() => null),
      ]);

      void health;

      const available = normaliseStrategies(strategyRes);
      setStrategies(available);

      setForm((prev) =>
        available.some((s) => s.value === prev.strategy)
          ? prev
          : { ...prev, strategy: available[0]?.value ?? "buy_hold" }
      );

      setDataInfo(dataRes);
      setApiStatus("connected");
    } catch {
      setApiStatus("offline");
    }
  }, []);

  useEffect(() => {
    connect();
  }, [connect]);

  const runBacktest = useCallback(async () => {
    setLoading(true);
    setError("");
    setResult(null);

    try {
      const isAdaptive = form.strategy === "hmm_adaptive";

      const payload = {
        initial_capital: Number(form.capital),
        transaction_costs: Number(form.costs),
        risk_free_rate: Number(form.riskFreeRate),
      };

      if (isAdaptive) {
        payload.training_fraction = 0.8;
      } else {
        payload.strategy = form.strategy;
        payload.lookback = Number(form.lookback);
      }

      const data = await runBacktestRequest(form.strategy, payload);
      console.log("BACKTEST RESPONSE:", data);
      console.log("TOP-LEVEL KEYS:", Object.keys(data ?? {}));
      console.log("CHART DATA:", data?.chart);
      console.log("EQUITY CURVE:", data?.equity_curve);
      console.log("PORTFOLIO VALUES:", data?.portfolio_values);
      console.log("METRICS:", data?.metrics);

      setResult(data);
      setRanWith({ ...form });
    } catch (err) {
      setError(err.message || "Could not run the backtest.");
    } finally {
      setLoading(false);
    }
  }, [form]);

  const curve = useMemo(() => getCurve(result), [result]);

  const strategyLabel =
    strategies.find((s) => s.value === form.strategy)?.label ?? form.strategy;

  const value = {
    strategies,
    form,
    updateField,
    dataInfo,
    apiStatus,
    loading,
    error,
    result,
    ranWith,
    curve,
    strategyLabel,
    runBacktest,
    reconnect: connect,
  };

  return (
    <BacktestContext.Provider value={value}>
      {children}
    </BacktestContext.Provider>
  );
}

export function useBacktest() {
  const ctx = useContext(BacktestContext);

  if (!ctx) {
    throw new Error("useBacktest must be used inside BacktestProvider");
  }

  return ctx;
}