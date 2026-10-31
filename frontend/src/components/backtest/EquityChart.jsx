import { useMemo } from "react";
import { formatAxisMoney, formatChartDate, formatMoney } from "../../utils/format.js";

const WIDTH = 900;
const HEIGHT = 300;
const PAD = { top: 20, right: 18, bottom: 38, left: 76 };

const STRATEGY_COLORS = {
  buy_hold: "#60a5fa",
  momentum: "#34d399",
  mean_reversion: "#fbbf24",
  ma_crossover: "#c084fc",
  rsi_mean_reversion: "#fb7185",
  donchian_breakout: "#f97316",
  adx_trend: "#22d3ee",
  atr_targeting: "#a3e635",
  hmm_adaptive: "#ffffff",
};

const STRATEGY_LABELS = {
  buy_hold: "Buy & Hold",
  momentum: "Momentum",
  mean_reversion: "Mean Reversion",
  ma_crossover: "MA Crossover",
  rsi_mean_reversion: "RSI Mean Reversion",
  donchian_breakout: "Donchian Breakout",
  adx_trend: "ADX Trend",
  atr_targeting: "ATR Targeting",
  hmm_adaptive: "HMM Adaptive",
};

export default function EquityChart({ points = [], curves = [] }) {
  const chart = useMemo(() => {
    const multiple = curves.length > 0;

    const sourceCurves = multiple
      ? curves
          .map((curve) => ({
            ...curve,
            strategy: curve.strategy ?? curve.name,
            points: curve.points ?? curve.data ?? [],
          }))
          .filter((curve) => curve.points.length > 0)
      : points.length > 0
        ? [{ strategy: "single", points }]
        : [];

    if (!sourceCurves.length) return null;

    const values = sourceCurves
      .flatMap((curve) =>
        curve.points.map((point) => Number(point.value))
      )
      .filter(Number.isFinite);

    if (!values.length) return null;

    const min = Math.min(...values);
    const max = Math.max(...values);
    const range = max - min || 1;
    const plotWidth = WIDTH - PAD.left - PAD.right;
    const plotHeight = HEIGHT - PAD.top - PAD.bottom;

    const plottedCurves = sourceCurves.map((curve) => {
      const coordinates = curve.points
        .filter((point) => Number.isFinite(Number(point.value)))
        .map((point, index, arr) => ({
          ...point,
          x:
            PAD.left +
            (index / Math.max(arr.length - 1, 1)) * plotWidth,
          y:
            PAD.top +
            ((max - Number(point.value)) / range) * plotHeight,
        }));

      const line = coordinates
        .map(
          (point, index) =>
            `${index === 0 ? "M" : "L"} ${point.x} ${point.y}`
        )
        .join(" ");

      return {
        ...curve,
        coordinates,
        line,
        color: STRATEGY_COLORS[curve.strategy] ?? "#94a3b8",
      };
    }).filter((curve) => curve.coordinates.length > 0);

    if (!plottedCurves.length) return null;

    if (!multiple) {
      const coordinates = plottedCurves[0].coordinates;
      const line = plottedCurves[0].line;
      const area = `${line} L ${coordinates.at(-1).x} ${HEIGHT - PAD.bottom} L ${coordinates[0].x} ${HEIGHT - PAD.bottom} Z`;

      return {
        multiple: false,
        coordinates,
        line,
        area,
        min,
        max,
      };
    }

    return {
      multiple: true,
      curves: plottedCurves,
      min,
      max,
    };
  }, [points, curves]);

  if (!chart) {
    return (
      <div className="chart-empty">
        Run a backtest to see your portfolio equity curve.
      </div>
    );
  }

  const referencePoints = chart.multiple
    ? chart.curves[0].coordinates
    : chart.coordinates;

  const ticks = [
    0,
    Math.floor((referencePoints.length - 1) / 2),
    referencePoints.length - 1,
  ].filter((value, index, arr) => arr.indexOf(value) === index);

  return (
    <div className="chart-wrap">
      <svg
        className="equity-chart"
        viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
        role="img"
        aria-label={
          chart.multiple
            ? `Comparison of ${chart.curves.length} strategy equity curves`
            : "Portfolio equity curve"
        }
      >
        {[0, 1, 2, 3, 4].map((step) => {
          const y =
            PAD.top +
            (step / 4) * (HEIGHT - PAD.top - PAD.bottom);
          const value =
            chart.max - (step / 4) * (chart.max - chart.min);

          return (
            <g key={step}>
              <line
                x1={PAD.left}
                y1={y}
                x2={WIDTH - PAD.right}
                y2={y}
                className="chart-grid"
              />
              <text
                x={PAD.left - 10}
                y={y + 4}
                textAnchor="end"
                className="axis-label"
              >
                {formatAxisMoney(value)}
              </text>
            </g>
          );
        })}

        {chart.multiple ? (
          chart.curves.map((curve) => (
            <path
              key={curve.strategy}
              d={curve.line}
              fill="none"
              stroke={curve.color}
              strokeWidth={curve.strategy === "hmm_adaptive" ? 2.8 : 1.8}
              strokeLinejoin="round"
              strokeLinecap="round"
            >
              <title>
                {STRATEGY_LABELS[curve.strategy] ?? curve.strategy}
              </title>
            </path>
          ))
        ) : (
          <>
            <path d={chart.area} className="chart-area" />
            <path d={chart.line} className="chart-line" />
          </>
        )}

        {ticks.map((index) => {
          const point = referencePoints[index];

          return (
            <text
              key={index}
              x={point.x}
              y={HEIGHT - 12}
              textAnchor={
                index === 0
                  ? "start"
                  : index === referencePoints.length - 1
                    ? "end"
                    : "middle"
              }
              className="axis-label"
            >
              {formatChartDate(point.date)}
            </text>
          );
        })}
      </svg>

      {chart.multiple ? (
        <div
          className="chart-legend"
          style={{ display: "flex", flexWrap: "wrap", alignItems: "center" }}
        >
          {chart.curves.map((curve) => (
            <div
              key={curve.strategy}
              style={{
                display: "flex",
                alignItems: "center",
                gap: 7,
                margin: "5px 12px 5px 0",
                fontSize: 12,
              }}
            >
              <span
                style={{
                  width: 9,
                  height: 9,
                  borderRadius: "50%",
                  background: curve.color,
                  display: "inline-block",
                  flexShrink: 0,
                }}
              />
              <span>
                {STRATEGY_LABELS[curve.strategy] ?? curve.strategy}
              </span>
              <span className="chart-range">
                {formatMoney(curve.coordinates[0].value)} →{" "}
                {formatMoney(curve.coordinates.at(-1).value)}
              </span>
            </div>
          ))}
        </div>
      ) : (
        <div className="chart-legend">
          <span className="legend-dot" />
          Portfolio value
          <span className="chart-range">
            {formatMoney(points[0].value)} → {formatMoney(points.at(-1).value)}
          </span>
        </div>
      )}
    </div>
  );
}