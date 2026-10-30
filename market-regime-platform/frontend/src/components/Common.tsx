import { ArrowDownToLine, ArrowUpRight, CalendarDays, ChevronDown, Info, RefreshCw } from 'lucide-react';
import { useState } from 'react';
import type { ReactNode } from 'react';
import { useWorkspace } from '../context';
import { downloadCsv, shortDate } from '../utils';
import type { Row } from '../types';

export function Panel({ children, className = '' }: { children: ReactNode; className?: string }) {
  return <section className={`panel ${className}`}>{children}</section>;
}
export function PanelTitle({ eyebrow, title, aside, description }: { eyebrow?: string; title: string; aside?: ReactNode; description?: string }) {
  return <div className="panel-heading"><div>{eyebrow && <div className="eyebrow">{eyebrow}</div>}<h2>{title}</h2>{description && <p className="panel-description">{description}</p>}</div>{aside}</div>;
}
export function PageHeading({ eyebrow, title, description, children }: { eyebrow: string; title: string; description: string; children?: ReactNode }) {
  return <div className="page-heading"><div><div className="eyebrow cyan">{eyebrow}</div><h1>{title}</h1><p>{description}</p></div>{children}</div>;
}
export function Badge({ children, tone='neutral' }: {children: ReactNode; tone?: 'neutral'|'green'|'amber'|'purple'}) {
  return <span className={`badge badge-${tone}`}>{children}</span>;
}
export function Loading({ label='Loading research artifacts' }: {label?: string}) {
  return <div className="loading"><RefreshCw size={16} className="spin" /> {label}…</div>;
}
export function ErrorBlock({ message }: {message: string}) {
  return <div className="notice error"><Info size={17}/><span>{message}</span></div>;
}
export function Notice({ children, tone='info' }: {children: ReactNode; tone?: 'info'|'warning'|'success'}) {
  return <div className={`notice ${tone}`}><Info size={17}/><div>{children}</div></div>;
}
export function ReportLink({ name, children='Download report' }: { name: string; children?: ReactNode }) {
  const {runId}=useWorkspace();
  return <a className="text-link" href={`/api/runs/${runId}/report/${name}`} download>{children}<ArrowUpRight size={14}/></a>;
}
export function CsvLink({ name, children='CSV' }: { name: string; children?: ReactNode }) {
  const {runId}=useWorkspace();
  return <a className="button button-small button-ghost" href={`/api/runs/${runId}/export/${name}`} download><ArrowDownToLine size={14}/>{children}</a>;
}
export function DateRange({ compact=false }: {compact?: boolean}) {
  const { info, start, end, setStart, setEnd } = useWorkspace();
  const min=String(info.metadata.first_return_date).slice(0,10), max=String(info.metadata.last_return_date).slice(0,10);
  function setYears(n: number | null) {
    setEnd(max);
    if (n === null) { setStart(min); return; }
    const d = new Date(`${max}T00:00:00Z`); d.setUTCFullYear(d.getUTCFullYear()-n);
    setStart(d.toISOString().slice(0,10) < min ? min : d.toISOString().slice(0,10));
  }
  const activeAll=start===min && end===max;
  return <div className={`range-control ${compact?'compact':''}`} aria-label="Date range filters">
    <div className="range-presets"><button className={activeAll?'active':''} onClick={()=>setYears(null)}>ALL</button><button onClick={()=>setYears(5)}>5Y</button><button onClick={()=>setYears(3)}>3Y</button><button onClick={()=>setYears(1)}>1Y</button></div>
    <div className="range-dates"><CalendarDays size={14}/><label className="sr-only" htmlFor={`start-${compact}`}>Start date</label><input id={`start-${compact}`} aria-label="Start date" type="date" value={start} min={min} max={max} onChange={e=>e.target.value && setStart(e.target.value)}/><span>–</span><label className="sr-only" htmlFor={`end-${compact}`}>End date</label><input id={`end-${compact}`} aria-label="End date" type="date" value={end} min={min} max={max} onChange={e=>e.target.value && setEnd(e.target.value)}/></div>
  </div>;
}
export function StatCard({ label, value, meta, accent, icon }: {label: string; value: ReactNode; meta: ReactNode; accent?: string; icon?: ReactNode}) {
  return <div className="stat-card"><div className="stat-top"><span>{label}</span>{icon && <span className="stat-icon">{icon}</span>}</div><div className="stat-value" style={accent?{color:accent}:undefined}>{value}</div><div className="stat-meta">{meta}</div></div>;
}
export interface Column { key: string; label: string; format?: (v: any, row: Row) => ReactNode; align?: 'right'|'left'; }
export function DataTable({ rows, columns, filename, initialRows=8, empty='No observations for this selection.' }: { rows: Row[]; columns: Column[]; filename: string; initialRows?: number; empty?: string }) {
  const [expanded,setExpanded]=useState(false);
  const [sort,setSort]=useState<{key:string; descending:boolean}|null>(null);
  const sorted=[...rows];
  if(sort) sorted.sort((a,b)=>{
    const x=a[sort.key], y=b[sort.key]; if(x==null) return 1;if(y==null)return -1;
    const v=typeof x==='number' && typeof y==='number' ? x-y : String(x).localeCompare(String(y));
    return sort.descending ? -v : v;
  });
  const shown=expanded ? sorted : sorted.slice(0,initialRows);
  return <div className="data-table-wrap"><div className="table-actions"><span>{rows.length.toLocaleString('en-IN')} rows</span><button className="button button-small button-ghost" onClick={()=>downloadCsv(sorted,columns.map(c=>c.key),filename)} disabled={!rows.length}><ArrowDownToLine size={14}/>Export filtered CSV</button></div>
    <div className="table-scroll"><table><thead><tr>{columns.map(c=><th key={c.key} className={c.align==='right'?'right':''} aria-sort={sort?.key===c.key?(sort.descending?'descending':'ascending'):'none'}><button onClick={()=>setSort({key:c.key,descending:sort?.key===c.key?!sort.descending:false})}>{c.label}<ChevronDown size={11} className={sort?.key===c.key?'sort-active':''}/></button></th>)}</tr></thead>
    <tbody>{shown.map((row,i)=><tr key={i}>{columns.map(c=><td key={c.key} className={c.align==='right'?'right':''}>{c.format ? c.format(row[c.key],row) : (row[c.key] == null ? '—' : String(row[c.key]))}</td>)}</tr>)}</tbody></table></div>
    {!rows.length && <div className="empty-table">{empty}</div>}{rows.length>initialRows && <button className="table-more" onClick={()=>setExpanded(!expanded)}>{expanded?'Show fewer':`Show all ${rows.length} rows`} <ChevronDown size={13} className={expanded?'flip':''}/></button>}</div>;
}
export function DateCaption() { const {start,end}=useWorkspace(); return <span>{shortDate(start)} — {shortDate(end)}</span>; }
