import { DEFAULT_STRATEGIES } from "../config.js";

export function normaliseStrategies(data) {
  const list = Array.isArray(data)
    ? data
    : data?.strategies ?? data?.items ?? [];

  if (!Array.isArray(list) || list.length === 0) {
    return DEFAULT_STRATEGIES;
  }

  return list
    .map((item) => {
      if (typeof item === "string") {
        return {
          value: item,
          label: item
            .replaceAll("_", " ")
            .replace(/\b\w/g, (c) => c.toUpperCase()),
        };
      }

      const value = item.value ?? item.id ?? item.key ?? item.name;

      return {
        value,
        label:
          item.label ??
          item.display_name ??
          item.name ??
          String(value ?? "").replaceAll("_", " "),
      };
    })
    .filter((item) => item.value);
}

// Extract equity-curve data from baseline and HMM responses.
export function getCurve(data) {
  if (!data || typeof data !== "object") {
    return [];
  }

  const candidates = [
    data.adaptive_equity_curve,
    data.equity_curves?.hmm_adaptive,
    data.equity_curves?.adaptive,
    data.equity_curve,
    data.portfolio_curve,
    data.portfolio_values,
    data.portfolio,
    data.curve,
    data.chart?.equity_curve,
    data.chart?.data,
  ];

  const raw = candidates.find(
    (candidate) => Array.isArray(candidate) && candidate.length > 0
  );

  if (!raw) {
    return [];
  }

  return raw
    .map((item, index) => {
      if (typeof item === "number") {
        return {
          date: String(index),
          value: item,
        };
      }

      if (Array.isArray(item)) {
        return {
          date: String(item[0] ?? index),
          value: Number(item[1]),
        };
      }

      if (!item || typeof item !== "object") {
        return null;
      }

      return {
        date: String(
          item.date ??
            item.Date ??
            item.timestamp ??
            item.time ??
            index
        ),
        value: Number(
          item.value ??
            item.portfolio_value ??
            item.portfolioValue ??
            item.equity ??
            item.equity_value ??
            item.close ??
            item.y
        ),
      };
    })
    .filter(
      (point) =>
        point !== null && Number.isFinite(point.value)
    );
}

// Extract the metrics for the selected strategy.
export function getMetrics(result) {
  if (!result || typeof result !== "object") {
    return {};
  }

  const metrics = result.metrics;

  if (!metrics || typeof metrics !== "object") {
    return (
      result.results?.metrics ??
      result.results ??
      result.performance ??
      result.backtest?.metrics ??
      {}
    );
  }

  // Some APIs return metrics grouped by strategy.
  if (
    metrics.hmm_adaptive &&
    typeof metrics.hmm_adaptive === "object"
  ) {
    return metrics.hmm_adaptive;
  }

  if (
    metrics.adaptive &&
    typeof metrics.adaptive === "object"
  ) {
    return metrics.adaptive;
  }

  // The HMM endpoint may return baseline strategy metrics
  // alongside the adaptive strategy metrics.
  if (result.strategy === "hmm_adaptive") {
    const adaptiveMetrics =
      result.adaptive_metrics ??
      result.adaptive_results ??
      result.adaptive_performance;

    if (
      adaptiveMetrics &&
      typeof adaptiveMetrics === "object"
    ) {
      return adaptiveMetrics;
    }
  }

  // Standard baseline or flat metrics response.
  return metrics;
}

export function buildMetricCards(metrics = {}, capital = 0) {
  const m = metrics ?? {};

  const pick = (...values) =>
    values.find(
      (value) =>
        value !== undefined &&
        value !== null &&
        value !== ""
    );

  return [
    {
      key: "final",
      label: "Final portfolio value",
      raw: pick(
        m["Final Portfolio Value"],
        m.final_portfolio_value,
        m.final_value,
        m.final_capital,
        m.final_equity
      ),
      kind: "money",
      detail: {
        initial: pick(
          m["Initial Capital"],
          m.initial_capital,
          capital
        ),
      },
      featured: true,
    },
    {
      key: "return",
      label: "Total return",
      raw: pick(
        m["Total Return"],
        m.total_return,
        m.total_return_pct
      ),
      kind: "percent",
      detailText: "",
      signed: true,
    },
    {
      key: "cagr",
      label: "CAGR",
      raw: pick(
        m.CAGR,
        m.cagr,
        m.cagr_pct
      ),
      kind: "percent",
      detailText: "",
    },
    {
      key: "sharpe",
      label: "Sharpe ratio",
      raw: pick(
        m["Annualized Sharpe"],
        m.annualized_sharpe,
        m.sharpe_ratio,
        m.sharpe
      ),
      kind: "number",
      detailText: "",
    },
    {
      key: "vol",
      label: "Annualized volatility",
      raw: pick(
        m["Annualized Volatility"],
        m.annualized_volatility,
        m.volatility
      ),
      kind: "percent",
      detailText: "",
    },
    {
      key: "dd",
      label: "Maximum drawdown",
      raw: pick(
        m["Maximum Drawdown"],
        m.maximum_drawdown,
        m.max_drawdown
      ),
      kind: "percent",
      detailText: "",
    },
  ];
}