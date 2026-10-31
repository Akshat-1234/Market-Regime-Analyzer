import Panel from "../common/Panel.jsx";
import EquityChart from "./EquityChart.jsx";
import { useBacktest } from "../../context/BacktestContext.jsx";
import { getCurve } from "../../utils/normalise.js";

const STRATEGIES = [
  "buy_hold",
  "momentum",
  "mean_reversion",
  "ma_crossover",
  "rsi_mean_reversion",
  "donchian_breakout",
  "adx_trend",
  "atr_targeting",
  "hmm_adaptive",
];

function normaliseKey(key) {
  const value = String(key ?? "")
    .toLowerCase()
    .replace(/[\s-]+/g, "_");

  if (["adaptive", "hmm", "hmm_adaptive"].includes(value)) {
    return "hmm_adaptive";
  }

  if (["buyandhold", "buy_and_hold", "buy_hold"].includes(value)) {
    return "buy_hold";
  }

  return value;
}

function getPoints(raw) {
  if (Array.isArray(raw)) {
    return getCurve({ equity_curve: raw });
  }

  if (!raw || typeof raw !== "object") {
    return [];
  }

  if (Array.isArray(raw.points)) {
    return getCurve({ equity_curve: raw.points });
  }

  if (Array.isArray(raw.data)) {
    return getCurve({ equity_curve: raw.data });
  }

  if (Array.isArray(raw.values)) {
    return getCurve({ equity_curve: raw.values });
  }

  return getCurve(raw);
}

export default function EquityPanel() {
  const { result, curve, strategyLabel } = useBacktest();

  const isHmmAdaptive =
    normaliseKey(result?.strategy ?? result?.strategy_name) ===
      "hmm_adaptive" ||
    normaliseKey(strategyLabel) === "hmm_adaptive";

  const comparisonCurves = [];

  if (isHmmAdaptive && result) {
    const equityCurves = result.equity_curves;

    const entries = Array.isArray(equityCurves)
      ? equityCurves.map((item) => [
          item.strategy ?? item.name ?? item.key,
          item.points ?? item.data ?? item.equity_curve ?? item.values,
        ])
      : Object.entries(equityCurves ?? {});

    for (const [key, raw] of entries) {
      const strategy = normaliseKey(key);

      if (!STRATEGIES.includes(strategy)) {
        continue;
      }

      const points = getPoints(raw);

      if (points.length > 0) {
        const existingIndex = comparisonCurves.findIndex(
          (item) => item.strategy === strategy
        );

        const item = { strategy, points };

        if (existingIndex >= 0) {
          comparisonCurves[existingIndex] = item;
        } else {
          comparisonCurves.push(item);
        }
      }
    }

    const adaptivePoints = getPoints(
      result.adaptive_equity_curve ??
        result.equity_curves?.hmm_adaptive ??
        result.equity_curves?.adaptive
    );

    if (
      adaptivePoints.length > 0 &&
      !comparisonCurves.some(
        (item) => item.strategy === "hmm_adaptive"
      )
    ) {
      comparisonCurves.push({
        strategy: "hmm_adaptive",
        points: adaptivePoints,
      });
    }

    if (
      curve.length > 0 &&
      !comparisonCurves.some(
        (item) => item.strategy === "hmm_adaptive"
      )
    ) {
      comparisonCurves.push({
        strategy: "hmm_adaptive",
        points: curve,
      });
    }

    comparisonCurves.sort(
      (a, b) =>
        STRATEGIES.indexOf(a.strategy) -
        STRATEGIES.indexOf(b.strategy)
    );
  }

  return (
    <Panel className="chart-panel">
      <div className="chart-heading">
        <div>
          <h2>Equity curve</h2>
          <p>
            {result
              ? `${strategyLabel} · Historical backtest`
              : ""}
          </p>
        </div>
      </div>

      {isHmmAdaptive ? (
        <EquityChart
          points={curve}
          curves={comparisonCurves}
        />
      ) : (
        <EquityChart points={curve} />
      )}

      {result && curve.length === 0 && (
        <p className="chart-notice">
          The API returned metrics, but no recognised equity-curve array.
          Check the response's chart data field to enable this chart.
        </p>
      )}

      {isHmmAdaptive &&
        comparisonCurves.length > 0 &&
        comparisonCurves.length < STRATEGIES.length && (
          <p className="chart-notice">
            The API returned {comparisonCurves.length} of {STRATEGIES.length} strategy curves.
            The backend must return the remaining equity curves for the full
            comparison.
          </p>
        )}
    </Panel>
  );
}