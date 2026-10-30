import { useEffect, useState } from 'react';
import { useApi, query } from '../api';
import { useWorkspace } from '../context';
import type { Row } from '../types';
import { num, pct } from '../utils';
import { Badge, DataTable, ErrorBlock, Loading, Notice, Panel, PanelTitle } from './Common';

interface Comparison {runs:Row[];strictly_comparable:boolean;warnings:string[];note:string}
export default function RunComparison(){
  const {runId,runs}=useWorkspace();
  const alternatives=runs.filter(r=>r.run_id!==runId&&r.status==='completed'&&r.has_research_artifacts);
  const [other,setOther]=useState(alternatives[0]?.run_id??'');
  useEffect(()=>{if(!alternatives.some(x=>x.run_id===other))setOther(alternatives[0]?.run_id??'');},[runId,runs,other]);
  const {data,error,loading}=useApi<Comparison>(other?query('/api/compare-runs',{run_ids:`${runId},${other}`}):null);
  return <Panel><PanelTitle eyebrow="EXPERIMENT HISTORY" title="Compare research runs" description="Compare the selected run with another immutable run; mismatched assumptions are flagged." aside={alternatives.length?<select aria-label="Compare another run" className="standalone-select" value={other} onChange={e=>setOther(e.target.value)}>{alternatives.map(r=><option key={r.run_id} value={r.run_id}>{r.run_id}</option>)}</select>:undefined}/>
    {!alternatives.length && <div className="empty-table">Generate a second completed research run to compare histories.</div>}
    {error&&<ErrorBlock message={error}/>} {loading&&<Loading label="Comparing run provenance"/>}
    {data&&<><div className="compare-status"><Badge tone={data.strictly_comparable?'green':'amber'}>{data.strictly_comparable?'MATCHED PROVENANCE':'CHECK DIFFERENCES'}</Badge><span>{data.note}</span></div>
      {data.warnings.length>0&&<div className="small-note">{data.warnings.join(' ')}</div>}
      <DataTable filename="run_comparison.csv" rows={data.runs} initialRows={5} columns={[{key:'run_id',label:'RUN'},{key:'control_history_sessions',label:'CONTROL HISTORY',format:(v)=>v?`${v} sessions`:'All prior'}, {key:'real_sharpe',label:'REAL SHARPE',align:'right',format:(v)=>num(v,3)},{key:'trend_sharpe',label:'TREND SHARPE',align:'right',format:(v)=>num(v,3)},{key:'matched_median_sharpe',label:'MATCHED MEDIAN',align:'right',format:(v)=>num(v,3)},{key:'matched_median_ks',label:'HMM KS',align:'right',format:(v)=>num(v,3)},{key:'real_max_drawdown',label:'REAL MAX DD',align:'right',format:(v)=>pct(v)}]}/>
    </>}
  </Panel>;
}
