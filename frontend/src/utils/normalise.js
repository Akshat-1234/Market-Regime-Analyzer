import { DEFAULT_STRATEGIES } from "../config.js";

export function normaliseStrategies(data) {
  const list = Array.isArray(data) ? data : data?.strategies ?? data?.items ?? [];

  if (!Array.isArray(list) || list.length === 0) return DEFAULT_STRATEGIES;

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

export function getCurve(data) {
  const raw =
    data?.equity_curve ??
    data?.portfolio_curve ??
    data?.portfolio_values ??
    data?.portfolio ??
    data?.curve ??
    data?.chart?.equity_curve;

  if (!Array.isArray(raw)) return [];

  return raw
    .map((item, index) => {
      if (typeof item === "number") return { date: String(index), value: item };
      if (Array.isArray(item))
        return { date: String(item[0] ?? index), value: Number(item[1]) };
      return {
        date: item.date ?? item.Date ?? item.timestamp ?? String(index),
        value: Number(
          item.value ?? item.portfolio_value ?? item.equity ?? item.close ?? item.y
        ),
      };
    })
    .filter((point) => Number.isFinite(point.value));
}

export function getMetrics(result) {
  return result?.metrics ?? result?.results ?? {};
}

export function buildMetricCards(metrics, capital) {
  const m = metrics;
  const totalReturn = m["Total Return"] ?? m.total_return;
  return [
    {
      key: "final",
      label: "Final portfolio value",
      raw: m["Final Portfolio Value"] ?? m.final_portfolio_value,
      kind: "money",
      detail: { initial: m["Initial Capital"] ?? m.initial_capital ?? capital },
      featured: true,
    },
    { key: "return", label: "Total return", raw: totalReturn, kind: "percent", detailText: "", signed: true },
    { key: "cagr", label: "CAGR", raw: m.CAGR ?? m.cagr, kind: "percent", detailText: "" },
    {
      key: "sharpe",
      label: "Sharpe ratio",
      raw: m["Annualized Sharpe"] ?? m.annualized_sharpe ?? m.sharpe_ratio,
      kind: "number",
      detailText: "",
    },
    {
      key: "vol",
      label: "Annualized volatility",
      raw: m["Annualized Volatility"] ?? m.annualized_volatility,
      kind: "percent",
      detailText: "",
    },
    {
      key: "dd",
      label: "Maximum drawdown",
      raw: m["Maximum Drawdown"] ?? m.maximum_drawdown,
      kind: "percent",
      detailText: "",
    },
  ];
}
