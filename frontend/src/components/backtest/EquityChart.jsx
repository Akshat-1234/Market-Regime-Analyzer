import { useMemo } from "react";
import { formatAxisMoney, formatChartDate, formatMoney } from "../../utils/format.js";

const WIDTH = 900;
const HEIGHT = 300;
const PAD = { top: 20, right: 18, bottom: 38, left: 76 };

export default function EquityChart({ points }) {
  const chart = useMemo(() => {
    if (!points.length) return null;

    const values = points.map((p) => p.value);
    const min = Math.min(...values);
    const max = Math.max(...values);
    const range = max - min || 1;
    const plotWidth = WIDTH - PAD.left - PAD.right;
    const plotHeight = HEIGHT - PAD.top - PAD.bottom;

    const coordinates = points.map((point, index) => ({
      ...point,
      x: PAD.left + (index / Math.max(points.length - 1, 1)) * plotWidth,
      y: PAD.top + ((max - point.value) / range) * plotHeight,
    }));

    const line = coordinates
      .map((p, i) => `${i === 0 ? "M" : "L"} ${p.x} ${p.y}`)
      .join(" ");
    const area = `${line} L ${coordinates.at(-1).x} ${HEIGHT - PAD.bottom} L ${coordinates[0].x} ${HEIGHT - PAD.bottom} Z`;

    return { coordinates, line, area, min, max };
  }, [points]);

  if (!chart) {
    return <div className="chart-empty">Run a backtest to see your portfolio equity curve.</div>;
  }

  const ticks = [0, Math.floor((points.length - 1) / 2), points.length - 1].filter(
    (v, i, arr) => arr.indexOf(v) === i
  );

  return (
    <div className="chart-wrap">
      <svg className="equity-chart" viewBox={`0 0 ${WIDTH} ${HEIGHT}`} role="img" aria-label="Portfolio equity curve">
        {[0, 1, 2, 3, 4].map((step) => {
          const y = PAD.top + (step / 4) * (HEIGHT - PAD.top - PAD.bottom);
          const value = chart.max - (step / 4) * (chart.max - chart.min);
          return (
            <g key={step}>
              <line x1={PAD.left} y1={y} x2={WIDTH - PAD.right} y2={y} className="chart-grid" />
              <text x={PAD.left - 10} y={y + 4} textAnchor="end" className="axis-label">
                {formatAxisMoney(value)}
              </text>
            </g>
          );
        })}

        <path d={chart.area} className="chart-area" />
        <path d={chart.line} className="chart-line" />

        {ticks.map((index) => {
          const point = chart.coordinates[index];
          return (
            <text
              key={index}
              x={point.x}
              y={HEIGHT - 12}
              textAnchor={index === 0 ? "start" : index === points.length - 1 ? "end" : "middle"}
              className="axis-label"
            >
              {formatChartDate(point.date)}
            </text>
          );
        })}
      </svg>
      <div className="chart-legend">
        <span className="legend-dot" />
        Portfolio value
        <span className="chart-range">
          {formatMoney(points[0].value)} → {formatMoney(points.at(-1).value)}
        </span>
      </div>
    </div>
  );
}
