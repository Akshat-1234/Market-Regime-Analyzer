import { useState } from 'react';
import { Area, AreaChart, CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { useApi, query } from '../api';
import { useWorkspace } from '../context';
import { Badge, CsvLink, DataTable, DateRange, ErrorBlock, Loading, Notice, PageHeading, Panel, PanelTitle, ReportLink, StatCard } from '../components/Common';
import type { Row } from '../types';
import { integer, num, pct, shortDate, stateName, yearTick } from '../utils';

interface RegimeData {model:string;states:number;observations:number;models:string[];occupancy:Row[];points:Row[];note:string}
const colors=['#63d7c6','#f3bb70','#b09bf2'];
const tick={fill:'#7f90a4',fontSize:11};
function Tip({active,payload,label}:any) {if(!active||!payload?.length)return null;return <div className="chart-tooltip"><div className="tooltip-date">{shortDate(label)}</div>{payload.map((p:any)=><div className="tooltip-row" key={p.dataKey}><span><i style={{background:p.color}}/>{p.name}</span><strong>{p.dataKey==='close'?Number(p.value).toLocaleString('en-IN',{maximumFractionDigits:1}):pct(p.value)}</strong></div>)}</div>}
export default function RegimeExplorer(){
  const {runId,info,start,end}=useWorkspace();
  const [model,setModel]=useState(info.metadata.primary_model as string);
  const {data,error,loading}=useApi<RegimeData>(query(`/api/runs/${runId}/regime`,{model,start,end}));
  const validation=useApi<{transitions:Row[]}>(`/api/runs/${runId}/validation`);
  return <div className="page"><PageHeading eyebrow="MODEL INTELLIGENCE  /  02" title="Regime explorer" description="Inspect filtered state probabilities and how frequently each state appears."><ReportLink name="model_diagnostics">Model diagnostics</ReportLink></PageHeading>
    <div className="filter-line"><DateRange compact/><label className="select-wrap"><span>MODEL</span><select value={model} onChange={e=>setModel(e.target.value)} aria-label="HMM model">{info.models.map(m=><option key={m} value={m}>{m}</option>)}</select></label></div>
    {error && <ErrorBlock message={error}/>} {loading && <Loading label="Loading filtered regimes"/>}
    {data && <><div className="regime-stats"><StatCard label="DECISION OBSERVATIONS" value={integer(data.observations)} meta={<>Filtered signal dates <span className="meta-separator">·</span> {data.model}</>}/>{data.occupancy.map(x=><StatCard key={x.state} label={`STATE ${x.state} · ${stateName(x.state,data.states)}`} value={pct(x.occupancy)} meta={<>{integer(x.days)} decision dates <span className="meta-separator">·</span> volatility rank {x.state}</>} accent={colors[x.state]}/>)}</div>
      <Panel><PanelTitle eyebrow="CLOSE PRICES  /  SIGNAL DATES" title="Index level" description="Actual supplied index closes; state estimates use information available at each decision close." aside={<CsvLink name="signals">Full signals CSV</CsvLink>}/>
        <div className="chart" style={{height:230}}><ResponsiveContainer width="100%" height="100%"><LineChart data={data.points} margin={{top:10,right:10,left:6,bottom:0}}><CartesianGrid stroke="#28313e" strokeDasharray="3 5" vertical={false}/><XAxis dataKey="Date" tickFormatter={yearTick} tick={tick} tickLine={false} axisLine={false} minTickGap={75}/><YAxis tick={tick} tickLine={false} axisLine={false} width={62} domain={['auto','auto']} tickFormatter={(v:number)=>`${Math.round(v/1000)}k`}/><Tooltip content={<Tip/>}/><Line dataKey="close" name="Index close" type="monotone" stroke="#63d7c6" strokeWidth={2} dot={false} isAnimationActive={false}/></LineChart></ResponsiveContainer></div>
      </Panel>
      <Panel><PanelTitle eyebrow="FILTERED, NOT SMOOTHED" title="Probability by state" description="Forward-filtered probabilities sum to 100% on each decision date." aside={<Badge tone="green">CAUSAL FILTER</Badge>}/>
        <div className="chart-legend">{Array.from({length:data.states},(_,i)=><span key={i}><i style={{background:colors[i]}}/>State {i} · {stateName(i,data.states).toLowerCase()}</span>)}</div>
        <div className="chart" style={{height:250}}><ResponsiveContainer width="100%" height="100%"><AreaChart data={data.points} margin={{top:12,right:10,left:-12,bottom:0}}><CartesianGrid stroke="#28313e" strokeDasharray="3 5" vertical={false}/><XAxis dataKey="Date" tickFormatter={yearTick} tick={tick} tickLine={false} axisLine={false} minTickGap={75}/><YAxis domain={[0,1]} tickFormatter={(v:number)=>`${Math.round(v*100)}%`} tick={tick} tickLine={false} axisLine={false}/><Tooltip content={<Tip/>}/>{Array.from({length:data.states},(_,i)=><Area key={i} dataKey={`p${i}`} name={`State ${i}`} stackId="states" stroke={colors[i]} fill={colors[i]} fillOpacity={.56} strokeWidth={0.5} isAnimationActive={false}/>)}</AreaChart></ResponsiveContainer></div>
        <div className="panel-foot"><span>Plot points are sampled; state counts use every signal in the selected range.</span><span>{integer(data.observations)} signal dates</span></div>
      </Panel>
      <div className="two-col"><Panel><PanelTitle eyebrow="SELECTED WINDOW" title="State occupancy" description="These are model-specific volatility ranks, not fixed economic labels."/>
        <div className="occupancy-list spacious">{data.occupancy.map(x=><div className="occupancy-row" key={x.state}><div><span><i className={`state-dot state-${x.state}`}/>STATE {x.state} <small>{stateName(x.state,data.states)}</small></span><strong>{pct(x.occupancy)}</strong></div><div className="progress-track"><span className={`state-fill state-${x.state}`} style={{width:`${x.occupancy*100}%`}}/></div></div>)}</div>
      </Panel><Panel><PanelTitle eyebrow="PRIMARY MODEL  /  FULL RUN" title="Empirical transitions" description="Next observed ranked state; annual refits can change the meaning of a label."/>
        {model===info.metadata.primary_model && validation.data ? <DataTable filename="transitions.csv" rows={validation.data.transitions} columns={[{key:'from_state',label:'FROM'},...Array.from({length:data.states},(_,i)=>({key:`state_${i}`,label:`TO ${i}`,align:'right' as const,format:(v:any)=>pct(v)}))]} initialRows={3}/> : <div className="empty-table">Select {info.metadata.primary_model} to view its full-run transition matrix.</div>}
      </Panel></div>
      <Notice tone="warning"><strong>State identities are not permanent.</strong> Ranks are local to a fit and may change at refits; Hungarian volatility matching is a heuristic, not proof of the same latent state. No data after {shortDate(info.metadata.data_end)} are included.</Notice>
    </>}
  </div>;
}
