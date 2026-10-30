import { useState } from 'react';
import { Bar, BarChart, CartesianGrid, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { useApi } from '../api';
import { useWorkspace } from '../context';
import { Badge, CsvLink, DataTable, ErrorBlock, Loading, Notice, PageHeading, Panel, PanelTitle, ReportLink, StatCard } from '../components/Common';
import type { Row } from '../types';
import RunComparison from '../components/RunComparison';
import { integer, num, pct, shortDate, signedPct } from '../utils';

interface ValidationData {folds:Row[];aggregate:Row[];stress:Row[];retrospective:Row[];freeze:Row;cash:Row[];fits:Row[];occupancy:Row[];model_diagnostics:Row[];state_stability:Row[];transitions:Row[]}
export default function Validation(){
  const {runId,info}=useWorkspace();
  const [strategy,setStrategy]=useState('HMM + Trend');
  const [period,setPeriod]=useState('All periods');
  const {data,error,loading}=useApi<ValidationData>(`/api/runs/${runId}/validation`);
  const folds=data?.folds.filter(x=>x.strategy===strategy)??[];
  const stress=data?.stress.filter(x=>x.strategy===strategy&&(period==='All periods'||x.period===period))??[];
  const chart=folds.map(x=>({year:String(x.test_signal_start).slice(0,4),sharpe:x.sharpe}));
  const rejected=data?.model_diagnostics.reduce((a,r)=>a+(r.rejected_seed_fits||0),0);
  const rate=info.data_manifest.cash_rate_reference;
  return <div className="page"><PageHeading eyebrow="RESEARCH INTEGRITY  /  04" title="Validation" description="Walk-forward evidence, stress windows and a strictly prospective holdout boundary."><ReportLink name="walk_forward">Validation report</ReportLink></PageHeading>
    <Notice tone="info"><strong>Full-run diagnostics.</strong> The fold, stress and holdout tables on this page use the run’s original dates and are not affected by the chart-date filters in other sections.</Notice>
    {error&&<ErrorBlock message={error}/>} {loading&&<Loading label="Loading validation artifacts"/>}
    {data && <><div className="stats-grid"><StatCard label="WALK-FORWARD FOLDS" value={integer(new Set(data.folds.map(x=>x.fold_id)).size)} meta="Annual expanding training windows"/><StatCard label="ACCEPTED MODEL FITS" value={integer(data.fits.length)} meta="One selected fit per model and fold"/><StatCard label="FITS WITH REJECTED SEEDS" value={integer(rejected)} meta="Fit rows with at least one rejected seed"/><StatCard label="PROSPECTIVE HOLDOUT" value="PENDING" meta={<>Decisions strictly after {shortDate(data.freeze.evaluation_decision_date_strictly_after)}</>} accent="#f3bd79"/></div>
      <div className="filter-line left"><label className="select-wrap"><span>STRATEGY</span><select aria-label="Validation strategy" value={strategy} onChange={e=>setStrategy(e.target.value)}>{info.strategies.map(s=><option key={s}>{s}</option>)}</select></label><CsvLink name="fold_metrics">All fold metrics</CsvLink></div>
      <Panel><PanelTitle eyebrow="ANNUAL REFITS  /  STRATEGY-SPECIFIC" title="Walk-forward by fold" description="Each bar is the selected strategy’s out-of-sample fold Sharpe. Aggregated Sharpe is recomputed from all daily returns, never averaged across these bars."/>
        <div className="chart" style={{height:215}}><ResponsiveContainer width="100%" height="100%"><BarChart data={chart} margin={{top:12,right:8,left:-18,bottom:0}}><CartesianGrid stroke="#28313e" strokeDasharray="3 5" vertical={false}/><XAxis dataKey="year" tick={{fill:'#7f90a4',fontSize:10}} tickLine={false} axisLine={false}/><YAxis tick={{fill:'#7f90a4',fontSize:10}} tickLine={false} axisLine={false}/><Tooltip cursor={{fill:'#ffffff08'}} content={({active,payload,label}:any)=>active&&payload?.length?<div className="chart-tooltip"><div className="tooltip-date">FOLD {label}</div><strong>Sharpe {num(payload[0].value,3)}</strong></div>:null}/><ReferenceLine y={0} stroke="#6c7888"/><Bar dataKey="sharpe" fill="#64d6c4" radius={[3,3,0,0]} isAnimationActive={false}/></BarChart></ResponsiveContainer></div>
        <DataTable filename="selected_fold_metrics.csv" rows={folds} initialRows={5} columns={[{key:'fold_id',label:'FOLD'}, {key:'train_end',label:'TRAIN END',format:(v)=>shortDate(v)}, {key:'test_signal_start',label:'FIRST SIGNAL',format:(v)=>shortDate(v)},{key:'test_signal_end',label:'LAST SIGNAL',format:(v)=>shortDate(v)},{key:'observations',label:'DAYS',align:'right'},{key:'cagr',label:'CAGR',align:'right',format:(v)=>pct(v)},{key:'sharpe',label:'SHARPE',align:'right',format:(v)=>num(v,2)},{key:'max_drawdown',label:'MAX DD',align:'right',format:(v)=>pct(v)}]}/>
      </Panel>
      <Panel><PanelTitle eyebrow="PREDEFINED CALENDAR WINDOWS" title="Stress-period analysis" description="Continuous inherited holdings; recovery is censored if the portfolio has not recovered by the end of the window." aside={<select aria-label="Validation stress period" className="standalone-select" value={period} onChange={e=>setPeriod(e.target.value)}><option>All periods</option>{Array.from(new Set(data.stress.map(x=>x.period))).map(p=><option key={String(p)}>{String(p)}</option>)}</select>}/>
        <DataTable filename="selected_stress_periods.csv" rows={stress} initialRows={6} columns={[{key:'period',label:'PERIOD'},{key:'actual_start',label:'START',format:(v)=>shortDate(v)},{key:'actual_end',label:'END',format:(v)=>shortDate(v)},{key:'total_return',label:'RETURN',align:'right',format:(v)=>signedPct(v)},{key:'sharpe',label:'SHARPE',align:'right',format:(v)=>num(v,2)},{key:'max_drawdown',label:'MAX DD',align:'right',format:(v)=>pct(v)},{key:'sessions_to_recover',label:'RECOVERY SESS.',align:'right',format:(v,row)=>v==null?(row.recovery_status==='no_drawdown'?'No drawdown':'Censored'):integer(v)}]}/>
        <div className="small-note">Fixed windows: 2013, 2015–2016, calendar 2020 including COVID recovery, and 2022. No added boundary liquidation.</div>
      </Panel>
      <div className="two-col"><Panel><PanelTitle eyebrow="NOT A HOLDOUT" title="Retrospective slice" description="Already examined during research; these are not untouched validation results." aside={<Badge tone="amber">RETROSPECTIVE</Badge>}/>
        <DataTable filename="retrospective_metrics.csv" rows={data.retrospective} initialRows={5} columns={[{key:'strategy',label:'STRATEGY'},{key:'cagr',label:'CAGR',align:'right',format:(v)=>pct(v)},{key:'sharpe',label:'SHARPE',align:'right',format:(v)=>num(v,2)},{key:'max_drawdown',label:'MAX DD',align:'right',format:(v)=>pct(v)}]}/>
      </Panel><Panel className="freeze-panel"><PanelTitle eyebrow="FROZEN AFTER HISTORICAL RESEARCH" title="Prospective holdout" description="No post-freeze observations have been evaluated." aside={<Badge tone="amber">PENDING</Badge>}/>
        <div className="fact-row"><span>Dataset ends</span><strong>{shortDate(data.freeze.last_original_data_date)}</strong></div><div className="fact-row"><span>Freeze date · India</span><strong>{shortDate(data.freeze.frozen_at_exchange_date)}</strong></div><div className="fact-row"><span>Eligible decisions</span><strong>After {shortDate(data.freeze.evaluation_decision_date_strictly_after)}</strong></div><div className="fact-row"><span>Source hash</span><strong className="hash">{String(data.freeze.source_code_sha256).slice(0,16)}…</strong></div>
        <div className="fact-note">The frozen rules allow scheduled annual refits with past data only. The evaluator rejects revised history or changed core code/configuration.</div><ReportLink name="holdout">Holdout protocol</ReportLink>
      </Panel></div>
      <div className="two-col"><Panel><PanelTitle eyebrow="SENSITIVITY, NOT A BASELINE CHANGE" title="Cash-rate assumptions" description={`Selected strategy · historical RBI proxy uses strictly prior auction yields${rate ? `; ${rate.dates_older_than_14_days} signal dates exceed 14 days old` : ''}.`}/>
        <DataTable filename="cash_rate_sensitivity.csv" rows={data.cash.filter(x=>x.strategy===strategy)} initialRows={3} columns={[{key:'cash_scenario',label:'SCENARIO'},{key:'cagr',label:'CAGR',align:'right',format:(v)=>pct(v)},{key:'sharpe',label:'SHARPE',align:'right',format:(v)=>num(v,3)},{key:'max_drawdown',label:'MAX DD',align:'right',format:(v)=>pct(v)}]}/>
      </Panel><Panel><PanelTitle eyebrow="MODEL FIT SAFEGUARDS" title="Fit & state checks" description="Unconverged or low-occupancy fits are rejected; if none is acceptable, the run aborts."/>
        <DataTable filename="model_occupancy.csv" rows={data.occupancy} initialRows={5} columns={[{key:'model',label:'MODEL'},{key:'local_volatility_rank',label:'STATE',align:'right'},{key:'days',label:'DAYS',align:'right',format:(v)=>integer(v)},{key:'occupancy',label:'OCCUPANCY',align:'right',format:(v)=>pct(v)},{key:'rare_below_5pct',label:'RARE < 5%',align:'right',format:(v)=>v?'YES':'NO'}]}/>
      </Panel></div>
      <RunComparison/>
      <Notice tone="warning"><strong>Interpretation limit.</strong> Overlapping training windows, extensive prior model selection, short stress windows and retrospective inspection mean these results are exploratory. Bootstrap intervals do not correct for selection.</Notice>
    </>}
  </div>;
}
