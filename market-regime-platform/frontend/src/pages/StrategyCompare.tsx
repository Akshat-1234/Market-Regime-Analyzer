import { useMemo, useState } from 'react';
import { Bar, BarChart, CartesianGrid, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { ArrowRight, Check, CircleHelp } from 'lucide-react';
import { useApi, query } from '../api';
import { useWorkspace } from '../context';
import { Badge, CsvLink, DataTable, DateRange, ErrorBlock, Loading, Notice, PageHeading, Panel, PanelTitle, ReportLink, StatCard } from '../components/Common';
import { DrawdownChart, EquityChart, Legend } from '../components/Charts';
import type { Row, SeriesData } from '../types';
import { integer, num, pct, signed, signedPct, strategyColor } from '../utils';

interface AttributionData {status:Row;summary:Row[];bootstrap:Row[];simulations:Row[];periods:Row[];note:string}
const controls=['Past-only shuffled','Past-only block shuffled','Exposure/turnover-matched random'];
const nice:Record<string,string>={'Past-only shuffled':'Shuffled','Past-only block shuffled':'Block shuffled','Exposure/turnover-matched random':'Matched random'};
function Histogram({samples,real,trend}:{samples:Row[];real:number;trend:number}){
  const values=samples.map(x=>x.sharpe).filter((x:any)=>typeof x==='number'&&Number.isFinite(x)) as number[];
  if(!values.length) return <div className="empty-table">No simulations available.</div>;
  const min=Math.min(...values,real,trend)-.005,max=Math.max(...values,real,trend)+.005,width=(max-min)/18;
  const bins=Array.from({length:18},(_,i)=>({label:(min+(i+.5)*width).toFixed(3),count:0}));
  const idx=(v:number)=>Math.min(17,Math.max(0,Math.floor((v-min)/width)));
  values.forEach(x=>bins[idx(x)].count++);
  return <div className="chart" style={{height:230}}><ResponsiveContainer width="100%" height="100%"><BarChart data={bins} margin={{top:15,right:8,left:-20,bottom:2}}>
    <CartesianGrid stroke="#28313e" strokeDasharray="3 5" vertical={false}/><XAxis dataKey="label" tick={{fill:'#7f90a4',fontSize:10}} tickLine={false} axisLine={false} interval={3}/><YAxis allowDecimals={false} tick={{fill:'#7f90a4',fontSize:10}} tickLine={false} axisLine={false}/><Tooltip cursor={{fill:'#ffffff0b'}} content={({active,payload,label}:any)=>active&&payload?.length?<div className="chart-tooltip"><div className="tooltip-date">SHARPE ≈ {label}</div><strong>{payload[0].value} simulations</strong></div>:null}/>
    <Bar dataKey="count" name="Simulations" fill="#536a9d" radius={[3,3,0,0]} isAnimationActive={false}/><ReferenceLine x={bins[idx(real)].label} stroke="#62ddcb" strokeWidth={2}/><ReferenceLine x={bins[idx(trend)].label} stroke="#f3b76c" strokeWidth={1.5} strokeDasharray="4 3"/>
  </BarChart></ResponsiveContainer></div>;
}
export default function StrategyCompare(){
  const {runId,info,start,end}=useWorkspace();
  const [selected,setSelected]=useState(['HMM + Trend','Trend 50','Buy & Hold']);
  const [control,setControl]=useState(controls[2]);
  const [period,setPeriod]=useState('All periods');
  const path=query(`/api/runs/${runId}/series`,{start,end,strategies:selected.join(',')});
  const series=useApi<SeriesData>(path);
  const attr=useApi<AttributionData>(`/api/runs/${runId}/attribution`);
  function toggle(n:string){setSelected(old=>old.includes(n)?(old.length>1?old.filter(v=>v!==n):old):[...old,n]);}
  const controlSummary=attr.data?.summary.find(x=>x.control===`Trend + ${control}`);
  const real=attr.data?.summary.find(x=>x.control==='Trend + real HMM');
  const trend=attr.data?.summary.find(x=>x.control==='Trend alone');
  const sims=attr.data?.simulations.filter(x=>x.control===control)??[];
  const history=attr.data?.status.control_history_sessions;
  const periods=attr.data?.periods.filter(x=>period==='All periods'||x.period===period)??[];
  return <div className="page"><PageHeading eyebrow="RELATIVE PERFORMANCE  /  03" title="Strategy compare" description="Compare the actual portfolios, then isolate the contribution of HMM information."><ReportLink name="strategy_comparison">Strategy report</ReportLink></PageHeading>
    <div className="filter-line"><DateRange compact/><CsvLink name="performance">Full-run performance CSV</CsvLink></div>
    <Panel><PanelTitle eyebrow="STRATEGIES  /  INTERACTIVE SELECTION" title="Select portfolios" description="At least one strategy must remain selected; all metrics below use the selected dates."/>
      <div className="strategy-chips">{info.strategies.map(n=><button key={n} className={`strategy-chip ${selected.includes(n)?'selected':''}`} onClick={()=>toggle(n)} aria-pressed={selected.includes(n)}><span className="chip-check" style={selected.includes(n)?{background:strategyColor[n],borderColor:strategyColor[n]}:undefined}>{selected.includes(n)&&<Check size={11}/>}</span>{n}</button>)}</div>
    </Panel>
    {series.error && <ErrorBlock message={series.error}/>} {series.loading && <Loading label="Recalculating strategy comparison"/>}
    {series.data && <><Panel><PanelTitle eyebrow="SELECTED PERIOD  /  REBASED TO 100" title="Growth of capital" description={`${integer(series.data.observations)} aligned return sessions; inherited positions are not liquidated at the filter boundary.`}/><Legend names={selected}/><EquityChart data={series.data.equity} names={selected}/></Panel>
      <div className="two-col compare-lower"><Panel><PanelTitle eyebrow="DRAWDOWN" title="Underwater view" description="Peak-to-trough change within the selected period."/><DrawdownChart data={series.data.drawdown} names={selected} height={220}/></Panel>
      <Panel><PanelTitle eyebrow="COST & RISK" title="Selected-period metrics" description="Annualized ratios use all daily observations, not chart samples."/><DataTable filename="selected_strategy_metrics.csv" rows={series.data.stats} initialRows={9} columns={[
        {key:'strategy',label:'STRATEGY'}, {key:'cagr',label:'CAGR',align:'right',format:(v)=>pct(v)},{key:'sharpe',label:'SHARPE',align:'right',format:(v)=>num(v,2)}, {key:'max_drawdown',label:'MAX DD',align:'right',format:(v)=>pct(v)},{key:'turnover_per_year',label:'TURNOVER/YR',align:'right',format:(v)=>num(v,2)}]}/></Panel></div></>}
    <div className="section-heading"><div><div className="eyebrow cyan">THE CENTRAL QUESTION</div><h2>HMM incremental-value attribution</h2><p>Full-run controls are fixed to the run's original calendar; the date filter above does not change them.</p></div><ReportLink name="hmm_attribution">Full attribution report</ReportLink></div>
    {attr.error&&<ErrorBlock message={attr.error}/>} {attr.loading&&<Loading label="Loading control simulations"/>}
    {attr.data && <><Notice tone="info"><strong>Empirical controls, not p-values.</strong> {integer(attr.data.status.simulation_count_per_control)} simulations per control. {history ? `Prior-only ${history}-session rolling history` : 'Full prior history'}; seed {attr.data.status.attribution_seed}; blocks {attr.data.status.attribution_block_length} sessions. The 63-session default was chosen after inspecting preliminary matching diagnostics, not pre-registered. Exposure matching is approximate.</Notice>
      <div className="attribution-grid"><Panel><PanelTitle eyebrow="NET SHARPE  /  SIMULATION DISTRIBUTION" title="What if the HMM signal were randomized?" description="Histogram of completed control simulations; vertical lines are realized reference Sharpes." aside={<select aria-label="Attribution control" value={control} onChange={e=>setControl(e.target.value)} className="standalone-select">{controls.map(c=><option key={c} value={c}>{nice[c]}</option>)}</select>}/>
        <div className="chart-legend"><span><i style={{background:'#536a9d'}}/>Simulated control</span><span><i style={{background:'#62ddcb'}}/>Real HMM + Trend</span><span><i style={{background:'#f3b76c'}}/>Trend</span></div>
        <Histogram samples={sims} real={real?.sharpe??0} trend={trend?.sharpe??0}/><div className="panel-foot"><span>5th–95th percentiles: {num(controlSummary?.sharpe_p05,3)} to {num(controlSummary?.sharpe_p95,3)}</span><CsvLink name="attribution_simulations">All simulations</CsvLink></div>
      </Panel><Panel className="control-facts"><PanelTitle eyebrow={nice[control]?.toUpperCase()} title="Control diagnostics" description="Compare economic exposure, trading and realized risk."/>
        <div className="fact-row"><span>Median control Sharpe</span><strong>{num(controlSummary?.sharpe,3)}</strong></div><div className="fact-row"><span>Real blend Sharpe</span><strong>{num(real?.sharpe,3)}</strong></div><div className="fact-row"><span>Real above simulations</span><strong>{pct(controlSummary?.fraction_real_sharpe_above_control)}</strong></div><div className="fact-row"><span>Median exposure KS distance</span><strong>{num(controlSummary?.median_hmm_exposure_ks,3)}</strong></div><div className="fact-row"><span>Control / real turnover per yr</span><strong>{num(controlSummary?.turnover_per_year,2)} / {num(real?.turnover_per_year,2)}</strong></div>
        <div className="fact-note">The empirical fraction is descriptive. The KS distance compares HMM-leg exposure distributions; zero is an exact match. Common-fee differences below are approximate counterfactuals.</div>
      </Panel></div>
      <Panel><PanelTitle eyebrow="FULL RUN  /  NET OF EACH STRATEGY'S COSTS" title="Control comparison" description="Randomized rows are medians across simulations; exposure and turnover are diagnostics, not guaranteed matches." aside={<CsvLink name="attribution">Summary CSV</CsvLink>}/>
        <DataTable filename="attribution_summary.csv" rows={attr.data.summary} initialRows={5} columns={[
          {key:'control',label:'CONTROL'}, {key:'sharpe',label:'SHARPE',align:'right',format:(v)=>num(v,3)}, {key:'max_drawdown',label:'MAX DD',align:'right',format:(v)=>pct(v)}, {key:'mean_exposure',label:'EXPOSURE',align:'right',format:(v)=>pct(v)}, {key:'turnover_per_year',label:'TURNOVER/YR',align:'right',format:(v)=>num(v,2)}, {key:'median_hmm_exposure_ks',label:'HMM KS',align:'right',format:(v)=>num(v,3)}, {key:'median_real_minus_control_common_fee_sharpe',label:'Δ SHARPE · COMMON FEE',align:'right',format:(v)=>signed(v)}]}/>
      </Panel>
      <div className="two-col"><Panel><PanelTitle eyebrow={`${integer(attr.data.status.bootstrap_samples)} BOOTSTRAP RESAMPLES`} title="Paired bootstrap intervals" description="Against trend and each daily mean control portfolio; these intervals are not a test against a single random path." aside={<CsvLink name="attribution_bootstrap"/>}/>
        <DataTable filename="bootstrap_intervals.csv" rows={attr.data.bootstrap} initialRows={4} columns={[{key:'control',label:'REFERENCE'},{key:'observed_sharpe_difference',label:'Δ SHARPE',align:'right',format:(v)=>signed(v)},{key:'lower',label:'LOWER',align:'right',format:(v)=>signed(v)},{key:'upper',label:'UPPER',align:'right',format:(v)=>signed(v)}]}/>
        <div className="small-note">{pct(attr.data.bootstrap[0]?.confidence,0)} intervals; paired {attr.data.bootstrap[0]?.block_length}-session bootstrap blocks. No correction for prior strategy selection.</div>
      </Panel><Panel><PanelTitle eyebrow="PERIOD ROBUSTNESS" title="Different market episodes" description="Annualized Sharpe in short periods is noisy." aside={<select className="standalone-select" aria-label="Stress period filter" value={period} onChange={e=>setPeriod(e.target.value)}><option>All periods</option>{Array.from(new Set(attr.data.periods.map(x=>x.period))).map(p=><option key={String(p)}>{String(p)}</option>)}</select>}/>
        <DataTable filename="attribution_periods.csv" rows={periods} initialRows={6} columns={[{key:'period',label:'PERIOD'},{key:'control',label:'CONTROL',format:(v)=>nice[v]??v},{key:'real_sharpe',label:'REAL',align:'right',format:(v)=>num(v,2)},{key:'control_sharpe_median',label:'MEDIAN',align:'right',format:(v)=>num(v,2)}]}/>
      </Panel></div></>}
  </div>;
}
