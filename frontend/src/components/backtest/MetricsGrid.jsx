import { useBacktest } from "../../context/BacktestContext.jsx";
import { buildMetricCards, getMetrics } from "../../utils/normalise.js";
import { formatMoney, formatNumber, formatPercent } from "../../utils/format.js";

const FORMATTERS = { money: formatMoney, percent: formatPercent, number: formatNumber };

export default function MetricsGrid() {
  const { result, form } = useBacktest();
  const cards = buildMetricCards(getMetrics(result), form.capital);

  return (
    <div className="metrics-grid">
      {cards.map((card) => {
        const value = FORMATTERS[card.kind](card.raw);
        const detail = card.detail
          ? ``
          : card.detailText;
        const positive = card.signed && Number(card.raw) >= 0;
        return (
          <article className={`metric-card ${card.featured ? "featured" : ""}`} key={card.key}>
            <div className="metric-label">{card.label}</div>
            <div className={`metric-value ${positive ? "positive" : ""}`}>{value}</div>
            <div className="metric-detail">{detail}</div>
          </article>
        );
      })}
    </div>
  );
}
