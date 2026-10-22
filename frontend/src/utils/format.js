export const formatMoney = (value) =>
  Number.isFinite(Number(value))
    ? new Intl.NumberFormat("en-IN", {
        style: "currency",
        currency: "INR",
        maximumFractionDigits: 0,
      }).format(Number(value))
    : "—";

export const formatPercent = (value) =>
  Number.isFinite(Number(value)) ? `${(Number(value) * 100).toFixed(2)}%` : "—";

export const formatNumber = (value) =>
  Number.isFinite(Number(value)) ? Number(value).toFixed(2) : "—";

export const formatAxisMoney = (value) =>
  value >= 1000000
    ? `₹${(value / 1000000).toFixed(1)}m`
    : `₹${Math.round(value / 1000)}k`;

export const formatChartDate = (raw) => {
  const parsed = new Date(raw);
  return Number.isNaN(parsed.getTime())
    ? raw
    : parsed.toLocaleDateString("en-IN", {
        month: "short",
        year: "numeric",
        timeZone: "UTC",
      });
};
