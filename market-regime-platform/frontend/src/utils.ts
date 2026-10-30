import type { Row } from './types';

const valid = (v: unknown): v is number => typeof v === 'number' && Number.isFinite(v);
export const num = (v: unknown, n = 2) => valid(v) ? v.toFixed(n) : '—';
export const integer = (v: unknown) => valid(v) ? Math.round(v).toLocaleString('en-IN') : '—';
export const pct = (v: unknown, n = 1) => valid(v) ? `${(v * 100).toFixed(n)}%` : '—';
export const signed = (v: unknown, n = 3) => valid(v) ? `${v > 0 ? '+' : ''}${v.toFixed(n)}` : '—';
export const signedPct = (v: unknown, n = 1) => valid(v) ? `${v > 0 ? '+' : ''}${(v * 100).toFixed(n)}%` : '—';
export const shortDate = (s: string | undefined) => {
  if (!s) return '—';
  const d = new Date(`${s.slice(0, 10)}T00:00:00Z`);
  return Number.isNaN(d.getTime()) ? s : new Intl.DateTimeFormat('en-GB', { day:'2-digit', month:'short', year:'numeric', timeZone:'UTC' }).format(d);
};
export const yearTick = (s: string) => String(s).slice(0, 4);
export function evidence(bootstrap: Row[]) {
  const b = bootstrap.find(x => x.control === 'Trend');
  if (!b || !valid(b.lower) || !valid(b.upper)) return 'INTERVAL UNAVAILABLE';
  return b.lower <= 0 && b.upper >= 0 ? 'INTERVAL INCLUDES ZERO' : 'INTERVAL EXCLUDES ZERO';
}
export const stateName = (s: number, count = 3) => count < 2 ? `STATE ${s}` : s === 0 ? 'LOWER VOL' : s === count-1 ? 'HIGHER VOL' : 'MIDDLE VOL';
export const strategyColor: Record<string, string> = {
  'HMM + Trend':'#61dccb', 'Trend 50':'#f3b76c', 'Buy & Hold':'#7788fe',
  'HMM Ensemble':'#b899e7', 'Momentum 20':'#ee8daa', 'MA Reversion':'#69acdf',
  'RSI Reversion':'#e2d171', 'Donchian':'#a4c987', 'Vol Target':'#e1a883',
};

function escapeCsv(v: unknown) {
  if (v == null) return '';
  let s = String(v);
  if (typeof v === 'string' && /^[=+@]/.test(s)) s = "'" + s;
  return /[",\n\r]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
}
export function downloadCsv(rows: Row[], keys: string[], filename: string) {
  const text = [keys.map(escapeCsv).join(','), ...rows.map(r => keys.map(k => escapeCsv(r[k])).join(','))].join('\r\n');
  const url = URL.createObjectURL(new Blob([text], { type: 'text/csv;charset=utf-8' }));
  const a = document.createElement('a'); a.href = url; a.download = filename; a.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
