import { Area, AreaChart, CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import type { Row } from '../types';
import { pct, shortDate, strategyColor, yearTick } from '../utils';

const grid='#28313e', tick={fill:'#7f90a4',fontSize:11};
function TooltipBox({ active, payload, label, percent=false }: any) {
  if (!active || !payload?.length) return null;
  return <div className="chart-tooltip"><div className="tooltip-date">{shortDate(label)}</div>{payload.map((p:any)=><div className="tooltip-row" key={p.dataKey}><span><i style={{background:p.color}}/>{p.name}</span><strong>{percent?pct(p.value,2):Number(p.value).toFixed(2)}</strong></div>)}</div>;
}
export function EquityChart({ data, names, height=270 }: {data: Row[]; names: string[]; height?:number}) {
  return <div className="chart" style={{height}}><ResponsiveContainer width="100%" height="100%"><LineChart data={data} margin={{top:10,right:8,left:-14,bottom:0}}>
    <CartesianGrid stroke={grid} strokeDasharray="3 5" vertical={false}/><XAxis dataKey="Date" tickFormatter={yearTick} tick={tick} tickLine={false} axisLine={false} minTickGap={72}/><YAxis tick={tick} tickLine={false} axisLine={false} width={54} domain={['auto','auto']} tickFormatter={(v:number)=>v.toFixed(0)}/><Tooltip content={<TooltipBox/>}/>
    {names.map(n=><Line key={n} type="monotone" dataKey={n} name={n} stroke={strategyColor[n]??'#d0d7e2'} strokeWidth={n==='HMM + Trend'?2.5:1.7} dot={false} activeDot={{r:3}} isAnimationActive={false}/>)}</LineChart></ResponsiveContainer></div>;
}
export function DrawdownChart({ data, names, height=185 }: {data:Row[];names:string[];height?:number}) {
  return <div className="chart" style={{height}}><ResponsiveContainer width="100%" height="100%"><AreaChart data={data} margin={{top:8,right:8,left:-14,bottom:0}}>
    <defs><linearGradient id="dd" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#61dccb" stopOpacity={.04}/><stop offset="100%" stopColor="#61dccb" stopOpacity={.22}/></linearGradient></defs>
    <CartesianGrid stroke={grid} strokeDasharray="3 5" vertical={false}/><XAxis dataKey="Date" tickFormatter={yearTick} tick={tick} tickLine={false} axisLine={false} minTickGap={75}/><YAxis tick={tick} tickLine={false} axisLine={false} width={54} tickFormatter={(v:number)=>`${Math.round(v*100)}%`}/><Tooltip content={<TooltipBox percent/>}/>
    {names.map((n,i)=><Area key={n} type="monotone" dataKey={n} name={n} stroke={strategyColor[n]??'#d0d7e2'} fill={i===0?'url(#dd)':'transparent'} strokeWidth={i===0?1.7:1.3} dot={false} isAnimationActive={false}/>)}</AreaChart></ResponsiveContainer></div>;
}
export function Legend({ names }: {names:string[]}) {return <div className="chart-legend">{names.map(n=><span key={n}><i style={{background:strategyColor[n]??'#d0d7e2'}}/>{n}</span>)}</div>}
